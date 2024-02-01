import logging
import re
import time

import requests
from django_redis import get_redis_connection
from rest_framework.response import Response

from django.conf import settings
from django.utils import timezone

from celery import shared_task

from temba.channels.models import Channel
from temba.contacts.models import URN, Contact, ContactURN
from temba.request_logs.models import HTTPLog
from temba.templates.models import Template, TemplateButton, TemplateHeader, TemplateTranslation
from temba.utils import chunk_list
from temba.wpp_products.models import Catalog, Product

from . import update_api_version
from .constants import LANGUAGE_MAPPING, STATUS_MAPPING

logger = logging.getLogger(__name__)


@shared_task(track_started=True, name="refresh_whatsapp_contacts")
def refresh_whatsapp_contacts(channel_id):
    r = get_redis_connection()
    key = "refresh_whatsapp_contacts_%d" % channel_id

    # we can't use our non-overlapping task decorator as it creates a loop in the celery resolver when registering
    if r.get(key):  # pragma: no cover
        return

    channel = Channel.objects.filter(id=channel_id, is_active=True).first()
    if not channel:  # pragma: no cover
        return

    with r.lock(key, 3600):
        # look up all whatsapp URNs for this channel
        wa_urns = (
            ContactURN.objects.filter(
                org_id=channel.org_id, scheme=URN.WHATSAPP_SCHEME, contact__status=Contact.STATUS_ACTIVE
            )
            .exclude(contact=None)
            .only("id", "path")
        )

        # 1,000 contacts at a time, we ask WhatsApp to look up our contacts based on the path
        refreshed = 0

        for urn_batch in chunk_list(wa_urns, 1000):
            # need to wait 10 seconds between each batch of 1000
            if refreshed > 0:  # pragma: no cover
                time.sleep(10)

            # build a list of the fully qualified numbers we have
            contacts = ["+%s" % u.path for u in urn_batch]
            payload = {"blocking": "wait", "contacts": contacts}

            # go fetch our contacts
            headers = {"Authorization": "Bearer %s" % channel.config[Channel.CONFIG_AUTH_TOKEN]}
            url = channel.config[Channel.CONFIG_BASE_URL] + "/v1/contacts"

            start = timezone.now()
            resp = requests.post(url, json=payload, headers=headers)
            elapsed = (timezone.now() - start).total_seconds() * 1000

            HTTPLog.create_from_response(
                HTTPLog.WHATSAPP_CONTACTS_REFRESHED, url, resp, channel=channel, request_time=elapsed
            )

            # if we had an error, break out
            if resp.status_code != 200:
                break

            refreshed += len(urn_batch)

        print("refreshed %d whatsapp urns for channel %d" % (refreshed, channel_id))


VARIABLE_RE = re.compile(r"{{(\d+)}}")


def _calculate_variable_count(content):
    """
    Utility method that extracts the number of variables in the passed in WhatsApp template
    """
    count = 0

    for match in VARIABLE_RE.findall(content):
        if int(match) > count:
            count = int(match)

    return count


