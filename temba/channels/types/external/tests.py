from django.urls import reverse

from temba.tests import TembaTest

from ...models import Channel
from .type import ExternalType


class ExternalTypeTest(TembaTest):
    def test_claim(self):
        url = reverse("channels.types.external.claim")

        self.login(self.admin)

        # check that claim page URL appears on claim list page
        response = self.client.get(reverse("channels.channel_claim"))
        self.assertContains(response, url)

        # try to claim a channel
        Channel.objects.all().delete()
        response = self.client.get(url)
        post_data = response.context["form"].initial

        post_data["scheme"] = "tel"
        post_data["country"] = "RW"
        post_data["url"] = "http://localhost:8000/foo"
        post_data["method"] = "POST"
        post_data["body"] = "send=true"
        post_data["content_type"] = Channel.CONTENT_TYPE_JSON
        post_data["max_length"] = 180
        post_data["send_authorization"] = "Token 123"
        post_data["encoding"] = Channel.ENCODING_SMART
        post_data["mt_response_check"] = "SENT"

        # fail due to missing number and invalid URL
        response = self.client.post(url, post_data)
        self.assertFormError(response, "form", "url", "Cannot be a local or private host.")
        self.assertFormError(response, "form", "number", "This field is required.")

        # change scheme to Ext and add valid URL
        ext_url = "http://test.com/send.php?from={{from}}&text={{text}}&to={{to}}"
        post_data["url"] = ext_url
        post_data["scheme"] = "ext"

        # fail due to missing address
        response = self.client.post(url, post_data)
        self.assertFormError(response, "form", "address", "This field is required.")

        # update to valid number
        post_data["scheme"] = "tel"
        post_data["number"] = "12345"
        response = self.client.post(url, post_data)
        channel = Channel.objects.get()

        self.assertEqual(channel.country, "RW")
        self.assertTrue(channel.uuid)
        self.assertEqual(post_data["number"], channel.address)
        self.assertEqual(post_data["url"], channel.config[Channel.CONFIG_SEND_URL])
        self.assertEqual(post_data["method"], channel.config[ExternalType.CONFIG_SEND_METHOD])
        self.assertEqual(post_data["content_type"], channel.config[ExternalType.CONFIG_CONTENT_TYPE])
        self.assertEqual(channel.config[ExternalType.CONFIG_MAX_LENGTH], 180)
        self.assertEqual(channel.config["headers"][ExternalType.CONFIG_AUTHORIZATION], "Token 123")
        self.assertEqual(channel.channel_type, "EX")
        self.assertEqual(Channel.ENCODING_SMART, channel.config[Channel.CONFIG_ENCODING])
        self.assertEqual("send=true", channel.config[ExternalType.CONFIG_SEND_BODY])
        self.assertEqual("SENT", channel.config[ExternalType.CONFIG_MT_RESPONSE_CHECK])

        config_url = reverse("channels.channel_configuration", args=[channel.uuid])
        self.assertRedirect(response, config_url)

        response = self.client.get(config_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, reverse("courier.ex", args=[channel.uuid, "sent"]))
        self.assertContains(response, reverse("courier.ex", args=[channel.uuid, "delivered"]))
        self.assertContains(response, reverse("courier.ex", args=[channel.uuid, "failed"]))
        self.assertContains(response, reverse("courier.ex", args=[channel.uuid, "receive"]))
        self.assertContains(response, reverse("courier.ex", args=[channel.uuid, "stopped"]))

        # test substitution in our url
        self.assertEqual(
            "http://test.com/send.php?from=5080&text=test&to=%2B250788383383",
            channel.replace_variables(ext_url, {"from": "5080", "text": "test", "to": "+250788383383"}),
        )

        # test substitution with unicode
        self.assertEqual(
            "http://test.com/send.php?from=5080&text=Reply+%E2%80%9C1%E2%80%9D+for+good&to=%2B250788383383",
            channel.replace_variables(ext_url, {"from": "5080", "text": "Reply “1” for good", "to": "+250788383383"}),
        )

        # test substitution with XML encoding
        body = "<xml>{{text}}</xml>"
        self.assertEqual(
            "<xml>Hello &amp; World</xml>",
            channel.replace_variables(body, {"text": "Hello & World"}, Channel.CONTENT_TYPE_XML),
        )

        self.assertEqual(
            "<xml>التوطين</xml>", channel.replace_variables(body, {"text": "التوطين"}, Channel.CONTENT_TYPE_XML)
        )

        # test substitution with JSON encoding
        body = "{ body: {{text}} }"
        self.assertEqual(
            '{ body: "this is \\"quote\\"" }',
            channel.replace_variables(body, {"text": 'this is "quote"'}, Channel.CONTENT_TYPE_JSON),
        )

        # raw content type should be loaded on setting page as is
        channel.config[ExternalType.CONFIG_CONTENT_TYPE] = "application/x-www-form-urlencoded; charset=utf-8"
        channel.save()

        response = self.client.get(config_url)
        self.assertEqual(response.status_code, 200)

        channel.config[ExternalType.CONFIG_CONTENT_TYPE] = Channel.CONTENT_TYPE_XML
        channel.save()

        response = self.client.get(config_url)
        self.assertEqual(response.status_code, 200)

        # now claim a non-tel external channel
        response = self.client.get(url)
        post_data = response.context["form"].initial

        post_data["scheme"] = "ext"
        post_data["address"] = "123456789"
        post_data["url"] = "http://test.com/send.php?from={{from}}&text={{text}}&to={{to}}"
        post_data["method"] = "GET"
        post_data["content_type"] = Channel.CONTENT_TYPE_JSON
        post_data["max_length"] = 180
        post_data["encoding"] = Channel.ENCODING_SMART

        self.client.post(url, post_data)
        channel = Channel.objects.get(schemes=["ext"])
        self.assertEqual("123456789", channel.address)
        self.assertIsNone(channel.country.code)

    def test_claim_bulk_sender(self):
        url = reverse("channels.types.external.claim") + "?role=S&channel=%s" % self.channel.pk

        self.login(self.admin)

        response = self.client.get(url)
        self.assertEqual(
            set(response.context["form"].fields.keys()),
            set(
                [
                    "url",
                    "method",
                    "encoding",
                    "content_type",
                    "max_length",
                    "send_authorization",
                    "body",
                    "mt_response_check",
                    "loc",
                ]
            ),
        )

        post_data = response.context["form"].initial

        ext_url = "http://test.com/send.php?from={{from}}&text={{text}}&to={{to}}"

        post_data["url"] = ext_url
        post_data["method"] = "POST"
        post_data["body"] = "send=true"
        post_data["content_type"] = Channel.CONTENT_TYPE_JSON
        post_data["max_length"] = 180
        post_data["encoding"] = Channel.ENCODING_SMART
        post_data["mt_response_check"] = "SENT"

        response = self.client.post(url, post_data)
        channel = Channel.objects.filter(org=self.org).exclude(pk=self.channel.pk).first()

        self.assertEqual(channel.country, "RW")
        self.assertTrue(channel.uuid)
        self.assertEqual(self.channel.address, channel.address)
        self.assertEqual(post_data["url"], channel.config[Channel.CONFIG_SEND_URL])
        self.assertEqual(post_data["method"], channel.config[ExternalType.CONFIG_SEND_METHOD])
        self.assertEqual(post_data["content_type"], channel.config[ExternalType.CONFIG_CONTENT_TYPE])
        self.assertEqual(channel.config[ExternalType.CONFIG_MAX_LENGTH], 180)
        self.assertEqual(channel.channel_type, "EX")
        self.assertEqual(Channel.ENCODING_SMART, channel.config[Channel.CONFIG_ENCODING])
        self.assertEqual("send=true", channel.config[ExternalType.CONFIG_SEND_BODY])
        self.assertEqual("SENT", channel.config[ExternalType.CONFIG_MT_RESPONSE_CHECK])
        self.assertEqual(channel.role, "S")
        self.assertEqual(channel.parent, self.channel)

    def test_update(self):
        channel = Channel.create(
            self.org,
            self.user,
            None,
            "EX",
            name="EX 12345",
            address="12345",
            role="SR",
            schemes=["tel"],
            config={
                Channel.CONFIG_SEND_URL: "https://example.com/send",
                ExternalType.CONFIG_SEND_METHOD: "POST",
                ExternalType.CONFIG_CONTENT_TYPE: "json",
                ExternalType.CONFIG_MAX_LENGTH: 160,
                Channel.CONFIG_ENCODING: Channel.ENCODING_DEFAULT,
            },
        )
        update_url = reverse("channels.channel_update", args=[channel.id])

        self.login(self.admin)
        response = self.client.get(update_url)
        self.assertEqual(
            ["name", "alert_email", "role", "allow_international", "loc"],
            list(response.context["form"].fields.keys()),
        )

        post_data = dict(name="Receiver 1234", role=["R"], alert_email="alert@example.com")
        response = self.client.post(update_url, post_data)

        channel = Channel.objects.filter(pk=channel.pk).first()
        self.assertEqual(channel.role, "R")
        self.assertEqual(channel.name, "Receiver 1234")
        self.assertEqual(channel.alert_email, "alert@example.com")

        post_data = dict(name="Channel 1234", role=["R", "S"], alert_email="")

        response = self.client.post(update_url, post_data)

        channel = Channel.objects.filter(pk=channel.pk).first()
        self.assertEqual(channel.role, "RS")
        self.assertEqual(channel.name, "Channel 1234")
        self.assertIsNone(channel.alert_email)
