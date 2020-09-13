import requests
from smartmin.views import SmartFormView

from django import forms
from django.utils.translation import ugettext_lazy as _

from temba.utils.fields import ExternalURLField
from temba.utils.text import random_string, truncate
from temba.utils.uuid import uuid4

from ...models import Channel
from ...views import ClaimViewMixin
from .type import RocketChatType, RE_HOST
from .client import Client, ClientError

UUID_PATTERN = r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
RE_UUID = re.compile(UUID_PATTERN)
RE_BASE_URL = re.compile(rf"https?://[^ \"]+/{UUID_PATTERN}")

SECRET_LENGTH = 32


class ClaimView(ClaimViewMixin, SmartFormView):
    SESSION_KEY = "_channel_rocketchat_secret"

    _secret = None
    form_blurb = _("Setup your RocketChat first to be able to integrate.")

    class Form(ClaimViewMixin.Form):
        base_url = ExternalURLField(
            label=_("URL"),
            widget=forms.URLInput(
                attrs={
                    "placeholder": _(
                        "Ex.: http://my.rocket.chat/29542a4b-5a89-4f27-872b"
                        "-5f8091899f7b"
                    )
                }
            ),
            help_text=_("The URL for your RocketChat Channnel app"),
        )
        bot_username = forms.CharField(
            label=_("Bot username"), help_text=_("The username of your RocketChat app")
        )
        secret = forms.CharField(
            label=_("Secret"),
            widget=forms.HiddenInput(),
            help_text=_("Secret to be passed to RocketChat"),
        )

        def clean(self):
            secret = self.cleaned_data.get("secret")
            if not secret:
                raise forms.ValidationError(_("Invalid secret code"))

            initial = self.initial.get("secret")
            if secret != initial:
                self.data = self.data.copy()
                self.data["secret"] = initial
                raise forms.ValidationError(_("Secret code change detected."))
            return self.cleaned_data

        def clean_base_url(self):

            org = self.request.user.get_org()
            base_url = RE_BASE_URL.search(self.cleaned_data.get("base_url", ""))
            if base_url:
                base_url = base_url.group()
            else:
                raise forms.ValidationError(
                    _("Invalid URL %(base_url)s") % self.cleaned_data
                )

            base_url_exists = org.channels.filter(
                is_active=True,
                channel_type=RocketChatType.slug,
                **{f"config__{RocketChatType.CONFIG_BASE_URL}": base_url},
            ).exists()
            if base_url_exists:
                raise forms.ValidationError(
                    _("There is already a channel configured for this URL.")
                )

            return base_url

        def get_secret(self):
            if self._secret:
                return self.get_secret

            self._secret = self.request.session.get(self.SESSION_KEY)
            if not self._secret or self.request.method.lower() != "post":
                self.request.session[self.SESSION_KEY] = self._secret = random_string(
                    SECRET_LENGTH
                )

            return self._secret

        def derive_initial(self):
            initial = super().derive_initial()
            initial["secret"] = self.get_secret()
            return initial

        def form_valid(self, form):

            base_url = form.cleaned_data["base_url"]
            bot_username = form.cleaned_data["bot_username"]
            secret = form.cleaned_data["secret"]
            config = {
                RocketChatType.CONFIG_BASE_URL: base_url,
                RocketChatType.CONFIG_BOT_USERNAME: bot_username,
                RocketChatType.CONFIG_SECRET:secret,
            }

            self.object = Channel(
                uuid=uuid4(),
                org=self.org,
                channel_type=RocketChatType.slug,
                config=config,
                name=truncate(
                    f"{RocketChatType.name}: {RE_HOST.search(url).group('domain')}",
                    Channel._meta.get_field("name").max_length,
                ),
                created_by=self.request.user,
                modified_by=self.request.user,
            )

            try:
                client = Client(**config)
                client.settings(self.request.build_absolute_uri("/"), self.object)
            except ClientError as err:
                messages.error(self.request,err.msg if err.msg else _("Configuration has failed"))
                return super().get(self.request,*self.args,**self.kwargs)
            else:
                self.request.session.pop(self.SESSION_KEY,None)

            self.object.save()
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs["secret"] = self.get_secret()
        return super().get_context_data(**kwargs)

    form_class = Form
    template_name = "channels/types/rocketchat/claim.haml"