def update_local_templates(channel, templates_data):
    channel_namespace = channel.config.get("fb_namespace", "")
    # run through all our templates making sure they are present in our DB
    seen = []
    for template in templates_data:
        template_status = template["status"]

        template_status = template_status.upper()
        # if this is a status we don't know about
        if template_status not in STATUS_MAPPING:
            continue

        status = STATUS_MAPPING[template_status]

        content_parts = []

        all_supported = True
        for component in template["components"]:
            if component["type"] not in ["HEADER", "BODY", "FOOTER"]:
                continue

            if "text" not in component:
                continue

            if component["type"] in ["HEADER", "FOOTER"] and _calculate_variable_count(component["text"]):
                all_supported = False

            content_parts.append(component["text"])

        if not content_parts or not all_supported:
            continue

        content = "\n\n".join(content_parts)
        variable_count = _calculate_variable_count(content)

        language, country = LANGUAGE_MAPPING.get(template["language"], (None, None))

        # its a (non fatal) error if we see a language we don't know
        if language is None:
            status = TemplateTranslation.STATUS_UNSUPPORTED_LANGUAGE
            language = template["language"]

        missing_external_id = f"{template['language']}/{template['name']}"
        translation = TemplateTranslation.get_or_create(
            channel=channel,
            name=template["name"],
            language=language,
            country=country,
            content=content,
            variable_count=variable_count,
            status=status,
            external_id=template.get("id", missing_external_id),
            namespace=template.get("namespace", channel_namespace),
            category=template["category"],
        )

        for component in template["components"]:
            if component["type"] == "HEADER":
                TemplateHeader.objects.get_or_create(
                    translation=translation, type=component.get("format"), text=component.get("text", None)
                )

            if component["type"] == "BUTTONS":
                for button in component.get("buttons"):
                    TemplateButton.objects.get_or_create(
                        translation=translation,
                        type=button.get("type"),
                        url=button.get("url", None),
                        text=button.get("text", None),
                        phone_number=button.get("phone_number", None),
                    )

        seen.append(translation)

    # trim any translations we didn't see
    TemplateTranslation.trim(channel, seen)
    Template.trim(channel)


@shared_task(track_started=True, name="refresh_whatsapp_templates")
def refresh_whatsapp_templates():
    """
    Runs across all WhatsApp templates that have connected FB accounts and syncs the templates which are active.
    """

    r = get_redis_connection()
    if r.get("refresh_whatsapp_templates"):  # pragma: no cover
        return

    with r.lock("refresh_whatsapp_templates", 1800):
        # for every whatsapp channel
        for channel in Channel.objects.filter(is_active=True, channel_type__in=["WA", "D3", "WAC"]):
            # update the version only when have it set in the config
            if channel.config.get("version"):
                # fetches API version and saves on channel.config
                update_api_version(channel)


def update_channel_catalogs_status(channel, facebook_catalog_id, is_active):
    channel.config["catalog_id"] = facebook_catalog_id if is_active else None
    channel.save(update_fields=["config"])

    Catalog.objects.filter(channel=channel, is_active=True).update(is_active=False)

    if is_active:
        Catalog.objects.filter(channel=channel, facebook_catalog_id=facebook_catalog_id).update(is_active=True)

    sync_products_catalogs(channel, facebook_catalog_id)

    return True

def sync_products_catalogs(channel, facebook_catalog_id):
        try:
            products_data, valid = channel.get_type().get_api_products(channel, facebook_catalog_id)

            catalog = Catalog.objects.filter(channel=channel, facebook_catalog_id=facebook_catalog_id)
            update_local_products(catalog, products_data, channel)

        except Exception as e:
            logger.error(f"Error refreshing WhatsApp catalog and products: {str(e)}", exc_info=True)


def set_false_is_active_catalog(channel, catalogs_data):
    channel.config["catalog_id"] = ""
    channel.save(update_fields=["config"])

    for catalog in catalogs_data:
        catalog.is_active = False
        catalog.save(update_fields=["is_active"])
    return catalogs_data


def update_is_active_catalog(channel, catalogs_data):
    waba_id = channel.config.get("wa_waba_id", None)
    if not waba_id:
        raise ValueError("Channel wa_waba_id not found")

    url = f"https://graph.facebook.com/v17.0/{waba_id}/product_catalogs"

    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ADMIN_SYSTEM_USER_TOKEN}"}
    resp = requests.get(url, params=dict(limit=255), headers=headers)

    if "error" in resp.json():
        set_false_is_active_catalog(channel, catalogs_data)
        logger.error(f"Error refreshing WhatsApp catalog and products: {str(resp.json())}", exc_info=True)

        return catalogs_data

    json_data = resp.json().get("data", [])
    if json_data and json_data[0].get("id"):
        actived_catalog = json_data[0]["id"]
    else:
        actived_catalog = None

    if actived_catalog is None or len(actived_catalog) == 0:
        set_false_is_active_catalog(channel, catalogs_data)
        return catalogs_data

    if actived_catalog:
        for catalog in catalogs_data:
            if catalog.facebook_catalog_id != actived_catalog:
                catalog.is_active = False

            else:
                catalog.is_active = True
            catalog.save(update_fields=["is_active"])

        verify_has_catalog_active = channel.catalogs.filter(is_active=True)
        if verify_has_catalog_active:
            channel.config["catalog_id"] = actived_catalog
            channel.save(update_fields=["config"])
        else:
            channel.config["catalog_id"] = ""
            channel.save(update_fields=["config"])

    return catalogs_data


