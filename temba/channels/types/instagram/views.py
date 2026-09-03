import logging

import requests
from smartmin.views import SmartFormView, SmartModelActionView

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from temba.orgs.views.mixins import OrgObjPermsMixin
from temba.utils.text import truncate
from temba.utils.views.mixins import ModalFormMixin

from ...models import Channel
from ...views import ChannelTypeMixin, ClaimViewMixin

logger = logging.getLogger(__name__)

PAGE_PERMISSION_ERROR = _(
    "This Facebook account doesn't have permission on the linked page. Reconnect as a page admin and select that page"
)
RECONNECT_OAUTH_STATE_PLACEHOLDER = "00000000-0000-0000-0000-000000000000"


def get_page_access_token(fb_user_id, page_id, long_lived_auth_token):
    url = f"https://graph.facebook.com/v22.0/{fb_user_id}/accounts"
    params = {"access_token": long_lived_auth_token}

    while url:
        response = requests.get(url, params=params)

        if response.status_code != 200:  # pragma: no cover
            logger.error(
                "Failed to get Instagram page token: status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise Exception("Failed to get a page long lived token")

        response_json = response.json()

        for page in response_json.get("data", []):
            if page["id"] == str(page_id) and page.get("access_token"):
                return page["access_token"], page["name"]

        url = response_json.get("paging", {}).get("next")
        params = {}

    raise Exception("Empty page access token!")


class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):
        user_access_token = forms.CharField(min_length=32, required=True, help_text=_("The User Access Token"))
        page_name = forms.CharField(required=True, help_text=_("The name of the Facebook page"))
        page_id = forms.IntegerField(required=True, help_text="The Facebook Page ID")

        def clean(self):
            try:
                auth_token = self.cleaned_data["user_access_token"]
                name = self.cleaned_data["page_name"]
                page_id = self.cleaned_data["page_id"]

                app_id = settings.FACEBOOK_APPLICATION_ID
                app_secret = settings.FACEBOOK_APPLICATION_SECRET

                url = "https://graph.facebook.com/v22.0/debug_token"
                params = {"access_token": f"{app_id}|{app_secret}", "input_token": auth_token}

                response = requests.get(url, params=params)
                if response.status_code != 200:  # pragma: no cover
                    raise Exception("Failed to get user ID")

                response_json = response.json()

                fb_user_id = response_json.get("data", dict()).get("user_id")
                expires_at = response_json.get("data", dict()).get("expires_at")

                if expires_at != 0:
                    # get user long lived access token
                    url = "https://graph.facebook.com/oauth/access_token"
                    params = {
                        "grant_type": "fb_exchange_token",
                        "client_id": app_id,
                        "client_secret": app_secret,
                        "fb_exchange_token": auth_token,
                    }

                    response = requests.get(url, params=params)
                    if response.status_code != 200:  # pragma: no cover
                        raise Exception("Failed to get a user long lived token")

                    long_lived_auth_token = response.json().get("access_token", "")

                    if long_lived_auth_token == "":  # pragma: no cover
                        raise Exception("Empty user access token!")

                    auth_token = long_lived_auth_token

                page_access_token, name = get_page_access_token(fb_user_id, page_id, auth_token)

                url = f"https://graph.facebook.com/v22.0/{page_id}/subscribed_apps"
                params = {"access_token": page_access_token}
                data = {"subscribed_fields": "messages,messaging_postbacks"}

                response = requests.post(url, data=data, params=params)

                if response.status_code != 200:  # pragma: no cover
                    raise Exception("Failed to subscribe to app for webhook events")

                self.cleaned_data["page_access_token"] = page_access_token
                self.cleaned_data["name"] = truncate(name, Channel._meta.get_field("name").max_length)

                # requires instagram_basic permission
                # https://developers.facebook.com/docs/instagram-api/reference/page#read
                url = f"https://graph.facebook.com/{page_id}?fields=instagram_business_account"
                params = {"access_token": auth_token}

                response = requests.get(url, params=params)

                if response.status_code != 200:  # pragma: no cover
                    raise Exception("Failed to get IG user")

                response_json = response.json()
                self.cleaned_data["address"] = response_json.get("instagram_business_account").get("id")

            except Exception as e:
                logger.error(f"Unable to connect Instagram channel with error: {str(e)}", exc_info=True)
                raise forms.ValidationError(_("Sorry your Instagram channel could not be connected. Please try again"))

            return super().clean()

    form_class = Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["claim_url"] = reverse("channels.types.instagram.claim")
        context["facebook_app_id"] = settings.FACEBOOK_APPLICATION_ID
        context["reconnect_oauth_placeholder"] = RECONNECT_OAUTH_STATE_PLACEHOLDER
        context["reconnect_token_url_template"] = reverse(
            "channels.types.instagram.refresh_token",
            args=(RECONNECT_OAUTH_STATE_PLACEHOLDER,),
        )

        context["facebook_login_instagram_config_id"] = settings.FACEBOOK_LOGIN_INSTAGRAM_CONFIG_ID

        claim_error = None
        if context["form"].errors:
            claim_error = context["form"].errors["__all__"][0]
        context["claim_error"] = claim_error
        return context

    def form_valid(self, form):
        page_id = form.cleaned_data["page_id"]
        page_access_token = form.cleaned_data["page_access_token"]
        name = form.cleaned_data["name"]
        ig_user_id = form.cleaned_data["address"]

        config = {
            Channel.CONFIG_AUTH_TOKEN: page_access_token,
            Channel.CONFIG_PAGE_NAME: name,
            "page_id": page_id,
        }

        self.object = Channel.create(
            self.request.org,
            self.request.user,
            None,
            self.channel_type,
            name=name,
            address=ig_user_id,
            config=config,
        )

        return super().form_valid(form)


