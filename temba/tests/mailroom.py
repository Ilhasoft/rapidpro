import functools
import re
from collections import defaultdict
from typing import Dict, List
from unittest.mock import call, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.utils import timezone

from temba.contacts.models import URN, Contact, ContactField, ContactGroup, ContactURN
from temba.mailroom.client import ContactSpec, MailroomClient, MailroomException
from temba.mailroom.modifiers import Modifier
from temba.orgs.models import Org
from temba.tickets.models import Ticket
from temba.utils import json


class Mocks:
    def __init__(self):
        self.calls = defaultdict(list)
        self._parse_query = {}
        self._contact_search = {}
        self._errors = []

        self.queued_batch_tasks = []

    @staticmethod
    def _parse_query_response(query: str, elastic: Dict, fields: List, allow_as_group: bool):
        def field_ref(f):
            return {"key": f.key, "name": f.label} if isinstance(f, ContactField) else {"key": f}

        return {
            "query": query,
            "elastic_query": elastic,
            "metadata": {
                "attributes": [],
                "schemes": [],
                "fields": [field_ref(f) for f in fields],
                "groups": [],
                "allow_as_group": allow_as_group,
            },
        }

    def parse_query(self, query, *, cleaned=None, fields=(), allow_as_group=True, elastic_query=None):
        def mock():
            elastic = elastic_query or {"term": {"is_active": True}}
            return self._parse_query_response(cleaned or query, elastic, fields, allow_as_group)

        self._parse_query[query] = mock

    def contact_search(self, query, *, cleaned=None, contacts=(), total=0, fields=(), allow_as_group=True):
        def mock(offset, sort):
            return {
                "query": cleaned or query,
                "contact_ids": [c.id for c in contacts],
                "total": total or len(contacts),
                "offset": offset,
                "sort": sort,
                "metadata": {
                    "attributes": [],
                    "schemes": [],
                    "fields": [{"key": f.key, "name": f.label} for f in fields],
                    "groups": [],
                    "allow_as_group": allow_as_group,
                },
            }

        self._contact_search[query] = mock

    def error(self, msg: str, code: str = None, extra: Dict = None):
        """
        Queues an error which will become a mailroom exception at the next client call
        """
        err = {"error": msg}
        if code:
            err["code"] = code
        if extra:
            err["extra"] = extra

        self._errors.append(err)

    def _check_error(self, endpoint: str):
        if self._errors:
            raise MailroomException(endpoint, None, self._errors.pop(0))


