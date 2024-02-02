from unittest.mock import MagicMock, Mock, patch

import requests
from django_redis import get_redis_connection

from django.conf import settings
from django.utils import timezone

from temba.channels.models import Channel
from temba.channels.types.whatsapp.type import (
    CONFIG_FB_ACCESS_TOKEN,
    CONFIG_FB_BUSINESS_ID,
    CONFIG_FB_NAMESPACE,
    CONFIG_FB_TEMPLATE_LIST_DOMAIN,
)
from temba.request_logs.models import HTTPLog
from temba.templates.models import Template, TemplateTranslation
from temba.tests import TembaTest
from temba.tests.requests import MockResponse
from temba.wpp_products.models import Catalog, Product

from . import update_api_version
from .tasks import (
    _calculate_variable_count,
    refresh_whatsapp_catalog_and_products,
    sent_products_to_sentenx,
    sent_trim_products_to_sentenx,
    update_is_active_catalog,
    update_local_catalogs,
    update_local_products,
    update_local_templates,
)


class WhatsAppUtilsTest(TembaTest):
    def test_calculate_variable_count(self):
        self.assertEqual(2, _calculate_variable_count("Hi {{1}} how are you? {{2}}"))
        self.assertEqual(2, _calculate_variable_count("Hi {{1}} how are you? {{2}} {{1}}"))
        self.assertEqual(0, _calculate_variable_count("Hi there."))

    def test_update_local_templates_whatsapp(self):
        # channel has namespace in the channel config
        channel = self.create_channel("WA", "channel", "1234", config={"fb_namespace": "foo_namespace"})

        self.assertEqual(0, Template.objects.filter(org=self.org).count())
        self.assertEqual(0, TemplateTranslation.objects.filter(channel=channel).count())

        # no namespace in template data, use channel config namespace
        WA_templates_data = [
            {
                "name": "hello",
                "components": [{"type": "BODY", "text": "Hello {{1}}"}],
                "language": "en",
                "status": "PENDING",
                "category": "ISSUE_RESOLUTION",
                "id": "1234",
            },
            {
                "name": "hello",
                "components": [{"type": "BODY", "text": "Hi {{1}}"}],
                "language": "en_GB",
                "status": "PENDING",
                "category": "ISSUE_RESOLUTION",
                "id": "4321",
            },
            {
                "name": "hello",
                "components": [{"type": "BODY", "text": "Bonjour {{1}}"}],
                "language": "fr",
                "status": "APPROVED",
                "category": "ISSUE_RESOLUTION",
                "id": "5678",
            },
            {
                "name": "goodbye",
                "components": [{"type": "BODY", "text": "Goodbye {{1}}, see you on {{2}}. See you later {{1}}"}],
                "language": "en",
                "status": "PENDING",
                "category": "ISSUE_RESOLUTION",
                "id": "9012",
            },
            {
                "name": "workout_activity",
                "components": [
                    {"type": "HEADER", "format": "text", "text": "Workout challenge week extra points!"},
                    {
                        "type": "BODY",
                        "text": "Hey {{1}}, Week {{2}} workout is out now. Get your discount of {{3}} for the next workout by sharing this program to 3 people.",
                    },
                    {"type": "FOOTER", "text": "Remember to drink water."},
                    {
                        "type": "BUTTONS",
                        "buttons": [
                            {"type": "QUICK_REPLY", "text": "Clique aqui - Segunda via"},
                            {"type": "QUICK_REPLY", "text": "Tirth", "url": "https://example.com"},
                        ],
                    },
                ],
                "language": "en",
                "status": "PENDING",
                "category": "ISSUE_RESOLUTION",
                "id": "9014",
            },
            {
                "name": "workout_activity_with_unsuported_variablet",
                "components": [
                    {"type": "HEADER", "text": "Workout challenge week {{2}}, {{4}} extra points!"},
                    {
                        "type": "BODY",
                        "text": "Hey {{1}}, Week {{2}} workout is out now. Get your discount of {{3}} for the next workout by sharing this program to 3 people.",
                    },
                    {"type": "FOOTER", "text": "Remember to drink water."},
                    {
                        "type": "BUTTONS",
                        "buttons": [
                            {"type": "QUICK_REPLY", "text": "Clique aqui - Segunda via"},
                            {"type": "QUICK_REPLY", "text": "Tirth", "url": "https://example.com"},
                        ],
                    },
                ],
                "language": "en",
                "status": "PENDING",
                "category": "ISSUE_RESOLUTION",
                "id": "9014",
            },
            {
                "name": "missing_text_component",
                "components": [
                    {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["FOO"]}},
                    {
                        "type": "BUTTONS",
                        "buttons": [
                            {"type": "QUICK_REPLY", "text": "Clique aqui - Segunda via"},
                            {"type": "QUICK_REPLY", "text": "Tirth", "url": "https://example.com"},
                        ],
                    },
                ],
                "language": "en",
                "status": "APPROVED",
                "category": "ISSUE_RESOLUTION",
                "id": "1235",
            },
            {
                "name": "invalid_component",
                "components": [{"type": "RANDOM", "text": "Bonjour {{1}}"}],
                "language": "fr",
                "status": "APPROVED",
                "category": "ISSUE_RESOLUTION",
                "id": "1233",
            },
            {
                "name": "invalid_status",
                "components": [{"type": "BODY", "text": "This is an unknown status, it will be ignored"}],
                "language": "en",
                "status": "UNKNOWN",
                "category": "ISSUE_RESOLUTION",
                "id": "9012",
            },
            {
                "name": "invalid_language",
                "components": [{"type": "BODY", "text": "This is an unknown language, it will be ignored"}],
                "language": "kli",
                "status": "APPROVED",
                "category": "ISSUE_RESOLUTION",
                "id": "9018",
            },
        ]

        update_local_templates(channel, WA_templates_data)

        self.assertEqual(4, Template.objects.filter(org=self.org).count())
        self.assertEqual(6, TemplateTranslation.objects.filter(channel=channel).count())
        self.assertEqual(6, TemplateTranslation.objects.filter(channel=channel, namespace="foo_namespace").count())

        ct = TemplateTranslation.objects.get(template__name="goodbye", is_active=True)
        self.assertEqual(2, ct.variable_count)
        self.assertEqual("Goodbye {{1}}, see you on {{2}}. See you later {{1}}", ct.content)
        self.assertEqual("eng", ct.language)
        self.assertEqual(TemplateTranslation.STATUS_PENDING, ct.status)
        self.assertEqual("goodbye (eng []) P: Goodbye {{1}}, see you on {{2}}. See you later {{1}}", str(ct))
        self.assertEqual("foo_namespace", ct.namespace)

        ct = TemplateTranslation.objects.get(template__name="workout_activity", is_active=True)
        self.assertEqual(3, ct.variable_count)
        self.assertEqual(
            "Workout challenge week extra points!\n\nHey {{1}}, Week {{2}} workout is out now. Get your discount of {{3}} for the next workout by sharing this program to 3 people.\n\nRemember to drink water.",
            ct.content,
        )
        self.assertEqual("eng", ct.language)
        self.assertEqual(TemplateTranslation.STATUS_PENDING, ct.status)
        self.assertEqual("foo_namespace", ct.namespace)

        # assert that a template translation was created despite it being in an unknown language
        ct = TemplateTranslation.objects.get(template__name="invalid_language", is_active=True)
        self.assertEqual("kli", ct.language)
        self.assertEqual(TemplateTranslation.STATUS_UNSUPPORTED_LANGUAGE, ct.status)
        self.assertEqual("foo_namespace", ct.namespace)

    def test_update_local_templates_dialog360(self):
        # no namespace in channel config
        channel = self.create_channel("D3", "channel", "1234", config={})

        # no template id, use language/name as external ID
        # template data have namespaces
        D3_templates_data = [
            {
                "name": "hello",
                "components": [{"type": "BODY", "text": "Hello {{1}}"}],
                "language": "en",
                "status": "pending",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "hello",
                "components": [{"type": "BODY", "text": "Hi {{1}}"}],
                "language": "en_GB",
                "status": "pending",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "hello",
                "components": [{"type": "BODY", "text": "Bonjour {{1}}"}],
                "language": "fr",
                "status": "approved",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "goodbye",
                "components": [{"type": "BODY", "text": "Goodbye {{1}}, see you on {{2}}. See you later {{1}}"}],
                "language": "en",
                "status": "PENDING",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "workout_activity",
                "components": [
                    {"type": "HEADER", "format": "text", "text": "Workout challenge week extra points!"},
                    {
                        "type": "BODY",
                        "text": "Hey {{1}}, Week {{2}} workout is out now. Get your discount of {{3}} for the next workout by sharing this program to 3 people.",
                    },
                    {"type": "FOOTER", "text": "Remember to drink water."},
                ],
                "language": "en",
                "status": "PENDING",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "workout_activity_with_unsuported_variablet",
                "components": [
                    {"type": "HEADER", "format": "text", "text": "Workout challenge week {{2}}, {{4}} extra points!"},
                    {
                        "type": "BODY",
                        "text": "Hey {{1}}, Week {{2}} workout is out now. Get your discount of {{3}} for the next workout by sharing this program to 3 people.",
                    },
                    {"type": "FOOTER", "text": "Remember to drink water."},
                    {
                        "type": "BUTTONS",
                        "buttons": [
                            {"type": "QUICK_REPLY", "text": "Clique aqui - Segunda via"},
                            {"type": "QUICK_REPLY", "text": "Tirth", "url": "https://example.com"},
                        ],
                    },
                ],
                "language": "en",
                "status": "PENDING",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "missing_text_component",
                "components": [
                    {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["FOO"]}},
                    {
                        "type": "BUTTONS",
                        "buttons": [
                            {"type": "QUICK_REPLY", "text": "Clique aqui - Segunda via"},
                            {"type": "QUICK_REPLY", "text": "Tirth", "url": "https://example.com"},
                        ],
                    },
                ],
                "language": "en",
                "status": "APPROVED",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "invalid_component",
                "components": [{"type": "RANDOM", "text": "Bonjour {{1}}"}],
                "language": "fr",
                "status": "APPROVED",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "invalid_status",
                "components": [{"type": "BODY", "text": "This is an unknown status, it will be ignored"}],
                "language": "en",
                "status": "UNKNOWN",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
            {
                "name": "invalid_language",
                "components": [{"type": "BODY", "text": "This is an unknown language, it will be ignored"}],
                "language": "kli",
                "status": "APPROVED",
                "namespace": "xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx",
                "rejected_reason": "NONE",
                "category": "ISSUE_RESOLUTION",
            },
        ]

        update_local_templates(channel, D3_templates_data)

        self.assertEqual(4, Template.objects.filter(org=self.org).count())
        self.assertEqual(6, TemplateTranslation.objects.filter(channel=channel).count())
        self.assertEqual(0, TemplateTranslation.objects.filter(channel=channel, namespace="").count())
        self.assertEqual(0, TemplateTranslation.objects.filter(channel=channel, namespace=None).count())
        self.assertEqual(
            sorted(
                ["en/hello", "en_GB/hello", "fr/hello", "en/goodbye", "en/workout_activity", "kli/invalid_language"]
            ),
            sorted(list(TemplateTranslation.objects.filter(channel=channel).values_list("external_id", flat=True))),
        )

        tt = TemplateTranslation.objects.filter(channel=channel, external_id="en/hello").first()
        self.assertEqual("xxxxxxxx_xxxx_xxxx_xxxx_xxxxxxxxxxxx", tt.namespace)

    @patch("temba.channels.types.whatsapp.WhatsAppType.check_health")
    def test_update_api_version_whatsapp(self, mock_health):
        mock_health.return_value = MockResponse(200, '{"meta": {"api_status": "stable", "version": "v2.35.2"}}')

        Channel.objects.all().delete()
        channel = self.create_channel(
            "WA",
            "WhatsApp: 1234",
            "1234",
            config={
                Channel.CONFIG_BASE_URL: "https://nyaruka.com/whatsapp",
                Channel.CONFIG_USERNAME: "temba",
                Channel.CONFIG_PASSWORD: "tembapasswd",
                Channel.CONFIG_AUTH_TOKEN: "authtoken123",
                CONFIG_FB_BUSINESS_ID: "1234",
                CONFIG_FB_ACCESS_TOKEN: "token123",
                CONFIG_FB_NAMESPACE: "my-custom-app",
                CONFIG_FB_TEMPLATE_LIST_DOMAIN: "graph.facebook.com",
            },
        )

        update_api_version(channel)
        mock_health.assert_called_with(channel)

        channel.refresh_from_db()
        self.assertDictContainsSubset({"version": "v2.35.2"}, channel.config)

        self.assertEqual(0, HTTPLog.objects.filter(log_type=HTTPLog.WHATSAPP_CHECK_HEALTH).count())
        mock_health.side_effect = [requests.RequestException(response=MockResponse(401, "{}"))]
        update_api_version(channel)
        self.assertEqual(1, HTTPLog.objects.filter(log_type=HTTPLog.WHATSAPP_CHECK_HEALTH).count())

    @patch("temba.channels.types.dialog360.Dialog360Type.check_health")
    def test_update_api_version_dialog360(self, mock_health):
        mock_health.return_value = MockResponse(200, '{"meta": {"api_status": "stable", "version": "2.35.4"}}')

        Channel.objects.all().delete()
        channel = self.create_channel(
            "D3",
            "360Dialog channel",
            address="1234",
            country="BR",
            config={
                Channel.CONFIG_BASE_URL: "https://example.com/whatsapp",
                Channel.CONFIG_AUTH_TOKEN: "123456789",
            },
        )

        update_api_version(channel)
        mock_health.assert_called_with(channel)

        channel.refresh_from_db()
        self.assertDictContainsSubset({"version": "v2.35.4"}, channel.config)

        self.assertEqual(0, HTTPLog.objects.filter(log_type=HTTPLog.WHATSAPP_CHECK_HEALTH).count())
        mock_health.side_effect = [requests.RequestException(response=MockResponse(401, "{}"))]
        update_api_version(channel)
        self.assertEqual(1, HTTPLog.objects.filter(log_type=HTTPLog.WHATSAPP_CHECK_HEALTH).count())


