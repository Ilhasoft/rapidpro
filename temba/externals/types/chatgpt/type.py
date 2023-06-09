import json

from django.utils.translation import ugettext_lazy as _

from temba.externals.models import ExternalServiceType, Prompt

from .serializers import ChatGPTSerializer
from .views import ConnectView


class ChatGPTType(ExternalServiceType):
    """
    Type for using chatgpt as a external service
    """

    CONFIG_API_KEY = "api_key"
    CONFIG_AI_MODEL = "ai_model"
    CONFIG_RULES = "rules"
    CONFIG_KNOWLEDGE_BASE = "knowledge_base"

    serializer_class = ChatGPTSerializer

    name = "ChatGPT"
    slug = "chatgpt"
    icon = "icon-power-cord"

    connect_view = ConnectView
    connect_blurb = _("chatgpt external service")

    def is_available_to(self, user):
        return True

    def get_actions(self):
        actions = super().get_actions()
        options_data = Prompt.objects.filter(chat_gpt_service_id=self.external_service.id)

        options_data_json = json.loads(json.dumps(list(options_data.values())))
        if options_data:
            actions[0]["params"][0]["options"].append(options_data_json)
            actions[0]["params"][0]["options"] = actions[0]["params"][0]["options"][0]

        return actions