def update_local_catalogs(channel, catalogs_data):
    seen = []
    for catalog in catalogs_data:
        new_catalog = Catalog.get_or_create(
            name=catalog.get("name"),
            channel=channel,
            is_active=False,
            facebook_catalog_id=catalog["id"],
        )

        seen.append(new_catalog)

    update_is_active_catalog(channel, seen)
    Catalog.trim(channel, seen)


def update_local_products(catalog, products_data, channel):
    seen = []
    products_sentenx = {"catalog_id": catalog.facebook_catalog_id, "products": []}

    for product in products_data:
        new_product = Product.get_or_create(
            facebook_product_id=product["id"],
            title=product["name"],
            product_retailer_id=product["retailer_id"],
            catalog=catalog,
            name=catalog.name,
            channel=channel,
            facebook_catalog_id=catalog.facebook_catalog_id,
        )

        seen.append(new_product)

        sentenx_object = {
            "facebook_id": new_product.facebook_product_id,
            "title": new_product.title,
            "org_id": str(catalog.org_id),
            "catalog_id": catalog.facebook_catalog_id,
            "product_retailer_id": new_product.product_retailer_id,
            "channel_id": str(catalog.channel_id),
        }

        products_sentenx["products"].append(sentenx_object)

    if len(products_sentenx["products"]) > 0:
        sent_products_to_sentenx(products_sentenx)
        sent_trim_products_to_sentenx(catalog, seen)

    Product.trim(catalog, seen)


@shared_task(track_started=True, name="refresh_whatsapp_catalog_and_products")
def refresh_whatsapp_catalog_and_products():
    """
    Fetches catalog data and associated products from Facebook's Graph API and syncs them to the local database.
    """
    r = get_redis_connection()
    if r.get("refresh_whatsapp_catalog_and_products"):  # pragma: no cover
        return

    with r.lock("refresh_whatsapp_catalog_and_products", 1800):
        try:
            for channel in Channel.objects.filter(is_active=True, channel_type="WAC"):
                for catalog in Catalog.objects.filter(channel=channel, is_active=True):
                    # Fetch products for each catalog
                    products_data, valid = channel.get_type().get_api_products(channel, catalog.facebook_catalog_id)
                    if not valid:
                        continue

                    update_local_products(catalog, products_data, channel)

        except Exception as e:
            logger.error(f"Error refreshing WhatsApp catalog and products: {str(e)}", exc_info=True)


def sent_products_to_sentenx(products):
    sentenx_url = settings.SENTENX_URL

    if sentenx_url:
        url = sentenx_url + "/products/batch"

        resp = requests.put(
            url,
            json=products,
        )

        if resp.status_code == 200:
            return Response("Products updated")
        else:
            raise Exception("Received non-200 response: %d", resp.status_code)

    else:
        raise Exception("Not found SENTENX_URL")


def sent_trim_products_to_sentenx(catalog, products):
    sentenx_url = settings.SENTENX_URL

    if sentenx_url:
        url = sentenx_url + "/products/batch"
        ids = [tc.id for tc in products]
        products_to_delete_list = list(
            Product.objects.filter(catalog=catalog).exclude(id__in=ids).values_list("product_retailer_id", flat=True)
        )

        if products_to_delete_list:
            payload = {
                "catalog_id": catalog.facebook_catalog_id,
                "product_retailer_ids": products_to_delete_list,
            }

            resp = requests.delete(
                url,
                json=payload,
            )

            if resp.status_code == 200:
                return Response("Products updated")
            else:
                raise Exception("Received non-200 response: %d", resp.status_code)

    else:
        raise Exception("Not found SENTENX_URL")
