import datetime

from nng_sdk.api.api import NngApi
from nng_sdk.pydantic_models.request import RequestType, Request
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import send_message_event_answer, edit_message
from requests import HTTPError

from actions.utils import request_status_phrase
from configuration.complex_templates import (
    build_complaint_request,
    build_unblock_request,
)
from configuration.phrases import INVALID_REQUEST, REQUESTS_HISTORY_PAGE
from keyboard import (
    PatternPayloads,
    Payloads,
    pagination_requests_keyboard,
    back_to_requests_history_keyboard,
)

PAGE_SIZE = 4


def handle_inline_requests(
    user: User, api: NngApi, message_id: int, event_id: str, payload: str
):
    def answer(text: str | None):
        if not text:
            send_message_event_answer(
                event_id,
                user.user_id,
                user.user_id,
            )
        else:
            send_message_event_answer(
                event_id,
                user.user_id,
                user.user_id,
                {
                    "type": "show_snackbar",
                    "text": text,
                },
            )

    def edit(text: str, new_keyboard: str | None = None):
        edit_message(user.user_id, text, message_id, new_keyboard)

    if PatternPayloads.inline_request_overview.check(payload):
        request_id = PatternPayloads.inline_request_overview.unbox(payload)
        request: Request

        try:
            request = api.requests.get_request(request_id)
        except HTTPError:
            answer(INVALID_REQUEST)
            return

        edit(get_request_string(request), back_to_requests_history_keyboard())
        return

    if (
        PatternPayloads.inline_request_go_to_page.check(payload)
        or payload == Payloads.inline_requests_history
    ):
        if payload == Payloads.inline_requests_history:
            page_number = 1
        else:
            page_number = int(PatternPayloads.inline_request_go_to_page.unbox(payload))
        requests = api.requests.get_user_requests(user.user_id)
        requests = sorted(
            requests,
            key=lambda r: (
                not r.answered,
                -(datetime.date.today() - r.created_on).days,
            ),
        )

        max_page = -(-len(requests) // PAGE_SIZE)

        if page_number < 1:
            page_number = 1
        elif page_number > max_page:
            page_number = max_page

        keyboard = pagination_requests_keyboard(requests, current_page=page_number)

        edit(REQUESTS_HISTORY_PAGE, keyboard.get_keyboard())
        return

    raise RuntimeError("Invalid payload")


def get_request_string(request: Request) -> str:
    if request.request_type == RequestType.complaint:
        return build_complaint_request(
            request_id=request.request_id,
            request_status=request_status_phrase(request),
            created_on=request.created_on.strftime("%d.%m.%Y"),
            admin_response=request.answer,
        )

    if request.request_type == RequestType.unblock:
        return build_unblock_request(
            request_id=request.request_id,
            request_status=request_status_phrase(request),
            created_on=request.created_on.strftime("%d.%m.%Y"),
            admin_response=request.answer,
        )

    raise RuntimeError("Invalid request type")
