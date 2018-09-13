from django.utils.translation import ugettext_lazy as _
from temba.channels.types.imimobile.forms import ClaimView

from temba.channels.models import ChannelType
from temba.contacts.models import TEL_SCHEME


class IMIMobileType(ChannelType):
    """
     An IMI mobile channel (https://imimobile.com/)
     """

    courier_url = r"^imi/(?P<uuid>[a-z0-9\-]+)/(?P<action>receive)$"

    code = "IMI"
    category = ChannelType.Category.PHONE

    name = "IMI Mobile"

    claim_blurb = _(
        """Configure your <a href="https://imimobile.com/">IMI Mobile</a> in a few simple steps."""
    )
    claim_view = ClaimView

    schemes = [TEL_SCHEME]
    max_length = 1120

    show_config_page = True
    attachment_support = False

    recommended_timezones = ["Asia/Kolkata"]

    configuration_urls = (
        dict(
            label=_("Receive URL"),
            url="https://{{ channel.callback_domain }}{% url 'courier.imi' channel.uuid 'receive' %}",
            description=_("To receive incoming messages, you need to set the receive URL for your IMI Mobile account."),
        ),
    )

    def is_available_to(self, user):
        org = user.get_org()
        return org.timezone and str(org.timezone) in ["Asia/Kolkata"]
