from amqp.channel import Channel  # pragma: no cover
from temba.projects.handle import handle_consumers as project_handle_consumers
from temba.classifiers.handle import handle_consumers as classifier_handle_consumers
from temba.tickets.handle import handle_consumers as ticketer_handle_consumers
# add todos os handles aqui

def handle_consumers(channel: Channel) -> None:  # pragma: no cover
    project_handle_consumers(channel)
    classifier_handle_consumers(channel)
    ticketer_handle_consumers(channel)
