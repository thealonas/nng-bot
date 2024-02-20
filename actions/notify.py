from nng_sdk.api.api import NngApi
from nng_sdk.api.models import EditorLog, EditorLogType
from nng_sdk.api.requests_category import RequestWebsocketLog
from nng_sdk.api.tickets_category import TicketWebsocketLog, TicketLogType
from nng_sdk.api.watchdog_category import WatchdogWebsocketLog, WatchdogWebsocketLogType
from nng_sdk.pydantic_models.group import Group
from nng_sdk.pydantic_models.request import Request, RequestType
from nng_sdk.pydantic_models.ticket import Ticket, TicketType, TicketMessage
from nng_sdk.vk.actions import send_message

from actions.tickets.utils import get_attachment_string
from actions.utils import request_status_phrase, priority_to_string
from configuration.complex_phrases import (
    EDITOR_SUCCESS,
    EDITOR_FAIL_LEFT_GROUP,
    TICKET_LOG_STATUS_UPDATE,
    TICKET_LOG_MESSAGE_NEW,
    WATCHDOG_NEW_WARNING,
    WATCHDOG_NEW_BAN,
)
from configuration.complex_templates import (
    build_complaint_notify_log,
    build_unblock_notify_log,
)
from configuration.phrases import EDITOR_LOG_FAIL
from configuration.stickers import get_random_editor_sticker
from keyboard import tickets_logs_keyboard


def notify_editor(log: EditorLog, api: NngApi):
    user = log.user_id

    group: Group | None = None

    if log.group_id:
        groups: list[Group] = api.groups.get_groups()
        group = next(g for g in groups if g.group_id == log.group_id)

    match log.log_type:
        case EditorLogType.editor_fail:
            send_message(user, EDITOR_LOG_FAIL)
        case EditorLogType.editor_fail_left_group:
            send_message(user, EDITOR_FAIL_LEFT_GROUP.build(group_id=group.screen_name))
        case EditorLogType.editor_success:
            send_message(
                user, EDITOR_SUCCESS.build(group_screen_name=group.screen_name)
            )

            send_message(user, sticker_id=get_random_editor_sticker())


def notify_request(log: RequestWebsocketLog, api: NngApi):
    user_id: int = log.send_to_user
    request: Request = api.requests.get_request(log.request_id)

    if request.request_type == RequestType.complaint:
        phrase = build_complaint_notify_log(
            request.request_id,
            request_status_phrase(request),
            user_message=request.user_message,
            admin_response=request.answer,
        )
    elif request.request_type == RequestType.unblock:
        admin_response = request.answer or (
            request.answer
            if len(request.answer) < 3500
            else request.answer[:3500] + "..."
        )

        phrase = build_unblock_notify_log(
            request_id=request.request_id,
            request_status=request_status_phrase(request),
            user_message=request.user_message,
            admin_response=admin_response,
        )
    else:
        raise RuntimeError("Invalid type")

    send_message(user_id, phrase)


def notify_ticket(log: TicketWebsocketLog, api: NngApi):
    if log.log_type == TicketLogType.user_added_message:
        return

    ticket: Ticket = api.tickets.get_ticket(log.ticket_id)
    if ticket.type != TicketType.question:
        return

    send_to: int = ticket.issuer

    ticket.sort_dialogs()

    match log.log_type:
        case TicketLogType.updated_status:
            text = TICKET_LOG_STATUS_UPDATE.build(
                id=ticket.ticket_id, status=ticket.status
            )
        case TicketLogType.admin_added_message:
            message: TicketMessage = ticket.dialog[-1]
            message_text = (
                message.message_text
                if len(message.message_text) < 3500
                else message.message_text[:3500] + "..."
            )
            text = TICKET_LOG_MESSAGE_NEW.build(
                id=ticket.ticket_id, message=message_text
            )
            if message.attachments:
                text += "\n" + get_attachment_string(len(message.attachments))
        case _:
            raise RuntimeError(f"Invalid log type {log.log_type}")

    keyboard: str = tickets_logs_keyboard(ticket)
    send_message(send_to, text, keyboard)


def notify_watchdog(log: WatchdogWebsocketLog, api: NngApi):
    match log.type:
        case WatchdogWebsocketLogType.new_warning:
            text = WATCHDOG_NEW_WARNING
        case WatchdogWebsocketLogType.new_ban:
            text = WATCHDOG_NEW_BAN
        case _:
            raise RuntimeError(f"Invalid log type {log.type}")

    group_screen_name = api.groups.get_group(log.group).screen_name

    text = text.build(
        priority=priority_to_string(log.priority), group_screen_name=group_screen_name
    )
    send_message(log.send_to_user, text)
