from unittest.mock import patch

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount, SocialLogin

from django.conf import settings
from django.contrib.messages import get_messages
from django.test import RequestFactory

from temba.orgs.models import Invitation, OrgRole
from temba.tests.base import TembaTest
from temba.users.adapter import TembaSocialAccountAdapter
from temba.users.models import User


class SSOAdapterTest(TembaTest):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.adapter = TembaSocialAccountAdapter()

    def _make_sociallogin(self, email, **extra_data):
        sociallogin = SocialLogin()
        sociallogin.account = SocialAccount(
            provider="openid_connect",
            uid="uid-test",
            extra_data={"email": email, **extra_data},
        )
        return sociallogin

    def _make_request(self):
        request = self.factory.get("/accounts/login/")
        request.session = self.client.session
        request.branding = settings.BRAND
        return request

    def test_extract_email_from_upn(self):
        sociallogin = self._make_sociallogin("", upn="user@unicef.org")
        self.assertEqual("user@unicef.org", TembaSocialAccountAdapter.extract_email(sociallogin))

    def test_pre_social_login_marks_existing_unverified_email_as_verified(self):
        user = User.objects.create_user(
            email="user@unicef.org",
            password=self.default_password,
            first_name="Test",
            last_name="User",
        )
        EmailAddress.objects.filter(user=user).update(verified=False)

        request = self._make_request()
        sociallogin = self._make_sociallogin("user@unicef.org")

        self.adapter.pre_social_login(request, sociallogin)

        self.assertEqual(user, sociallogin.user)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)

    def test_pre_social_login_connects_existing_user_with_case_mismatch(self):
        user = User.objects.create_user(
            email="User@unicef.org",
            password=self.default_password,
            first_name="Test",
            last_name="User",
        )
        EmailAddress.objects.filter(user=user).update(verified=False)

        request = self._make_request()
        sociallogin = self._make_sociallogin("user@unicef.org")

        self.adapter.pre_social_login(request, sociallogin)

        self.assertEqual(user, sociallogin.user)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)

    def test_pre_social_login_keeps_verified_email_for_existing_user(self):
        user = User.objects.create_user(
            email="verified@unicef.org",
            password=self.default_password,
            first_name="Test",
            last_name="User",
        )
        EmailAddress.objects.update_or_create(user=user, email=user.email, defaults={"verified": True, "primary": True})

        request = self._make_request()
        sociallogin = self._make_sociallogin("verified@unicef.org")

        self.adapter.pre_social_login(request, sociallogin)

        self.assertEqual(user, sociallogin.user)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)

    def test_save_user_marks_new_user_email_as_verified(self):
        request = self._make_request()
        sociallogin = self._make_sociallogin("newuser@unicef.org")
        user = User.objects.create_user(
            email="newuser@unicef.org",
            password=self.default_password,
            first_name="New",
            last_name="User",
        )

        with patch.object(DefaultSocialAccountAdapter, "save_user", return_value=user):
            saved_user = self.adapter.save_user(request, sociallogin)

        self.assertEqual(user, saved_user)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)

    def test_post_login_accepts_invite_with_case_insensitive_email(self):
        invitation = Invitation.create(self.org, self.admin, "User@unicef.org", OrgRole.EDITOR)
        user = User.create("user@unicef.org", "Test", "User", password=self.default_password)

        request = self._make_request()
        request.session["invite_secret"] = invitation.secret
        self.adapter.request = request

        with patch.object(DefaultAccountAdapter, "post_login", return_value=None):
            self.adapter.post_login(
                request,
                user,
                email_verification=None,
                signal_kwargs={},
                email=user.email,
                signup=False,
                redirect_url="/org/choose/",
            )

        invitation.refresh_from_db()
        self.assertFalse(invitation.is_active)
        self.assertTrue(user.get_orgs().filter(id=self.org.id).exists())

    def test_post_login_does_not_accept_invite_with_different_email(self):
        invitation = Invitation.create(self.org, self.admin, "other@unicef.org", OrgRole.EDITOR)
        user = User.create("user@unicef.org", "Test", "User", password=self.default_password)

        request = self._make_request()
        request.session["invite_secret"] = invitation.secret
        self.adapter.request = request

        with patch.object(DefaultAccountAdapter, "post_login", return_value=None):
            self.adapter.post_login(
                request,
                user,
                email_verification=None,
                signal_kwargs={},
                email=user.email,
                signup=False,
                redirect_url="/org/choose/",
            )

        invitation.refresh_from_db()
        self.assertTrue(invitation.is_active)
        self.assertFalse(user.get_orgs().filter(id=self.org.id).exists())

        messages = [str(m.message) for m in get_messages(request)]
        self.assertTrue(any("other@unicef.org" in message for message in messages))
