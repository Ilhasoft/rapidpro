import pytz
from django.urls import reverse

from temba.tests import TembaTest
from ...models import Channel


class IMIMobileTypeTest(TembaTest):
    def test_claim(self):
        Channel.objects.all().delete()

        self.login(self.admin)
        url = reverse("channels.types.imimobile.claim")

        # shouldn't be able to see the claim novo page if we aren't part of that group
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

        response = self.client.post(url, post_data)

        channel = Channel.objects.get()

        self.assertEqual("IN", channel.country)
        self.assertEqual("myUsername", channel.config[Channel.CONFIG_USERNAME])
        self.assertEqual("myPassword", channel.config[Channel.CONFIG_PASSWORD])
        self.assertEqual("IMI", channel.channel_type)

        config_url = reverse("channels.channel_configuration", args=[channel.uuid])
        self.assertRedirect(response, config_url)

        response = self.client.get(config_url)
        self.assertEqual(200, response.status_code)

        self.assertContains(response, reverse("courier.imI", args=[channel.uuid, "receive"]))
