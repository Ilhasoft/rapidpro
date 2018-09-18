from django import forms
from django.utils.translation import ugettext_lazy as _
from smartmin.views import SmartFormView

from ...models import Channel
from ...views import ClaimViewMixin


class ClaimView(ClaimViewMixin, SmartFormView):
    class IMIClaimForm(ClaimViewMixin.Form):
        api_key = forms.CharField(max_length=36, min_length=36, help_text=_("The IMI Mobile secret key"))
        username = forms.CharField(max_length=32, help_text=_("The account username provided by IMI Mobile"))
        password = forms.CharField(max_length=64, help_text=_("The account password provided by IMI Mobile"))
        campaign_id = forms.CharField(max_length=64, help_text=_("The campaign ID provided by IMI Mobile"))
        sender_name = forms.CharField(max_length=64, help_text=_("The sender name provided by IMI Mobile"))

    form_class = IMIClaimForm

    def form_valid(self, form: IMIClaimForm):
        user = self.request.user
        data = form.cleaned_data
        org = user.get_org()

        if not org:  # pragma: no cover
            raise Exception(_("No org for this user, cannot claim"))

        from .type import IMIMobileType

        config = {
            Channel.CONFIG_USERNAME: data["username"],
            Channel.CONFIG_PASSWORD: data["password"],
            Channel.CONFIG_API_KEY: data["api_key"],
            IMIMobileType.CONFIG_CAMPAIGN_ID: data["campaign_id"],
            IMIMobileType.CONFIG_SENDER_NAME: data["sender_name"],
        }

        self.object = Channel.create(org, user, "IN", "IMI", name="IMI Mobile: %s" % data["username"], config=config)

        return super(ClaimView, self).form_valid(form)