class UpdateLocalProductsTest(TembaTest):
    def test_update_local_products(self):
        catalog = Catalog(name="Test Catalog", org=self.org, channel=self.channel, facebook_catalog_id=1)

        catalog.channel.get_type().code = "WAC"
        catalog.save()

        products_data = [
            {"id": 1, "name": "Product A", "retailer_id": 123},
            {"id": 2, "name": "Product B", "retailer_id": 456},
        ]

        update_local_products(catalog, products_data, self.channel)

        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(Product.objects.filter(catalog=catalog).count(), 2)


class RefreshWhatsappCatalogAndProductsTestCase(TembaTest):
    @patch("temba.utils.whatsapp.tasks.update_local_products")
    @patch("temba.utils.whatsapp.tasks.update_local_catalogs")
    @patch("temba.channels.types.whatsapp_cloud.type.WhatsAppCloudType.get_api_products")
    @patch("temba.channels.types.whatsapp_cloud.type.WhatsAppCloudType.get_api_catalogs")
    def test_refresh_catalogs_and_products_task(
        self, mock_get_api_catalogs, mock_get_api_products, update_local_catalogs_mock, update_local_products_mock
    ):
        Catalog.objects.all().delete()
        Product.objects.all().delete()
        Channel.objects.all().delete()

        channel = self.create_channel("WAC", "Test WAC Channel", "54764868534")

        Catalog.objects.create(
            facebook_catalog_id="123456789",
            name="Catalog1",
            org=self.org,
            channel=channel,
            created_on=timezone.now(),
            modified_on=timezone.now(),
            is_active=True,
        )

        self.login(self.admin)

        mock_get_api_products.side_effect = [
            ([], False),
            ([], True),
        ]

        update_local_catalogs_mock.return_value = None
        update_local_products_mock.return_value = None

        r = get_redis_connection()
        with r.lock("refresh_whatsapp_catalog_and_products", timeout=1800):
            refresh_whatsapp_catalog_and_products()
            self.assertEqual(0, mock_get_api_catalogs.call_count)
            self.assertEqual(0, mock_get_api_products.call_count)
            self.assertEqual(0, update_local_catalogs_mock.call_count)
            self.assertEqual(0, update_local_products_mock.call_count)

        refresh_whatsapp_catalog_and_products()

        refresh_whatsapp_catalog_and_products()

        refresh_whatsapp_catalog_and_products()

        self.assertEqual(1, update_local_products_mock.call_count)