def _client_method(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        self.mocks.calls[func.__name__].append(call(*args, **kwargs))
        self.mocks._check_error(func.__name__)

        return func(self, *args, **kwargs)

    return wrap


class TestClient(MailroomClient):
    def __init__(self, mocks: Mocks):
        self.mocks = mocks

        super().__init__(settings.MAILROOM_URL, settings.MAILROOM_AUTH_TOKEN)

    @_client_method
    def contact_create(self, org_id: int, user_id: int, contact: ContactSpec):
        org = Org.objects.get(id=org_id)
        user = User.objects.get(id=user_id)

        obj = create_contact_locally(
            org, user, contact.name, contact.language, contact.urns, contact.fields, contact.groups
        )

        return {"contact": {"id": obj.id, "uuid": str(obj.uuid), "name": obj.name}}

    @_client_method
    def contact_modify(self, org_id, user_id, contact_ids, modifiers: List[Modifier]):
        org = Org.objects.get(id=org_id)
        user = User.objects.get(id=user_id)
        contacts = org.contacts.filter(id__in=contact_ids)

        apply_modifiers(org, user, contacts, modifiers)

        return {c.id: {"contact": {}, "events": []} for c in contacts}

    @_client_method
    def parse_query(self, org_id, query, group_uuid=""):
        # if there's a mock for this query we use that
        mock = self.mocks._parse_query.get(query)
        if mock:
            return mock()

        # otherwise just approximate what mailroom would do
        tokens = [t.lower() for t in re.split(r"\W+", query) if t]
        fields = ContactField.all_fields.filter(org_id=org_id, key__in=tokens)
        allow_as_group = "id" not in tokens and "group" not in tokens

        return Mocks._parse_query_response(query, {"term": {"is_active": True}}, fields, allow_as_group)

    @_client_method
    def contact_search(self, org_id, group_uuid, query, sort, offset=0, exclude_ids=()):
        mock = self.mocks._contact_search.get(query or "")

        assert mock, f"missing contact_search mock for query '{query}'"

        return mock(offset, sort)

    @_client_method
    def ticket_close(self, org_id, ticket_ids):
        tickets = Ticket.objects.filter(org_id=org_id, status=Ticket.STATUS_OPEN, id__in=ticket_ids)
        tickets.update(status=Ticket.STATUS_CLOSED)

        return {"changed_ids": [t.id for t in tickets]}

    @_client_method
    def ticket_reopen(self, org_id, ticket_ids):
        tickets = Ticket.objects.filter(org_id=org_id, status=Ticket.STATUS_CLOSED, id__in=ticket_ids)
        tickets.update(status=Ticket.STATUS_OPEN)

        return {"changed_ids": [t.id for t in tickets]}


def mock_mailroom(f):
    """
    Convenience decorator to make a test method use a mocked version of the mailroom client
    """

    def wrapped(instance, *args, **kwargs):
        with patch("temba.mailroom.get_client") as mock_get_client, patch(
            "temba.mailroom.queue._queue_batch_task"
        ) as mock_queue_batch_task:
            mocks = Mocks()
            mock_get_client.return_value = TestClient(mocks)

            def queue_batch_task(org_id, task_type, task, priority):
                mocks.queued_batch_tasks.append(
                    {"type": task_type.value, "org_id": org_id, "task": task, "queued_on": timezone.now()}
                )

            mock_queue_batch_task.side_effect = queue_batch_task

            return f(instance, mocks, *args, **kwargs)

    return wrapped


def apply_modifiers(org, user, contacts, modifiers: List):
    """
    Approximates mailroom applying modifiers but doesn't do dynamic group re-evaluation.
    """

    for mod in modifiers:
        fields = dict()
        clear_groups = False

        if mod.type == "name":
            fields = dict(name=mod.name)

        if mod.type == "language":
            fields = dict(language=mod.language)

        if mod.type == "field":
            for c in contacts:
                update_field_locally(user, c, mod.field.key, mod.value, label=mod.field.name)

        elif mod.type == "status":
            if mod.status == "blocked":
                fields = dict(status=Contact.STATUS_BLOCKED)
                clear_groups = True
            elif mod.status == "stopped":
                fields = dict(status=Contact.STATUS_STOPPED)
                clear_groups = True
            elif mod.status == "archived":
                fields = dict(status=Contact.STATUS_ARCHIVED)
                clear_groups = True
            else:
                fields = dict(status=Contact.STATUS_ACTIVE)

        elif mod.type == "groups":
            add = mod.modification == "add"
            for contact in contacts:
                update_groups_locally(contact, [g.uuid for g in mod.groups], add=add)

        elif mod.type == "urns":
            assert len(contacts) == 1, "should never be trying to bulk update contact URNs"
            assert mod.modification == "set", "should only be setting URNs from here"

            update_urns_locally(contacts[0], mod.urns)

        contacts.update(modified_by=user, modified_on=timezone.now(), **fields)
        if clear_groups:
            for c in contacts:
                Contact.objects.get(id=c.id).clear_all_groups(user)


def create_contact_locally(org, user, name, language, urns, fields, group_uuids):
    orphaned_urns = {}

    for urn in urns:
        existing = ContactURN.lookup(org, urn)
        if existing:
            if existing.contact_id:
                raise MailroomException("contact/create", None, {"error": "URNs in use by other contacts"})
            else:
                orphaned_urns[urn] = existing

    contact = Contact.objects.create(
        org=org, name=name, language=language, created_by=user, modified_by=user, created_on=timezone.now(),
    )
    update_urns_locally(contact, urns)
    update_fields_locally(user, contact, fields)
    update_groups_locally(contact, group_uuids, add=True)
    return contact


def update_fields_locally(user, contact, fields):
    for key, val in fields.items():
        update_field_locally(user, contact, key, val)


def update_field_locally(user, contact, key, value, label=None):
    field = ContactField.get_or_create(contact.org, user, key, label=label)

    field_uuid = str(field.uuid)
    if contact.fields is None:
        contact.fields = {}

    if not value:
        value = None
        if field_uuid in contact.fields:
            del contact.fields[field_uuid]

    else:
        field_dict = contact.serialize_field(field, value)

        if contact.fields.get(field_uuid) != field_dict:
            contact.fields[field_uuid] = field_dict

    # update our JSONB on our contact
    with connection.cursor() as cursor:
        if value is None:
            # delete the field
            cursor.execute("UPDATE contacts_contact SET fields = fields - %s WHERE id = %s", [field_uuid, contact.id])
        else:
            # update the field
            cursor.execute(
                "UPDATE contacts_contact SET fields = COALESCE(fields,'{}'::jsonb) || %s::jsonb WHERE id = %s",
                [json.dumps({field_uuid: contact.fields[field_uuid]}), contact.id],
            )


def update_urns_locally(contact, urns: List[str]):
    country = contact.org.get_country_code()
    priority = ContactURN.PRIORITY_HIGHEST

    urns_created = []  # new URNs created
    urns_attached = []  # existing orphan URNs attached
    urns_retained = []  # existing URNs retained

    for urn_as_string in urns:
        normalized = URN.normalize(urn_as_string, country)
        urn = ContactURN.lookup(contact.org, normalized)

        if not urn:
            urn = ContactURN.create(contact.org, contact, normalized, priority=priority)
            urns_created.append(urn)

        # unassigned URN or different contact
        elif not urn.contact or urn.contact != contact:
            urn.contact = contact
            urn.priority = priority
            urn.save()
            urns_attached.append(urn)

        else:
            if urn.priority != priority:
                urn.priority = priority
                urn.save()
            urns_retained.append(urn)

        # step down our priority
        priority -= 1

    # detach any existing URNs that weren't included
    urn_ids = [u.pk for u in (urns_created + urns_attached + urns_retained)]
    urns_detached = ContactURN.objects.filter(contact=contact).exclude(id__in=urn_ids)
    urns_detached.update(contact=None)


def update_groups_locally(contact, group_uuids, add: bool):
    groups = ContactGroup.user_groups.filter(uuid__in=group_uuids)
    for group in groups:
        assert not group.is_dynamic, "can't add/remove contacts from smart groups"
        if add:
            group.contacts.add(contact)
        else:
            group.contacts.remove(contact)
