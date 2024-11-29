from datetime import timedelta, timezone as tzone
from unittest.mock import call, patch

from django.urls import reverse
from django.utils import timezone

from temba import mailroom
from temba.campaigns.models import Campaign, CampaignEvent, EventFire
from temba.contacts.models import Contact, ContactExport, ContactField
from temba.flows.models import FlowStart
from temba.locations.models import AdminBoundary
from temba.orgs.models import Export, OrgRole
from temba.schedules.models import Schedule
from temba.tests import CRUDLTestMixin, MockResponse, TembaTest, mock_mailroom
from temba.tests.engine import MockSessionWriter
from temba.triggers.models import Trigger
from temba.utils import json
from temba.utils.views.mixins import TEMBA_MENU_SELECTION


class ContactCRUDLTest(CRUDLTestMixin, TembaTest):
    def setUp(self):
        super().setUp()

        self.country = AdminBoundary.create(osm_id="171496", name="Rwanda", level=0)
        AdminBoundary.create(osm_id="1708283", name="Kigali", level=1, parent=self.country)

        self.create_field("age", "Age", value_type="N", show_in_table=True)
        self.create_field("home", "Home", value_type="S", show_in_table=True, priority=10)

        # sample flows don't actually get created by org initialization during tests because there are no users at that
        # point so create them explicitly here, so that we also get the sample groups
        self.org.create_sample_flows("https://api.rapidpro.io")

    def test_menu(self):
        menu_url = reverse("contacts.contact_menu")

        self.assertRequestDisallowed(menu_url, [None, self.agent])
        self.assertPageMenu(
            menu_url,
            self.admin,
            [
                "Active (0)",
                "Archived (0)",
                "Blocked (0)",
                "Stopped (0)",
                "Import",
                "Fields (2)",
                ("Groups", ["Open Tickets (0)", "Survey Audience (0)", "Unsatisfied Customers (0)"]),
            ],
        )

    @mock_mailroom
    def test_create(self, mr_mocks):
        create_url = reverse("contacts.contact_create")

        self.assertRequestDisallowed(create_url, [None, self.agent, self.user])
        self.assertCreateFetch(create_url, [self.editor, self.admin], form_fields=("name", "phone"))

        # simulate validation failing because phone number taken
        mr_mocks.contact_urns({"tel:+250781111111": 12345678})

        self.assertCreateSubmit(
            create_url,
            self.admin,
            {"name": "Joe", "phone": "+250781111111"},
            form_errors={"phone": "In use by another contact."},
        )

        # simulate validation failing because phone number isn't E164
        mr_mocks.contact_urns({"tel:+250781111111": False})

        self.assertCreateSubmit(
            create_url,
            self.admin,
            {"name": "Joe", "phone": "+250781111111"},
            form_errors={"phone": "Ensure number includes country code."},
        )

        # simulate validation failing because phone number isn't valid
        mr_mocks.contact_urns({"tel:xx": "URN 0 invalid"})

        self.assertCreateSubmit(
            create_url,
            self.admin,
            {"name": "Joe", "phone": "xx"},
            form_errors={"phone": "Invalid phone number."},
        )

        # try valid number
        self.assertCreateSubmit(
            create_url,
            self.admin,
            {"name": "Joe", "phone": "+250782222222"},
            new_obj_query=Contact.objects.filter(org=self.org, name="Joe", urns__identity="tel:+250782222222"),
            success_status=200,
        )

    @mock_mailroom
    def test_list(self, mr_mocks):
        self.login(self.user)
        list_url = reverse("contacts.contact_list")

        joe = self.create_contact("Joe", phone="123", fields={"age": "20", "home": "Kigali"})
        frank = self.create_contact("Frank", phone="124", fields={"age": "18"})

        mr_mocks.contact_search('name != ""', contacts=[])
        self.create_group("No Name", query='name = ""')

        with self.assertNumQueries(16):
            response = self.client.get(list_url)

        self.assertEqual([frank, joe], list(response.context["object_list"]))
        self.assertIsNone(response.context["search_error"])
        self.assertEqual([], list(response.context["actions"]))
        self.assertContentMenu(list_url, self.user, ["Export"])

        active_contacts = self.org.active_contacts_group

        # fetch with spa flag
        response = self.client.get(list_url, content_type="application/json", HTTP_X_TEMBA_SPA="1")
        self.assertEqual(response.context["base_template"], "spa.html")

        mr_mocks.contact_search("age = 18", contacts=[frank])

        response = self.client.get(list_url + "?search=age+%3D+18")
        self.assertEqual(list(response.context["object_list"]), [frank])
        self.assertEqual(response.context["search"], "age = 18")
        self.assertEqual(response.context["save_dynamic_search"], True)
        self.assertIsNone(response.context["search_error"])
        self.assertEqual(
            [f.name for f in response.context["contact_fields"]], ["Home", "Age", "Last Seen On", "Created On"]
        )

        mr_mocks.contact_search("age = 18", contacts=[frank], total=10020)

        # we return up to 10000 contacts when searching with ES, so last page is 200
        url = f'{reverse("contacts.contact_list")}?{"search=age+%3D+18&page=200"}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # when user requests page 201, we return a 404, page not found
        url = f'{reverse("contacts.contact_list")}?{"search=age+%3D+18&page=201"}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

        mr_mocks.contact_search('age > 18 and home = "Kigali"', cleaned='age > 18 AND home = "Kigali"', contacts=[joe])

        response = self.client.get(list_url + '?search=age+>+18+and+home+%3D+"Kigali"')
        self.assertEqual(list(response.context["object_list"]), [joe])
        self.assertEqual(response.context["search"], 'age > 18 AND home = "Kigali"')
        self.assertEqual(response.context["save_dynamic_search"], True)
        self.assertIsNone(response.context["search_error"])

        mr_mocks.contact_search("Joe", cleaned='name ~ "Joe"', contacts=[joe])

        response = self.client.get(list_url + "?search=Joe")
        self.assertEqual(list(response.context["object_list"]), [joe])
        self.assertEqual(response.context["search"], 'name ~ "Joe"')
        self.assertEqual(response.context["save_dynamic_search"], True)
        self.assertIsNone(response.context["search_error"])

        with self.anonymous(self.org):
            mr_mocks.contact_search(f"{joe.id}", cleaned=f"id = {joe.id}", contacts=[joe])

            response = self.client.get(list_url + f"?search={joe.id}")
            self.assertEqual(list(response.context["object_list"]), [joe])
            self.assertIsNone(response.context["search_error"])
            self.assertEqual(response.context["search"], f"id = {joe.id}")
            self.assertEqual(response.context["save_dynamic_search"], False)

        # try with invalid search string
        mr_mocks.exception(mailroom.QueryValidationException("mismatched input at (((", "syntax"))

        response = self.client.get(list_url + "?search=(((")
        self.assertEqual(list(response.context["object_list"]), [])
        self.assertEqual(response.context["search_error"], "Invalid query syntax.")
        self.assertContains(response, "Invalid query syntax.")

        self.login(self.admin)

        # admins can see bulk actions
        age_query = "?search=age%20%3E%2050"
        response = self.client.get(list_url)
        self.assertEqual([frank, joe], list(response.context["object_list"]))
        self.assertEqual(["block", "archive", "send", "start-flow"], list(response.context["actions"]))

        self.assertContentMenu(
            list_url,
            self.admin,
            ["New Contact", "New Group", "Export"],
        )
        self.assertContentMenu(
            list_url + age_query,
            self.admin,
            ["Create Smart Group", "New Contact", "New Group", "Export"],
        )

        # TODO: group labeling as a feature is on probation
        # self.client.post(list_url, {"action": "label", "objects": frank.id, "label": survey_audience.id})
        # self.assertIn(frank, survey_audience.contacts.all())

        # try label bulk action against search results
        # self.client.post(list_url + "?search=Joe", {"action": "label", "objects": joe.id, "label": survey_audience.id})
        # self.assertIn(joe, survey_audience.contacts.all())

        # self.assertEqual(
        #    call(self.org.id, group_uuid=str(active_contacts.uuid), query="Joe", sort="", offset=0, exclude_ids=[]),
        #    mr_mocks.calls["contact_search"][-1],
        # )

        # try archive bulk action
        self.client.post(list_url + "?search=Joe", {"action": "archive", "objects": joe.id})

        # we re-run the search for the response, but exclude Joe
        self.assertEqual(
            call(self.org, active_contacts, "Joe", sort="", offset=0, exclude_ids=[joe.id]),
            mr_mocks.calls["contact_search"][-1],
        )

        response = self.client.get(list_url)
        self.assertEqual([frank], list(response.context["object_list"]))

        joe.refresh_from_db()
        self.assertEqual(Contact.STATUS_ARCHIVED, joe.status)

    @mock_mailroom
    def test_blocked(self, mr_mocks):
        joe = self.create_contact("Joe", urns=["twitter:joe"])
        frank = self.create_contact("Frank", urns=["twitter:frank"])
        billy = self.create_contact("Billy", urns=["twitter:billy"])
        self.create_contact("Mary", urns=["twitter:mary"])

        joe.block(self.admin)
        frank.block(self.admin)
        billy.block(self.admin)

        self.login(self.user)

        blocked_url = reverse("contacts.contact_blocked")

        self.assertRequestDisallowed(blocked_url, [None, self.agent])
        response = self.assertListFetch(blocked_url, [self.editor, self.admin], context_objects=[billy, frank, joe])
        self.assertEqual(["restore", "archive"], list(response.context["actions"]))
        self.assertContentMenu(blocked_url, self.admin, ["Export"])

        # try restore bulk action
        self.client.post(blocked_url, {"action": "restore", "objects": billy.id})

        response = self.client.get(blocked_url)
        self.assertEqual([frank, joe], list(response.context["object_list"]))

        billy.refresh_from_db()
        self.assertEqual(Contact.STATUS_ACTIVE, billy.status)

        # try archive bulk action
        self.client.post(blocked_url, {"action": "archive", "objects": frank.id})

        response = self.client.get(blocked_url)
        self.assertEqual([joe], list(response.context["object_list"]))

        frank.refresh_from_db()
        self.assertEqual(Contact.STATUS_ARCHIVED, frank.status)

    @mock_mailroom
    def test_stopped(self, mr_mocks):
        joe = self.create_contact("Joe", urns=["twitter:joe"])
        frank = self.create_contact("Frank", urns=["twitter:frank"])
        billy = self.create_contact("Billy", urns=["twitter:billy"])
        self.create_contact("Mary", urns=["twitter:mary"])

        joe.stop(self.admin)
        frank.stop(self.admin)
        billy.stop(self.admin)

        self.login(self.user)

        stopped_url = reverse("contacts.contact_stopped")

        self.assertRequestDisallowed(stopped_url, [None, self.agent])
        response = self.assertListFetch(
            stopped_url, [self.user, self.editor, self.admin], context_objects=[billy, frank, joe]
        )
        self.assertEqual(["restore", "archive"], list(response.context["actions"]))
        self.assertContentMenu(stopped_url, self.admin, ["Export"])

        # try restore bulk action
        self.client.post(stopped_url, {"action": "restore", "objects": billy.id})

        response = self.client.get(stopped_url)
        self.assertEqual([frank, joe], list(response.context["object_list"]))

        billy.refresh_from_db()
        self.assertEqual(Contact.STATUS_ACTIVE, billy.status)

        # try archive bulk action
        self.client.post(stopped_url, {"action": "archive", "objects": frank.id})

        response = self.client.get(stopped_url)
        self.assertEqual([joe], list(response.context["object_list"]))

        frank.refresh_from_db()
        self.assertEqual(Contact.STATUS_ARCHIVED, frank.status)

    @patch("temba.contacts.models.Contact.BULK_RELEASE_IMMEDIATELY_LIMIT", 5)
    @mock_mailroom
    def test_archived(self, mr_mocks):
        joe = self.create_contact("Joe", urns=["twitter:joe"])
        frank = self.create_contact("Frank", urns=["twitter:frank"])
        billy = self.create_contact("Billy", urns=["twitter:billy"])
        self.create_contact("Mary", urns=["twitter:mary"])

        joe.archive(self.admin)
        frank.archive(self.admin)
        billy.archive(self.admin)

        self.login(self.user)

        archived_url = reverse("contacts.contact_archived")

        self.assertRequestDisallowed(archived_url, [None, self.agent])
        response = self.assertListFetch(
            archived_url, [self.user, self.editor, self.admin], context_objects=[billy, frank, joe]
        )
        self.assertEqual(["restore", "delete"], list(response.context["actions"]))
        self.assertContentMenu(archived_url, self.admin, ["Export", "Delete All"])

        # try restore bulk action
        self.client.post(archived_url, {"action": "restore", "objects": billy.id})

        response = self.client.get(archived_url)
        self.assertEqual([frank, joe], list(response.context["object_list"]))

        billy.refresh_from_db()
        self.assertEqual(Contact.STATUS_ACTIVE, billy.status)

        # try delete bulk action
        self.client.post(archived_url, {"action": "delete", "objects": frank.id})

        response = self.client.get(archived_url)
        self.assertEqual([joe], list(response.context["object_list"]))

        frank.refresh_from_db()
        self.assertFalse(frank.is_active)

        # the archived view also supports deleting all
        self.client.post(archived_url, {"action": "delete", "all": "true"})

        response = self.client.get(archived_url)
        self.assertEqual([], list(response.context["object_list"]))

        # only archived contacts affected
        self.assertEqual(2, Contact.objects.filter(is_active=False, status=Contact.STATUS_ARCHIVED).count())
        self.assertEqual(2, Contact.objects.filter(is_active=False).count())

        # for larger numbers of contacts, a background task is used
        for c in range(6):
            contact = self.create_contact(f"Bob{c}", urns=[f"twitter:bob{c}"])
            contact.archive(self.user)

        response = self.client.get(archived_url)
        self.assertEqual(6, len(response.context["object_list"]))

        self.client.post(archived_url, {"action": "delete", "all": "true"})

        response = self.client.get(archived_url)
        self.assertEqual(0, len(response.context["object_list"]))

    @mock_mailroom
    def test_group(self, mr_mocks):
        open_tickets = self.org.groups.get(name="Open Tickets")
        joe = self.create_contact("Joe", phone="123")
        frank = self.create_contact("Frank", phone="124")
        self.create_contact("Bob", phone="125")

        mr_mocks.contact_search("age > 40", contacts=[frank], total=1)

        group1 = self.create_group("Testers", contacts=[joe, frank])  # static group
        group2 = self.create_group("Oldies", query="age > 40")  # smart group
        group2.contacts.add(frank)
        group3 = self.create_group("Other Org", org=self.org2)

        group1_url = reverse("contacts.contact_group", args=[group1.uuid])
        group2_url = reverse("contacts.contact_group", args=[group2.uuid])
        group3_url = reverse("contacts.contact_group", args=[group3.uuid])
        open_tickets_url = reverse("contacts.contact_group", args=[open_tickets.uuid])

        self.assertRequestDisallowed(group1_url, [None, self.agent, self.admin2])
        response = self.assertReadFetch(group1_url, [self.user, self.editor, self.admin])

        self.assertEqual([frank, joe], list(response.context["object_list"]))
        self.assertEqual(["block", "unlabel", "send", "start-flow"], list(response.context["actions"]))
        self.assertEqual(
            [f.name for f in response.context["contact_fields"]], ["Home", "Age", "Last Seen On", "Created On"]
        )

        self.assertContentMenu(
            group1_url,
            self.admin,
            ["Edit", "Export", "Usages", "Delete"],
        )

        response = self.assertReadFetch(group2_url, [self.editor])

        self.assertEqual([frank], list(response.context["object_list"]))
        self.assertEqual(["block", "archive", "send", "start-flow"], list(response.context["actions"]))
        self.assertContains(response, "age &gt; 40")

        # can access system group like any other except no options to edit or delete
        response = self.assertReadFetch(open_tickets_url, [self.editor])
        self.assertEqual([], list(response.context["object_list"]))
        self.assertEqual(["block", "archive", "send", "start-flow"], list(response.context["actions"]))
        self.assertContains(response, "tickets &gt; 0")
        self.assertContentMenu(open_tickets_url, self.admin, ["Export", "Usages"])

        # if a user tries to access a non-existent group, that's a 404
        response = self.requestView(reverse("contacts.contact_group", args=["21343253"]), self.admin)
        self.assertEqual(404, response.status_code)

        # if a user tries to access a group in another org, send them to the login page
        response = self.requestView(group3_url, self.admin)
        self.assertLoginRedirect(response)

        # if the user has access to that org, we redirect to the org choose page
        self.org2.add_user(self.admin, OrgRole.ADMINISTRATOR)
        response = self.requestView(group3_url, self.admin)
        self.assertRedirect(response, "/org/choose/")

    @mock_mailroom
    def test_read(self, mr_mocks):
        joe = self.create_contact("Joe", phone="123")

        read_url = reverse("contacts.contact_read", args=[joe.uuid])

        self.assertRequestDisallowed(read_url, [None, self.agent])

        self.assertContentMenu(read_url, self.user, [])
        self.assertContentMenu(read_url, self.editor, ["Edit", "Start Flow", "Open Ticket"])
        self.assertContentMenu(read_url, self.admin, ["Edit", "Start Flow", "Open Ticket"])

        # if there's an open ticket already, don't show open ticket option
        self.create_ticket(joe)
        self.assertContentMenu(read_url, self.editor, ["Edit", "Start Flow"])

        # login as viewer
        self.login(self.user)

        response = self.client.get(read_url)
        self.assertContains(response, "Joe")

        # login as admin
        self.login(self.admin)

        response = self.client.get(read_url)
        self.assertContains(response, "Joe")
        self.assertEqual("/contact/active", response.headers[TEMBA_MENU_SELECTION])

        # block the contact
        joe.block(self.admin)
        self.assertTrue(Contact.objects.get(pk=joe.id, status="B"))

        self.assertContentMenu(read_url, self.admin, ["Edit"])

        response = self.client.get(read_url)
        self.assertContains(response, "Joe")
        self.assertEqual("/contact/blocked", response.headers[TEMBA_MENU_SELECTION])

        # can't access a deleted contact
        joe.release(self.admin)

        response = self.client.get(read_url)
        self.assertEqual(response.status_code, 404)

        # contact with only a urn
        nameless = self.create_contact("", urns=["twitter:bobby_anon"])
        response = self.client.get(reverse("contacts.contact_read", args=[nameless.uuid]))
        self.assertContains(response, "bobby_anon")

        # contact without name or urn
        nameless = Contact.objects.create(org=self.org)
        response = self.client.get(reverse("contacts.contact_read", args=[nameless.uuid]))
        self.assertContains(response, "Contact Details")

        # invalid uuid should return 404
        response = self.client.get(reverse("contacts.contact_read", args=["invalid-uuid"]))
        self.assertEqual(response.status_code, 404)

    @mock_mailroom
    def test_update(self, mr_mocks):
        self.org.flow_languages = ["eng", "spa"]
        self.org.save(update_fields=("flow_languages",))

        self.create_field("gender", "Gender", value_type=ContactField.TYPE_TEXT)
        contact = self.create_contact(
            "Bob",
            urns=["tel:+593979111111", "tel:+593979222222", "telegram:5474754"],
            fields={"age": 41, "gender": "M"},
            language="eng",
        )
        testers = self.create_group("Testers", contacts=[contact])
        self.create_contact("Ann", urns=["tel:+593979444444"])

        update_url = reverse("contacts.contact_update", args=[contact.id])

        self.assertRequestDisallowed(update_url, [None, self.user, self.agent, self.admin2])
        self.assertUpdateFetch(
            update_url,
            [self.editor, self.admin],
            form_fields={
                "name": "Bob",
                "status": "A",
                "language": "eng",
                "groups": [testers],
                "new_scheme": None,
                "new_path": None,
                "urn__tel__0": "+593979111111",
                "urn__tel__1": "+593979222222",
                "urn__telegram__2": "5474754",
            },
        )

        # try to take URN in use by another contact
        mr_mocks.contact_urns({"tel:+593979444444": 12345678})

        self.assertUpdateSubmit(
            update_url,
            self.admin,
            {"name": "Bobby", "status": "B", "language": "spa", "groups": [testers.id], "urn__tel__0": "+593979444444"},
            form_errors={"urn__tel__0": "In use by another contact."},
            object_unchanged=contact,
        )

        # try to update to an invalid URN
        mr_mocks.contact_urns({"tel:++++": "invalid path component"})

        self.assertUpdateSubmit(
            update_url,
            self.admin,
            {"name": "Bobby", "status": "B", "language": "spa", "groups": [testers.id], "urn__tel__0": "++++"},
            form_errors={"urn__tel__0": "Invalid format."},
            object_unchanged=contact,
        )

        # try to add a new invalid phone URN
        mr_mocks.contact_urns({"tel:123": "not a valid phone number"})

        self.assertUpdateSubmit(
            update_url,
            self.admin,
            {
                "name": "Bobby",
                "status": "B",
                "language": "spa",
                "groups": [testers.id],
                "urn__tel__0": "+593979111111",
                "new_scheme": "tel",
                "new_path": "123",
            },
            form_errors={"new_path": "Invalid format."},
            object_unchanged=contact,
        )

        # try to add a new phone URN that isn't E164
        mr_mocks.contact_urns({"tel:123": False})

        self.assertUpdateSubmit(
            update_url,
            self.admin,
            {
                "name": "Bobby",
                "status": "B",
                "language": "spa",
                "groups": [testers.id],
                "urn__tel__0": "+593979111111",
                "new_scheme": "tel",
                "new_path": "123",
            },
            form_errors={"new_path": "Invalid phone number. Ensure number includes country code."},
            object_unchanged=contact,
        )

        # update all fields (removes second tel URN, adds a new Facebook URN)
        self.assertUpdateSubmit(
            update_url,
            self.admin,
            {
                "name": "Bobby",
                "status": "B",
                "language": "spa",
                "groups": [testers.id],
                "urn__tel__0": "+593979333333",
                "urn__telegram__2": "78686776",
                "new_scheme": "facebook",
                "new_path": "9898989",
            },
            success_status=200,
        )

        contact.refresh_from_db()
        self.assertEqual("Bobby", contact.name)
        self.assertEqual(Contact.STATUS_BLOCKED, contact.status)
        self.assertEqual("spa", contact.language)
        self.assertEqual({testers}, set(contact.get_groups()))
        self.assertEqual(
            ["tel:+593979333333", "telegram:78686776", "facebook:9898989"],
            [u.identity for u in contact.urns.order_by("-priority")],
        )

        # for non-active contacts, shouldn't see groups on form
        self.assertUpdateFetch(
            update_url,
            [self.editor, self.admin],
            form_fields={
                "name": "Bobby",
                "status": "B",
                "language": "spa",
                "new_scheme": None,
                "new_path": None,
                "urn__tel__0": "+593979333333",
                "urn__telegram__1": "78686776",
                "urn__facebook__2": "9898989",
            },
        )

        # try to update with invalid URNs
        mr_mocks.contact_urns({"tel:456": "invalid path component", "facebook:xxxxx": "invalid path component"})

        self.assertUpdateSubmit(
            update_url,
            self.admin,
            {
                "name": "Bobby",
                "status": "B",
                "language": "spa",
                "groups": [],
                "urn__tel__0": "456",
                "urn__facebook__2": "xxxxx",
            },
            form_errors={
                "urn__tel__0": "Invalid format.",
                "urn__facebook__2": "Invalid format.",
            },
            object_unchanged=contact,
        )

        # if contact has a language which is no longer a flow language, it should still be a valid option on the form
        contact.language = "kin"
        contact.save(update_fields=("language",))

        response = self.assertUpdateFetch(
            update_url,
            [self.admin],
            form_fields={
                "name": "Bobby",
                "status": "B",
                "language": "kin",
                "new_scheme": None,
                "new_path": None,
                "urn__tel__0": "+593979333333",
                "urn__telegram__1": "78686776",
                "urn__facebook__2": "9898989",
            },
        )
        self.assertContains(response, "Kinyarwanda")

        self.assertUpdateSubmit(
            update_url,
            self.admin,
            {
                "name": "Bobby",
                "status": "A",
                "language": "kin",
                "urn__tel__0": "+593979333333",
                "urn__telegram__1": "78686776",
                "urn__facebook__2": "9898989",
            },
            success_status=200,
        )

        contact.refresh_from_db()
        self.assertEqual("Bobby", contact.name)
        self.assertEqual(Contact.STATUS_ACTIVE, contact.status)
        self.assertEqual("kin", contact.language)

    @mock_mailroom
    def test_update_with_mailroom_error(self, mr_mocks):
        mr_mocks.exception(mailroom.RequestException("", "", MockResponse(400, '{"error": "Error updating contact"}')))

        contact = self.create_contact("Joe", phone="1234")

        self.login(self.admin)

        response = self.client.post(
            reverse("contacts.contact_update", args=[contact.id]),
            {"name": "Joe", "status": Contact.STATUS_ACTIVE, "language": "eng"},
        )

        self.assertFormError(
            response.context["form"], None, "An error occurred updating your contact. Please try again later."
        )

    @mock_mailroom
    def test_export(self, mr_mocks):
        export_url = reverse("contacts.contact_export")

        self.assertRequestDisallowed(export_url, [None, self.agent])
        response = self.assertUpdateFetch(export_url, [self.editor, self.admin], form_fields=("with_groups",))
        self.assertNotContains(response, "already an export in progress")

        # create a dummy export task so that we won't be able to export
        blocking_export = ContactExport.create(self.org, self.admin)

        response = self.client.get(export_url)
        self.assertContains(response, "already an export in progress")

        # check we can't submit in case a user opens the form and whilst another user is starting an export
        response = self.client.post(export_url, {})
        self.assertContains(response, "already an export in progress")
        self.assertEqual(1, Export.objects.count())

        # mark that one as finished so it's no longer a blocker
        blocking_export.status = Export.STATUS_COMPLETE
        blocking_export.save(update_fields=("status",))

        # try to export a group that is too big
        big_group = self.create_group("Big Group", contacts=[])
        mr_mocks.contact_export_preview(1_000_123)

        response = self.client.get(export_url + f"?g={big_group.uuid}")
        self.assertContains(response, "This group or search is too large to export.")

        response = self.client.post(
            export_url + f"?g={self.org.active_contacts_group.uuid}", {"with_groups": [big_group.id]}
        )
        self.assertEqual(200, response.status_code)

        export = Export.objects.exclude(id=blocking_export.id).get()
        self.assertEqual("contact", export.export_type)
        self.assertEqual(
            {"group_id": self.org.active_contacts_group.id, "search": None, "with_groups": [big_group.id]},
            export.config,
        )

    def test_scheduled(self):
        contact1 = self.create_contact("Joe", phone="+1234567890")
        contact2 = self.create_contact("Frank", phone="+1204567802")
        farmers = self.create_group("Farmers", contacts=[contact1, contact2])

        schedule_url = reverse("contacts.contact_scheduled", args=[contact1.uuid])

        self.assertRequestDisallowed(schedule_url, [None, self.agent, self.admin2])
        response = self.assertReadFetch(schedule_url, [self.user, self.editor, self.admin])
        self.assertEqual({"results": []}, response.json())

        # create a campaign and event fires for this contact
        campaign = Campaign.create(self.org, self.admin, "Reminders", farmers)
        joined = self.create_field("joined", "Joined On", value_type=ContactField.TYPE_DATETIME)
        event2_flow = self.create_flow("Reminder Flow")
        event1 = CampaignEvent.create_message_event(self.org, self.admin, campaign, joined, 2, unit="D", message="Hi")
        event2 = CampaignEvent.create_flow_event(self.org, self.admin, campaign, joined, 2, unit="D", flow=event2_flow)
        fire1 = EventFire.objects.create(event=event1, contact=contact1, scheduled=timezone.now() + timedelta(days=2))
        fire2 = EventFire.objects.create(event=event2, contact=contact1, scheduled=timezone.now() + timedelta(days=5))

        # create scheduled and regular broadcasts which send to both groups
        bcast1 = self.create_broadcast(
            self.admin,
            {"eng": {"text": "Hi again"}},
            contacts=[contact1, contact2],
            schedule=Schedule.create(self.org, timezone.now() + timedelta(days=3), Schedule.REPEAT_DAILY),
        )
        self.create_broadcast(self.admin, {"eng": {"text": "Bye"}}, contacts=[contact1, contact2])  # not scheduled

        # create scheduled trigger which this contact is explicitly added to
        trigger1_flow = self.create_flow("Favorites 1")
        trigger1 = Trigger.create(
            self.org,
            self.admin,
            trigger_type=Trigger.TYPE_SCHEDULE,
            flow=trigger1_flow,
            schedule=Schedule.create(self.org, timezone.now() + timedelta(days=4), Schedule.REPEAT_WEEKLY),
        )
        trigger1.contacts.add(contact1, contact2)

        # create scheduled trigger which this contact is added to via a group
        trigger2_flow = self.create_flow("Favorites 2")
        trigger2 = Trigger.create(
            self.org,
            self.admin,
            trigger_type=Trigger.TYPE_SCHEDULE,
            flow=trigger2_flow,
            schedule=Schedule.create(self.org, timezone.now() + timedelta(days=6), Schedule.REPEAT_MONTHLY),
        )
        trigger2.groups.add(farmers)

        # create scheduled trigger which this contact is explicitly added to... but also excluded from
        trigger3 = Trigger.create(
            self.org,
            self.admin,
            trigger_type=Trigger.TYPE_SCHEDULE,
            flow=self.create_flow("Favorites 3"),
            schedule=Schedule.create(self.org, timezone.now() + timedelta(days=4), Schedule.REPEAT_WEEKLY),
        )
        trigger3.contacts.add(contact1, contact2)
        trigger3.exclude_groups.add(farmers)

        response = self.requestView(schedule_url, self.admin)
        self.assertEqual(
            {
                "results": [
                    {
                        "type": "campaign_event",
                        "scheduled": fire1.scheduled.isoformat(),
                        "repeat_period": None,
                        "campaign": {"uuid": str(campaign.uuid), "name": "Reminders"},
                        "message": "Hi",
                    },
                    {
                        "type": "scheduled_broadcast",
                        "scheduled": bcast1.schedule.next_fire.astimezone(tzone.utc).isoformat(),
                        "repeat_period": "D",
                        "message": "Hi again",
                    },
                    {
                        "type": "scheduled_trigger",
                        "scheduled": trigger1.schedule.next_fire.astimezone(tzone.utc).isoformat(),
                        "repeat_period": "W",
                        "flow": {"uuid": str(trigger1_flow.uuid), "name": "Favorites 1"},
                    },
                    {
                        "type": "campaign_event",
                        "scheduled": fire2.scheduled.isoformat(),
                        "repeat_period": None,
                        "campaign": {"uuid": str(campaign.uuid), "name": "Reminders"},
                        "flow": {"uuid": str(event2_flow.uuid), "name": "Reminder Flow"},
                    },
                    {
                        "type": "scheduled_trigger",
                        "scheduled": trigger2.schedule.next_fire.astimezone(tzone.utc).isoformat(),
                        "repeat_period": "M",
                        "flow": {"uuid": str(trigger2_flow.uuid), "name": "Favorites 2"},
                    },
                ]
            },
            response.json(),
        )

        # fires for archived campaigns shouldn't appear
        campaign.archive(self.admin)

        response = self.requestView(schedule_url, self.admin)
        self.assertEqual(3, len(response.json()["results"]))

    @mock_mailroom
    def test_open_ticket(self, mr_mocks):
        contact = self.create_contact("Joe", phone="+593979000111")
        general = self.org.default_ticket_topic
        open_url = reverse("contacts.contact_open_ticket", args=[contact.id])

        self.assertRequestDisallowed(open_url, [None, self.user, self.agent, self.admin2])
        self.assertUpdateFetch(open_url, [self.editor, self.admin], form_fields=("topic", "assignee", "note"))

        # can submit with no assignee
        response = self.assertUpdateSubmit(open_url, self.admin, {"topic": general.id, "body": "Help", "assignee": ""})

        # should have new ticket
        ticket = contact.tickets.get()
        self.assertEqual(general, ticket.topic)
        self.assertIsNone(ticket.assignee)

        # and we're redirected to that ticket
        self.assertRedirect(response, f"/ticket/all/open/{ticket.uuid}/")

    @mock_mailroom
    def test_interrupt(self, mr_mocks):
        contact = self.create_contact("Joe", phone="+593979000111")
        other_org_contact = self.create_contact("Hans", phone="+593979123456", org=self.org2)

        read_url = reverse("contacts.contact_read", args=[contact.uuid])
        interrupt_url = reverse("contacts.contact_interrupt", args=[contact.uuid])

        self.login(self.admin)

        # shoud see start flow option
        response = self.client.get(read_url)
        self.assertContentMenu(read_url, self.admin, ["Edit", "Start Flow", "Open Ticket"])

        MockSessionWriter(contact, self.create_flow("Test")).wait().save()
        MockSessionWriter(other_org_contact, self.create_flow("Test", org=self.org2)).wait().save()

        # start option should be gone
        self.assertContentMenu(read_url, self.admin, ["Edit", "Open Ticket"])

        # can't interrupt if not logged in
        self.client.logout()
        response = self.client.post(interrupt_url)
        self.assertLoginRedirect(response)

        self.login(self.user)

        # can't interrupt if just regular user
        response = self.client.post(interrupt_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)

        response = self.client.post(interrupt_url)
        self.assertEqual(302, response.status_code)

        contact.refresh_from_db()
        self.assertIsNone(contact.current_flow)

        # can't interrupt contact in other org
        other_contact_interrupt = reverse("contacts.contact_interrupt", args=[other_org_contact.uuid])
        response = self.client.post(other_contact_interrupt)
        self.assertLoginRedirect(response)

        # contact should be unchanged
        other_org_contact.refresh_from_db()
        self.assertIsNotNone(other_org_contact.current_flow)

    @mock_mailroom
    def test_delete(self, mr_mocks):
        contact = self.create_contact("Joe", phone="+593979000111")
        other_org_contact = self.create_contact("Hans", phone="+593979123456", org=self.org2)

        delete_url = reverse("contacts.contact_delete", args=[contact.id])

        # can't delete if not logged in
        response = self.client.post(delete_url, {"id": contact.id})
        self.assertLoginRedirect(response)

        self.login(self.user)

        # can't delete if just regular user
        response = self.client.post(delete_url, {"id": contact.id})
        self.assertLoginRedirect(response)

        self.login(self.admin)

        response = self.client.post(delete_url, {"id": contact.id})
        self.assertEqual(302, response.status_code)

        contact.refresh_from_db()
        self.assertFalse(contact.is_active)

        self.assertEqual([call(self.org, [contact])], mr_mocks.calls["contact_deindex"])

        # can't delete contact in other org
        delete_url = reverse("contacts.contact_delete", args=[other_org_contact.id])
        response = self.client.post(delete_url, {"id": other_org_contact.id})
        self.assertLoginRedirect(response)

        # contact should be unchanged
        other_org_contact.refresh_from_db()
        self.assertTrue(other_org_contact.is_active)

    @mock_mailroom
    def test_start(self, mr_mocks):
        sample_flows = list(self.org.flows.order_by("name"))
        background_flow = self.create_flow("Background")
        archived_flow = self.create_flow("Archived")
        archived_flow.archive(self.admin)

        contact = self.create_contact("Joe", phone="+593979000111")
        start_url = f"{reverse('flows.flow_start', args=[])}?flow={sample_flows[0].id}&c={contact.uuid}"

        self.assertRequestDisallowed(start_url, [None, self.user, self.agent])
        response = self.assertUpdateFetch(start_url, [self.editor, self.admin], form_fields=["flow", "contact_search"])

        self.assertEqual([background_flow] + sample_flows, list(response.context["form"].fields["flow"].queryset))

        # try to submit without specifying a flow
        self.assertUpdateSubmit(
            start_url,
            self.admin,
            data={},
            form_errors={"flow": "This field is required.", "contact_search": "This field is required."},
            object_unchanged=contact,
        )

        # submit with flow...
        contact_search = dict(query=f"uuid='{contact.uuid}'", advanced=True)
        self.assertUpdateSubmit(
            start_url, self.admin, {"flow": background_flow.id, "contact_search": json.dumps(contact_search)}
        )

        # should now have a flow start
        start = FlowStart.objects.get()
        self.assertEqual(background_flow, start.flow)
        self.assertEqual(contact_search["query"], start.query)
        self.assertEqual({}, start.exclusions)

        # that has been queued to mailroom
        self.assertEqual("start_flow", mr_mocks.queued_batch_tasks[-1]["type"])