class UpdateIsActiveCatalogTestCase(TembaTest):
    @patch("temba.utils.whatsapp.tasks.requests.get")
    def test_update_is_active_catalog(self, mock_requests_get):
        mock_response = {
            "data": [
                {"id": "catalog1"},
                {"id": "catalog2"},
            ]
        }
        mock_requests_get.return_value.json.return_value = mock_response

        config = {"wa_waba_id": "1111111111111", "wa_business_id": "2222222222"}

        channel = self.channel
        channel.get_type().code = "WAC"
        channel.config = config

        catalogs_data = [
            {"name": "Catalog1", "id": "catalog1", "is_active": True},
            {"name": "Catalog2", "id": "catalog2", "is_active": False},
            {"name": "Catalog3", "id": "catalog3", "is_active": False},
        ]

        update_local_catalogs(channel, catalogs_data)

        self.assertEqual(Catalog.objects.count(), 3)

    @patch("temba.utils.whatsapp.tasks.requests.get")
    def test_update_is_active_catalog_empty_catalog(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_requests_get.return_value = mock_response

        # Chamada da função a ser testada
        class FakeChannel:
            def __init__(self):
                self.config = {"wa_waba_id": "123456"}
                self.catalogs = []
                self.save = MagicMock()

        # Chamada da função a ser testada
        channel = FakeChannel()
        catalogs_data = []  # Adicione dados fictícios conforme necessário
        result = update_is_active_catalog(channel, catalogs_data)

        # Asserções
        self.assertEqual(channel.config["catalog_id"], "")
        self.assertTrue(channel.save.called)
        self.assertEqual(result, catalogs_data)
        #self.assertFalse(channel.catalogs.filter.called)


    @patch("temba.utils.whatsapp.tasks.requests.get")
    def test_update_is_active_catalog_waba_error(self, mock_requests_get):
        mock_response = {
            "data": [
                {"id": "catalog1"},
                {"id": "catalog2"},
            ]
        }
        mock_requests_get.return_value.json.return_value = mock_response

        config = {"wa_business_id": "2222222222"}

        channel = self.channel
        channel.config = config

        catalogs_data = [
            {"id": "catalog1", "is_active": True},
            {"id": "catalog2", "is_active": False},
            {"id": "catalog3", "is_active": False},
        ]

        with self.assertRaises(ValueError):
            update_is_active_catalog(channel, catalogs_data)


class SentenxTestCase(TembaTest):
    def setUp(self):
        super().setUp()
        self.new_channel = self.create_channel("WAC", "Test WAC Channel", "54764868534")
        self.catalog = Catalog.objects.create(
            facebook_catalog_id="987654321",
            name="Catalog1",
            org=self.org,
            channel=self.new_channel,
            created_on=timezone.now(),
            modified_on=timezone.now(),
            is_active=True,
        )
        self.product1 = Product.objects.create(
            facebook_product_id="123",
            title="Existing Product 1",
            product_retailer_id="product-1",
            catalog=self.catalog,
        )
        self.product2 = Product.objects.create(
            facebook_product_id="456",
            title="Existing Product 2",
            product_retailer_id="product-2",
            catalog=self.catalog,
        )
        self.products = [self.product1, self.product2]

    def test_sent_products_to_sentenx_success(self):
        settings.SENTENX_URL = "https://example.com"
        products = [{"product_id": 1, "name": "Product 1"}, {"product_id": 2, "name": "Product 2"}]

        def mock_requests_put(*args, **kwargs):
            class MockResponse:
                status_code = 200

            return MockResponse()

        requests.put = mock_requests_put

        sent_products_to_sentenx(products)

    def test_sent_products_to_sentenx_failure(self):
        settings.SENTENX_URL = "https://example.com"
        products = [{"product_id": 1, "name": "Product 1"}, {"product_id": 2, "name": "Product 2"}]

        def mock_requests_put(*args, **kwargs):
            class MockResponse:
                status_code = 400

            return MockResponse()

        requests.put = mock_requests_put

        with self.assertRaises(Exception):
            sent_products_to_sentenx(products)

    def test_sent_products_to_sentenx_no_sentenx_url(self):
        settings.SENTENX_URL = ""

        with self.assertRaises(Exception) as context:
            sent_products_to_sentenx([])

        self.assertEqual(str(context.exception), "Not found SENTENX_URL")

    def test_sent_trim_products_to_sentenx_success(self):
        settings.SENTENX_URL = "https://example.com"

        with patch("requests.delete") as mock_delete:
            mock_response = mock_delete.return_value
            mock_response.status_code = 200

            sent_trim_products_to_sentenx(self.catalog, self.products)

    def test_sent_trim_products_to_sentenx_no_products_to_delete(self):
        settings.SENTENX_URL = "https://example.com"

        with patch("requests.delete") as mock_delete:
            mock_response = mock_delete.return_value
            mock_response.status_code = 200

            sent_trim_products_to_sentenx(self.catalog, [])

    def test_sent_trim_products_to_sentenx_failure(self):
        settings.SENTENX_URL = "https://example.com"
        mock_response = Mock()
        mock_response.status_code = 400

        with patch("requests.delete", return_value=mock_response):
            with self.assertRaises(Exception):
                sent_trim_products_to_sentenx(self.catalog, [])

    def test_sent_trim_products_to_sentenx_no_sentenx_url(self):
        settings.SENTENX_URL = ""

        with self.assertRaises(Exception) as context:
            sent_trim_products_to_sentenx(self.catalog, self.products)

        self.assertEqual(str(context.exception), "Not found SENTENX_URL")
