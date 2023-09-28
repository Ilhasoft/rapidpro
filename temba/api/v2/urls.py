from rest_framework.urlpatterns import format_suffix_patterns

from django.urls import re_path

from .views import (
    ArchivesEndpoint,
    AuthenticateView,
    BoundariesEndpoint,
    BroadcastsEndpoint,
    CampaignEventsEndpoint,
    CampaignsEndpoint,
    ChannelEventsEndpoint,
    ChannelsEndpoint,
    ClassifiersEndpoint,
    ContactActionsEndpoint,
    ContactsEndpoint,
    DefinitionsEndpoint,
    ExplorerView,
    FieldsEndpoint,
    FlowsEndpoint,
    FlowStartsEndpoint,
    GlobalsEndpoint,
    GroupsEndpoint,
    LabelsEndpoint,
    MediaEndpoint,
    MessageActionsEndpoint,
    MessagesEndpoint,
    OptInsEndpoint,
    ResthookEventsEndpoint,
    ResthooksEndpoint,
    ResthookSubscribersEndpoint,
    RootView,
    RunsEndpoint,
    TemplatesEndpoint,
    TicketActionsEndpoint,
    TicketersEndpoint,
    TicketsEndpoint,
    TopicsEndpoint,
    UsersEndpoint,
    WorkspaceEndpoint,
)

urlpatterns = [
    re_path(r"^$", RootView.as_view(), name="api.v2"),
    re_path(r"^explorer/$", ExplorerView.as_view(), name="api.v2.explorer"),
    re_path(r"^authenticate$", AuthenticateView.as_view(), name="api.v2.authenticate"),
    # ========== endpoints A-Z ===========
    re_path(r"^archives$", ArchivesEndpoint.as_view(), name="api.v2.archives"),
    re_path(r"^boundaries$", BoundariesEndpoint.as_view(), name="api.v2.boundaries"),
    re_path(r"^broadcasts$", BroadcastsEndpoint.as_view(), name="api.v2.broadcasts"),
    re_path(r"^campaigns$", CampaignsEndpoint.as_view(), name="api.v2.campaigns"),
    re_path(r"^campaign_events$", CampaignEventsEndpoint.as_view(), name="api.v2.campaign_events"),
    re_path(r"^channels$", ChannelsEndpoint.as_view(), name="api.v2.channels"),
    re_path(r"^channel_events$", ChannelEventsEndpoint.as_view(), name="api.v2.channel_events"),
    re_path(r"^classifiers$", ClassifiersEndpoint.as_view(), name="api.v2.classifiers"),
    re_path(r"^contacts$", ContactsEndpoint.as_view(), name="api.v2.contacts"),
    re_path(r"^contact_actions$", ContactActionsEndpoint.as_view(), name="api.v2.contact_actions"),
    re_path(r"^definitions$", DefinitionsEndpoint.as_view(), name="api.v2.definitions"),
    re_path(r"^fields$", FieldsEndpoint.as_view(), name="api.v2.fields"),
    re_path(r"^flow_starts$", FlowStartsEndpoint.as_view(), name="api.v2.flow_starts"),
    re_path(r"^flows$", FlowsEndpoint.as_view(), name="api.v2.flows"),
    re_path(r"^globals$", GlobalsEndpoint.as_view(), name="api.v2.globals"),
    re_path(r"^groups$", GroupsEndpoint.as_view(), name="api.v2.groups"),
    re_path(r"^labels$", LabelsEndpoint.as_view(), name="api.v2.labels"),
    re_path(r"^media$", MediaEndpoint.as_view(), name="api.v2.media"),
    re_path(r"^messages$", MessagesEndpoint.as_view(), name="api.v2.messages"),
    re_path(r"^message_actions$", MessageActionsEndpoint.as_view(), name="api.v2.message_actions"),
    re_path(r"^optins$", OptInsEndpoint.as_view(), name="api.v2.optins"),
    re_path(r"^org$", WorkspaceEndpoint.as_view(), name="api.v2.org"),  # deprecated
    re_path(r"^resthooks$", ResthooksEndpoint.as_view(), name="api.v2.resthooks"),
    re_path(r"^resthook_events$", ResthookEventsEndpoint.as_view(), name="api.v2.resthook_events"),
    re_path(r"^resthook_subscribers$", ResthookSubscribersEndpoint.as_view(), name="api.v2.resthook_subscribers"),
    re_path(r"^runs$", RunsEndpoint.as_view(), name="api.v2.runs"),
    re_path(r"^templates$", TemplatesEndpoint.as_view(), name="api.v2.templates"),
    re_path(r"^ticketers$", TicketersEndpoint.as_view(), name="api.v2.ticketers"),
    re_path(r"^tickets$", TicketsEndpoint.as_view(), name="api.v2.tickets"),
    re_path(r"^ticket_actions$", TicketActionsEndpoint.as_view(), name="api.v2.ticket_actions"),
    re_path(r"^topics$", TopicsEndpoint.as_view(), name="api.v2.topics"),
    re_path(r"^users$", UsersEndpoint.as_view(), name="api.v2.users"),
    re_path(r"^workspace$", WorkspaceEndpoint.as_view(), name="api.v2.workspace"),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=["json"])
