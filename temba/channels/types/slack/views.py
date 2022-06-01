from django.utils.translation import ugettext_lazy as _
from smartmin.views import SmartFormView
from ...views import ClaimViewMixin
from django import forms

class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):
        bot_token = forms.CharField(
            label=_("Bot Token")
        )
        user_token = forms.CharField(
            label=_("Bot Token")
        )
        verification_token = forms.CharField(
            label=_("Verification Token")
        )
    form_class = Form