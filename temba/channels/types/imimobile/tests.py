import pytz
from django.urls import reverse

from temba.tests import TembaTest
from ...models import Channel


class IMIMobileTypeTest(TembaTest):
    def test_claim(self):
        Channel.objects.all().delete()

        self.login(self.admin)
        url = reverse("channels.types.imimobile.claim")

        # shouldn't be able to see the claim IMI Mobile page if we aren't part of that group
        response = self.client.get(reverse("channels.channel_claim"))
        self.assertNotContains(response, url)

        # but if we are in the proper time zone
        self.org.timezone = pytz.timezone("Asia/Kolkata")
        self.org.save()

        response = self.client.get(reverse("channels.channel_claim"))
        self.assertContains(response, "IMI Mobile")
        self.assertContains(response, url)

        # try to claim a channel
        response = self.client.get(url)
        post_data = response.context["form"].initial

        post_data["username"] = "myUsername"
        post_data["password"] = "myPassword"
        post_data["secret_key"] = "c2af26c7-8b3d-47f8-a6e2-0524d0f835e2"
        post_data["campaign_id"] = "camp_001"
        post_data["sender_name"] = "MY_SENDER_NAME"

        response = self.client.post(url, post_data)

        channel = Channel.objects.get()

        from .type import IMIMobileType

        self.assertEqual("IN", channel.country)
        self.assertEqual("myUsername", channel.config[Channel.CONFIG_USERNAME])
        self.assertEqual("myPassword", channel.config[Channel.CONFIG_PASSWORD])
        self.assertEqual("camp_001", channel.config[IMIMobileType.CONFIG_CAMPAIGN_ID])
        self.assertEqual("MY_SENDER_NAME", channel.config[IMIMobileType.CONFIG_SENDER_NAME])
        self.assertEqual("IMI", channel.channel_type)

        config_url = reverse("channels.channel_configuration", args=[channel.uuid])
        self.assertRedirect(response, config_url)

        response = self.client.get(config_url)
        self.assertEqual(200, response.status_code)

        self.assertContains(response, reverse("courier.imi", args=[channel.uuid, "receive"]))
