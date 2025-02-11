from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.urls import re_path
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog

from temba.channels.views import register, sync

from .views import WeniRedirect

# javascript translation packages
js_info_dict = {"packages": ()}  # this is empty due to the fact that all translation are in one folder

urlpatterns = [
    re_path(r"^", include("temba.airtime.urls")),
    re_path(r"^", include("temba.api.urls")),
    re_path(r"^", include("temba.apks.urls")),
    re_path(r"^", include("temba.archives.urls")),
    re_path(r"^", include("temba.campaigns.urls")),
    re_path(r"^", include("temba.channels.urls")),
    re_path(r"^", include("temba.classifiers.urls")),
    re_path(r"^", include("temba.contacts.urls")),
    re_path(r"^", include("temba.dashboard.urls")),
    re_path(r"^", include("temba.flows.urls")),
    re_path(r"^", include("temba.globals.urls")),
    re_path(r"^", include("temba.ivr.urls")),
    re_path(r"^", include("temba.locations.urls")),
    re_path(r"^", include("temba.msgs.urls")),
    re_path(r"^", include("temba.notifications.urls")),
    re_path(r"^", include("temba.policies.urls")),
    re_path(r"^", include("temba.public.urls")),
    re_path(r"^", include("temba.request_logs.urls")),
    re_path(r"^", include("temba.schedules.urls")),
    re_path(r"^", include("temba.tickets.urls")),
    re_path(r"^", include("temba.triggers.urls")),
    re_path(r"^", include("temba.orgs.urls")),
    re_path(r"^relayers/relayer/sync/(\d+)/$", sync, {}, "sync"),
    re_path(r"^relayers/relayer/register/$", register, {}, "register"),
    re_path(r"users/user/forget/", RedirectView.as_view(pattern_name="orgs.user_forget", permanent=True)),
    re_path(r"^users/", include("smartmin.users.urls")),
    re_path(r"^imports/", include("smartmin.csv_imports.urls")),
    re_path(r"^assets/", include("temba.assets.urls")),
    re_path(r"^jsi18n/$", JavaScriptCatalog.as_view(), js_info_dict, name="django.views.i18n.javascript_catalog"),
    re_path(r"^redirect/", WeniRedirect.as_view(), {}, "weni.redirect"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# import any additional urls
for app in settings.APP_URLS:  # pragma: needs cover
    urlpatterns.append(re_path(r"^", include(app)))


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.

    Templates: `500.html`
    Context: None
    """
    from sentry_sdk import last_event_id

    from django.http import HttpResponseServerError
    from django.template import loader

    from .context_processors_weni import use_weni_layout
    from .settings import BRANDING, DEFAULT_BRAND

    weni_layout = use_weni_layout(request)

    t = loader.get_template("500.html")
    return HttpResponseServerError(
        t.render(
            {
                "request": request,
                "brand": BRANDING[DEFAULT_BRAND],
                "use_weni_layout": weni_layout["use_weni_layout"],
                "sentry_id": last_event_id(),
            }
        )
    )
