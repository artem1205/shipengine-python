"""
ShipEngine event emission via Observer Pattern. The ShipEngine SDK emits when an
HTTP request is sent and when an HTTP response is received for said request.
"""
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from ..errors import ShipEngineError
from ..models.enums import Events


class ShipEngineEvent:
    timestamp: str

    def __init__(self, event_type: str, message: str) -> None:
        self.timestamp = datetime.now().isoformat()
        self.type = event_type
        self.message = message

    def to_dict(self):
        return (lambda o: o.__dict__)(self)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)

    @staticmethod
    def new_event_message(method: str, base_uri: str, message_type: str) -> str:
        """A method to dynamically create an event message based on the $messageType being passed in."""
        if message_type == "base_message":
            return f"Calling the ShipEngine {method} API at {base_uri}"
        elif message_type == "retry_message":
            return f"Retrying the ShipEngine {method} API at {base_uri}"
        else:
            raise ShipEngineError(f"Message type [{message_type}] is not a valid type of message.")


class RequestSentEvent(ShipEngineEvent):
    REQUEST_SENT = "request_sent"

    def __init__(
        self,
        request_id: str,
        message: str,
        url: str,
        headers: List[str],
        body: Dict[str, Any],
        retry: int,
        timeout: int,
    ) -> None:
        super().__init__(event_type=self.REQUEST_SENT, message=message)
        self.request_id = request_id
        self.url = url
        self.headers = headers
        self.body = body
        self.retry = retry
        self.timeout = timeout


class ResponseReceivedEvent(ShipEngineEvent):
    RESPONSE_RECEIVED = "response_received"

    def __init__(
        self,
        message: str,
        request_id: str,
        url: str,
        status_code: int,
        headers: List[str],
        body: Dict[str, Any],
        retry: int,
        elapsed: str,
    ) -> None:
        super().__init__(event_type=self.RESPONSE_RECEIVED, message=message)
        self.request_id = request_id
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.retry = retry
        self.elapsed = elapsed


class Dispatcher:
    def __init__(self, events: List[str]) -> None:
        self.events = {event: dict() for event in events}

    def get_subscribers(self, event: Optional[str] = None):
        return self.events[event]

    def register(self, event, subscriber, callback: Optional[Callable] = None):
        if callback is None:
            callback = getattr(subscriber, "update")
        self.get_subscribers(event)[subscriber] = callback

    def unregister(self, event, subscriber):
        del self.get_subscribers(event)[subscriber]

    def dispatch(self, event, event_name: str = None):
        for subscriber, callback in self.get_subscribers(event_name).items():
            callback(event)


class Subscriber:
    def __init__(self, name=None) -> None:
        if name is not None:
            self.name = name
        else:
            self.name = "Event Subscriber"

    @staticmethod
    def update(event: Union[RequestSentEvent, ResponseReceivedEvent]):
        return event

    def to_dict(self):
        return (lambda o: o.__dict__)(self)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)


class ShipEngineEventListener(Subscriber):
    def __init__(self, name=None) -> None:
        super().__init__(name=name)

    # You can add your own event consumption logic by adding/overriding the parent `update()` method below.
    @staticmethod
    def update(event: Union[RequestSentEvent, ResponseReceivedEvent]):
        print(event.to_dict())


def emit_event(emitted_event_type: str, event_data, config):
    dispatcher = Dispatcher([Events.ON_REQUEST_SENT.value, Events.ON_RESPONSE_RECEIVED.value])
    dispatcher.register(event=Events.ON_REQUEST_SENT.value, subscriber=config.event_listener)
    dispatcher.register(event=Events.ON_RESPONSE_RECEIVED.value, subscriber=config.event_listener)
    if emitted_event_type == RequestSentEvent.REQUEST_SENT:
        request_sent_event = RequestSentEvent(
            message=event_data.message,
            request_id=event_data.request_id,
            url=event_data.base_uri,
            headers=event_data.request_headers,
            body=event_data.body,
            retry=event_data.retry,
            timeout=event_data.timeout,
        )
        dispatcher.dispatch(event=request_sent_event, event_name=Events.ON_REQUEST_SENT.value)
        return request_sent_event
    elif emitted_event_type == ResponseReceivedEvent.RESPONSE_RECEIVED:
        response_received_event = ResponseReceivedEvent(
            message=event_data.message,
            request_id=event_data.request_id,
            url=event_data.base_uri,
            status_code=event_data.status_code,
            headers=event_data.request_headers,
            body=event_data.body,
            retry=event_data.retry,
            elapsed=event_data.elapsed,
        )
        dispatcher.dispatch(
            event=response_received_event, event_name=Events.ON_RESPONSE_RECEIVED.value
        )
        return response_received_event
    else:
        raise ShipEngineError(f"Event type [{emitted_event_type}] is not a valid type of event.")
