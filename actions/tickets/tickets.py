import datetime

import sentry_sdk
from requests import HTTPError

from actions.support.support import inline_handle_requests
from actions.tickets.input_storage import (
    tickets_answer_message_input,
    tickets,
    features,
    reset_user_inputs,
)
from actions.tickets.utils import get_ticket_string, get_ticket_dialog_string
from keyboard import (
    PatternPayloads,
    Payloads,
    pagination_tickets_keyboard,
    tickets_keyboard,
    cancel_feature_answer_input,
    tickets_dialog_keyboard,
    cancel_ticket_answer_input_with_id,
    cancel_ticket_keyboard,
)
from nng_sdk.api.api import NngApi
from nng_sdk.api.tickets_category import TicketShort
from nng_sdk.pydantic_models.ticket import Ticket, TicketStatus
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import send_message_event_answer, edit_message, send_message
from configuration.phrases import (
    INVALID_REQUEST,
    TICKETS_PAGE,
    TICKET_CLOSED_FOR_REPLY,
    TICKET_POST_PROMPT,
    FEATURE_INPUT_PROMPT,
    TICKET_ANSWER_PROMPT,
    TICKET_ALREADY_CLOSED,
    BUTTON_BROKEN,
    TICKET_CLOSED,
)

PAGE_SIZE = 4


def edit_long_message(
    peer_id: int, text: str, first_message_id: int, keyboard: str | None = None
):
    bunch_by_3500: list[str] = [text[i : i + 3500] for i in range(0, len(text), 3500)]
    if not bunch_by_3500:
        raise RuntimeError("Text is empty")

    if len(bunch_by_3500) == 1:
        edit_message(
            peer_id,
            bunch_by_3500[0],
            first_message_id,
            keyboard=keyboard,
        )
        return

    edit_message(
        peer_id,
        bunch_by_3500[0] + "...\n",
        first_message_id,
        keyboard=None,
    )

    for i in range(1, len(bunch_by_3500)):
        is_last_message = i == len(bunch_by_3500) - 1

        if not is_last_message:
            send_message(
                peer_id,
                "..." + bunch_by_3500[i] + "...\n",
                keyboard=None,
            )
        else:
            send_message(peer_id, "..." + bunch_by_3500[i], keyboard=keyboard)


def send_long_message(peer_id: int, text: str, keyboard: str | None = None):
    bunch_by_3500: list[str] = [text[i : i + 3500] for i in range(0, len(text), 3500)]
    if not bunch_by_3500:
        raise RuntimeError("Text is empty")

    if len(bunch_by_3500) == 1:
        send_message(peer_id, bunch_by_3500[0], keyboard=keyboard)
        return

    send_message(
        peer_id,
        bunch_by_3500[0] + "...\n",
        keyboard=None,
    )

    for i in range(1, len(bunch_by_3500)):
        is_last_message = i == len(bunch_by_3500) - 1

        if not is_last_message:
            send_message(
                peer_id,
                "..." + bunch_by_3500[i] + "...\n",
                keyboard=None,
            )
        else:
            send_message(peer_id, "..." + bunch_by_3500[i], keyboard=keyboard)


def _inline_handle_ticket_cancel(
    user: User, api: NngApi, payload: str, message_id: int
):
    reset_user_inputs(user.user_id)
    ticket_id: int = int(PatternPayloads.inline_ticket_cancel.unbox(payload))
    ticket: Ticket
    try:
        ticket = api.tickets.get_ticket(ticket_id)
        ticket.sort_dialogs()
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        send_message_event_answer(
            payload,
            user.user_id,
            user.user_id,
            {
                "type": "show_snackbar",
                "text": INVALID_REQUEST,
            },
        )
        return

    edit_message(
        user.user_id,
        get_ticket_string(ticket),
        message_id,
        tickets_keyboard(ticket_id, ticket.is_closed),
    )


def handle_inline_tickets(
    user: User, api: NngApi, message_id: int, event_id: str, payload: str
):
    if PatternPayloads.inline_ticket_overview.check(payload):
        _inline_handle_ticket_overview(payload, api, user, message_id, event_id)
    elif (
        PatternPayloads.inline_ticket_go_to_page.check(payload)
        or payload == Payloads.inline_tickets
    ):
        _inline_handle_ticket_go_to_page(payload, api, user, message_id)
    elif PatternPayloads.inline_reply_to_ticket.check(payload):
        _inline_handle_reply_to_ticket(payload, api, user, message_id, event_id)
    elif PatternPayloads.inline_ticket_close.check(payload):
        _inline_handle_ticket_close(payload, api, user, message_id, event_id)
    elif payload == Payloads.inline_new_ticket:
        _inline_handle_new_ticket(user, message_id)
    elif PatternPayloads.inline_ticket_dialog.check(payload):
        _inline_handle_ticket_dialog(user, api, payload, message_id, event_id)
    elif PatternPayloads.inline_ticket_cancel.check(payload):
        _inline_handle_ticket_cancel(user, api, payload, message_id)
    elif payload == Payloads.inline_new_feature:
        _inline_handle_new_feature(user, message_id)
    else:
        raise RuntimeError("Invalid payload")


def _inline_handle_ticket_overview(
    payload: str, api: NngApi, user: User, message_id: int, event_id: str
):
    ticket_id = PatternPayloads.inline_ticket_overview.unbox(payload)
    ticket: Ticket

    try:
        ticket = api.tickets.get_ticket(ticket_id)
    except HTTPError:
        send_message_event_answer(
            event_id,
            user.user_id,
            user.user_id,
            {
                "type": "show_snackbar",
                "text": INVALID_REQUEST,
            },
        )
        return

    ticket.sort_dialogs()

    edit_message(
        user.user_id,
        get_ticket_string(ticket),
        message_id,
        tickets_keyboard(ticket_id, ticket.is_closed),
        lambda e: sentry_sdk.capture_exception(e),
    )


