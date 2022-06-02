from slack_sdk import WebClient
from django.utils.translation import ugettext_lazy as _
from smartmin.views import SmartFormView
from ...models import Channel
from ...views import ClaimViewMixin
from django import forms

class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):
        user_token = forms.CharField(
            label=_("User OAuth Token"),
            help_text=_("In https://api.slack.com/apps select your bot app and go to Features / OAuth & Permissions to see this information.")
        )
        bot_token = forms.CharField(
            label=_("Bot User OAuth Token"), 
            help_text=_("In https://api.slack.com/apps select your bot app and go to Features / OAuth & Permissions to see this information.")
        )
        verification_token = forms.CharField(
            label=_("Verification Token"),
            help_text=_("In https://api.slack.com/apps go to Settings / Basic information, find in App Credentials and paste here.")
        )
    
    def form_valid(self, form):
        from .type import SlackType
        
        user_token = form.cleaned_data["user_token"]
        bot_token = form.cleaned_data["bot_token"]
        verification_token = form.cleaned_data["verification_token"]
        
        client = WebClient(token=bot_token)

        auth_test = client.api_call(
            api_method='auth.test',
        )
        
        print(auth_test)
        
        config = {
            SlackType.CONFIG_BOT_TOKEN: bot_token,
            SlackType.CONFIG_USER_TOKEN: user_token,
            SlackType.CONFIG_VERIFICATION_TOKEN: verification_token,
        }

        self.object = Channel.create(
            org=self.org,
            user=self.request.user,
            country=None,
            channel_type=self.channel_type,
            name=auth_test["user"],
            address=auth_test["user"],
            config=config,
        )
        
        return super().form_valid(form)
    form_class = Form
    success_url = "uuid@channels.channel_configuration"