class RefreshToken(ChannelTypeMixin, OrgObjPermsMixin, ModalFormMixin, SmartModelActionView):
    class Form(forms.Form):
        user_access_token = forms.CharField(min_length=32, required=True, help_text=_("The User Access Token"))
        fb_user_id = forms.CharField(
            required=True,
            help_text=_("The Facebook User ID of the admin that connected the channel"),
        )

    slug_url_kwarg = "uuid"
    success_url = "uuid@channels.channel_read"
    form_class = Form
    permission = "channels.channel_claim"
    fields = ()
    template_name = "channels/types/instagram/refresh_token.html"
    title = _("Reconnect Instagram Business Account")

    def derive_menu_path(self):
        return f"/settings/channels/{self.get_object().uuid}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["refresh_url"] = reverse("channels.types.instagram.refresh_token", args=(self.object.uuid,))
        context["oauth_redirect_path"] = reverse("channels.types.instagram.claim")
        context["channel_uuid"] = str(self.object.uuid)

        app_id = settings.FACEBOOK_APPLICATION_ID
        app_secret = settings.FACEBOOK_APPLICATION_SECRET

        context["facebook_app_id"] = app_id

        context["facebook_login_instagram_config_id"] = settings.FACEBOOK_LOGIN_INSTAGRAM_CONFIG_ID

        url = "https://graph.facebook.com/v22.0/debug_token"
        params = {
            "access_token": f"{app_id}|{app_secret}",
            "input_token": self.object.config[Channel.CONFIG_AUTH_TOKEN],
        }
        resp = requests.get(url, params=params)

        error_connect = False
        if resp.status_code != 200:
            error_connect = True
        else:
            valid_token = resp.json().get("data", dict()).get("is_valid", False)
            if not valid_token:
                error_connect = True

        context["error_connect"] = error_connect

        non_field_errors = context["form"].non_field_errors()
        context["reconnect_error"] = non_field_errors[0] if non_field_errors else None

        return context

    def get_queryset(self):
        return self.request.org.channels.filter(is_active=True, channel_type=self.channel_type.code)

    def execute_action(self):
        form = self.form
        channel = self.object

        auth_token = form.data["user_access_token"]
        fb_user_id = form.data["fb_user_id"]

        page_id = channel.config.get("page_id")

        if page_id is None:
            raise Exception("Failed to get channel page ID")  # pragma: needs cover

        app_id = settings.FACEBOOK_APPLICATION_ID
        app_secret = settings.FACEBOOK_APPLICATION_SECRET

        # get user long lived access token
        url = "https://graph.facebook.com/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": auth_token,
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:  # pragma: no cover
            logger.error(
                "Failed to get Instagram user long lived token: status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise ValidationError(_("Instagram channel couldn't be reconnected due to a technical issue"))

        long_lived_auth_token = response.json().get("access_token", "")

        if long_lived_auth_token == "":  # pragma: no cover
            raise ValidationError(_("Instagram channel couldn't be reconnected due to a technical issue"))

        try:
            page_access_token, name = get_page_access_token(fb_user_id, page_id, long_lived_auth_token)
        except Exception as e:
            if str(e) == "Empty page access token!":
                logger.warning(
                    "Instagram reconnect did not find linked page %s for Facebook user %s",
                    page_id,
                    fb_user_id,
                )
                raise ValidationError(PAGE_PERMISSION_ERROR)
            logger.error("Unable to refresh Instagram channel token with error: %s", str(e), exc_info=True)
            raise ValidationError(_("Instagram channel couldn't be reconnected due to a technical issue"))

        url = f"https://graph.facebook.com/v22.0/{page_id}/subscribed_apps"
        params = {"access_token": page_access_token}
        data = {"subscribed_fields": "messages,messaging_postbacks"}

        response = requests.post(url, data=data, params=params)

        if response.status_code != 200:  # pragma: no cover
            logger.error(
                "Failed to subscribe Instagram webhooks: status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise ValidationError(_("Instagram channel couldn't be reconnected due to a technical issue"))

        channel.config[Channel.CONFIG_AUTH_TOKEN] = page_access_token
        channel.config[Channel.CONFIG_PAGE_NAME] = name
        channel.save(update_fields=["config"])