def _inline_handle_ticket_go_to_page(
    payload: str, api: NngApi, user: User, message_id: int
):
    if PatternPayloads.inline_ticket_go_to_page.check(payload):
        page_number = int(PatternPayloads.inline_ticket_go_to_page.unbox(payload))
    else:
        page_number = 1

    local_tickets: list[TicketShort] = api.tickets.get_user_tickets(user.user_id)

    local_tickets = sorted(
        local_tickets,
        key=lambda r: (-(datetime.datetime.now() - r.opened).days,),
    )

    max_page = -(-len(local_tickets) // PAGE_SIZE)

    if page_number < 1:
        page_number = 1
    elif page_number > max_page:
        page_number = max_page

    keyboard = pagination_tickets_keyboard(
        local_tickets,
        current_page=page_number,
    )

    edit_message(
        user.user_id,
        TICKETS_PAGE,
        message_id,
        keyboard.get_keyboard(),
    )


def _inline_handle_reply_to_ticket(
    payload: str, api: NngApi, user: User, message_id: int, event_id: str
):
    ticket_id = PatternPayloads.inline_reply_to_ticket.unbox(payload)

    try:
        ticket: Ticket = api.tickets.get_ticket(ticket_id)
    except HTTPError:
        send_message_event_answer(
            event_id,
            user.user_id,
            user.user_id,
            {
                "type": "show_snackbar",
                "text": INVALID_REQUEST,
            },
        )
        return

    if ticket.is_closed:
        send_message_event_answer(
            event_id,
            user.user_id,
            user.user_id,
            {
                "type": "show_snackbar",
                "text": TICKET_CLOSED_FOR_REPLY,
            },
        )
        return

    tickets_answer_message_input.add_user(user.user_id, ticket_id)

    edit_message(
        user.user_id,
        TICKET_ANSWER_PROMPT,
        message_id,
        cancel_ticket_answer_input_with_id(ticket_id),
        lambda e: sentry_sdk.capture_exception(e),
    )


def _inline_handle_ticket_close(
    payload: str, api: NngApi, user: User, message_id: int, event_id: str
):
    def send_snackbar(text: str):
        send_message_event_answer(
            event_id,
            user.user_id,
            user.user_id,
            {
                "type": "show_snackbar",
                "text": text,
            },
        )

    ticket_id = PatternPayloads.inline_ticket_close.unbox(payload)

    if not ticket_id.isdigit():
        sentry_sdk.capture_exception(ValueError(f"Invalid ticket id {ticket_id}"))
        send_snackbar(BUTTON_BROKEN)
        return

    ticket_id = int(ticket_id)

    try:
        ticket: Ticket = api.tickets.get_ticket(ticket_id)
    except HTTPError:
        send_snackbar(INVALID_REQUEST)
        return

    if ticket.closed:
        send_snackbar(TICKET_ALREADY_CLOSED)
        return

    try:
        api.tickets.update_status(ticket_id, TicketStatus.closed, silent=True)
    except HTTPError as e:
        if e.response.status_code in [404, 409]:
            send_snackbar(TICKET_ALREADY_CLOSED)
            return

        sentry_sdk.capture_exception(e)
        send_snackbar(BUTTON_BROKEN)
        return

    ticket.status = TicketStatus.closed

    send_snackbar(TICKET_CLOSED)

    edit_message(
        user.user_id,
        get_ticket_string(ticket),
        message_id,
        tickets_keyboard(ticket.ticket_id, ticket.is_closed),
        lambda ex: sentry_sdk.capture_exception(ex),
    )


def _inline_handle_new_ticket(user: User, message_id: int):
    tickets.add_user(user.user_id)

    edit_message(
        user.user_id,
        TICKET_POST_PROMPT,
        message_id,
        cancel_ticket_keyboard(),
        lambda e: sentry_sdk.capture_exception(e),
    )


def _inline_handle_new_feature(user: User, message_id: int):
    features.add_user(user.user_id)

    edit_message(
        user.user_id,
        FEATURE_INPUT_PROMPT,
        message_id,
        cancel_feature_answer_input(),
    )


def _inline_handle_ticket_dialog(
    user: User, api: NngApi, payload: str, message_id: int, event_id: str
):
    def answer(text: str):
        send_message_event_answer(
            event_id,
            user.user_id,
            user.user_id,
            {
                "type": "show_snackbar",
                "text": text,
            },
        )

    ticket_id: str = PatternPayloads.inline_ticket_dialog.unbox(payload)
    ticket: Ticket
    try:
        ticket = api.tickets.get_ticket(ticket_id)
        ticket.sort_dialogs()
    except HTTPError:
        answer(INVALID_REQUEST)
        return

    edit_long_message(
        user.user_id,
        get_ticket_dialog_string(ticket),
        message_id,
        tickets_dialog_keyboard(ticket_id, ticket.is_closed),
    )
    return


def inline_handle_ticket_cancel_answer(
    user: User, api: NngApi, message_id: int, event_id: str
):
    reset_user_inputs(user.user_id)
    ticket_id: str = tickets_answer_message_input.get_user(user.user_id).ticket_id
    return _inline_handle_ticket_overview(
        PatternPayloads.inline_ticket_overview.box(ticket_id),
        api,
        user,
        message_id,
        event_id,
    )


def inline_handle_ticket_cancel(user: User, api: NngApi, message_id: int):
    reset_user_inputs(user.user_id)
    return _inline_handle_ticket_go_to_page("", api, user, message_id)


def inline_handle_feature_cancel(user: User, message_id: int):
    reset_user_inputs(user.user_id)
    return inline_handle_requests(user, message_id)
