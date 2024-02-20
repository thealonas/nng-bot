import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from typing import Optional

import sentry_sdk
from fastapi import FastAPI
from nng_sdk.api.api import NngApi
from nng_sdk.api.models import VkEvent
from nng_sdk.api.tickets_category import AlgoliaOutput
from nng_sdk.one_password.op_callback_group import OpCallbackGroup
from nng_sdk.one_password.op_connect import OpConnect
from nng_sdk.pydantic_models.ticket import TicketStatus
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import (
    send_message,
    send_message_event_answer,
)
from nng_sdk.vk.vk_manager import VkManager
from onepasswordconnectsdk.client import FailedToRetrieveItemException
from requests import HTTPError
from starlette.background import BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

import actions.support
import actions.support.inputs
import actions.tickets.input_storage
import actions.tickets.inputs
import log_sockets
from actions.editor import (
    handle_editor,
    inline_handle_editor_agree_with_rules,
    inline_handle_editor,
)
from actions.invite import (
    handle_invite_cancel,
    handle_invite_command_confirm,
    handle_invite_command,
)
from actions.profile import (
    handle_profile,
    inline_handle_invites,
    inline_handle_profile,
    inline_handle_my_violations,
)
from actions.request_history import handle_inline_requests
from actions.support.support import (
    handle_support,
    inline_handle_support,
    inline_handle_requests,
)
from actions.support.unban import (
    inline_handle_unban_send_empty,
    inline_handle_unban,
    inline_handle_unban_attach_message,
    inline_handle_unban_cancel,
    inline_handle_unban_send,
)
from actions.support.complaint import (
    inline_handle_complaint_confirm,
    inline_handle_complaint_go_to_first_phase,
    inline_handle_complaint_go_to_second_phase,
    inline_handle_complaint_cancel,
    inline_handle_complaint,
)
from actions.tickets.tickets import (
    handle_inline_tickets,
    inline_handle_ticket_cancel_answer,
    inline_handle_feature_cancel,
    inline_handle_ticket_cancel,
)
from configuration.phrases import (
    MAIN_MENU,
    BUTTON_BROKEN,
    TICKET_STATUS_UNREVIEWED,
    TICKET_STATUS_IN_REVIEW,
    TICKET_STATUS_CLOSED,
)
from configuration.stickers import get_random_greeting_sticker, get_random_fun_sticker
from keyboard import (
    main_menu_keyboard,
    Payloads,
    PatternPayloads,
)
from logger import get_logger

sentry_sdk.init(
    dsn="https://60f3622aa1cfbe5dd3d10e4c483e84b1@o555933.ingest.sentry.io/4505970495193088",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)


def ticket_to_string(status: TicketStatus) -> str:
    match status:
        case TicketStatus.unreviewed:
            return TICKET_STATUS_UNREVIEWED
        case TicketStatus.in_review:
            return TICKET_STATUS_IN_REVIEW
        case TicketStatus.closed:
            return TICKET_STATUS_CLOSED


TicketStatus.__str__ = ticket_to_string


# noinspection PyAsyncCall
@asynccontextmanager
async def app_lifespan(_: FastAPI):
    asyncio.create_task(log_sockets.receive_editor_logs(api))
    asyncio.create_task(log_sockets.receive_requests_logs(api))
    asyncio.create_task(log_sockets.receive_tickets_logs(api))
    asyncio.create_task(log_sockets.receive_watchdog_logs(api))
    asyncio.create_task(log_sockets.online_ticker(op))
    yield


app = FastAPI(docs_url=None, redoc_url=None, lifespan=app_lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = NngApi("bot", os.environ.get("NNG_API_AK"))
op = OpConnect()
vk = VkManager()

vk.auth_in_vk()
vk.auth_in_bot()

logger = get_logger()

api_url = str(os.environ.get("NNG_API_URL"))


def ensure_user_has_profile(user_id: int) -> User:
    try:
        return api.users.get_user(user_id)
    except HTTPError:
        api.users.add_user(user_id)
        return api.users.get_user(user_id)


def check_pattern(string: str, pattern: str) -> (bool, str):
    match = re.match(pattern, string)
    if match:
        return True, match.group(1)
    return False, None


def reset_all_inputs(user: User):
    actions.tickets.inputs.reset_user_inputs(user.user_id)
    actions.tickets.inputs.reset_user_texts(user.user_id)
    actions.support.inputs.reset_user_inputs(user.user_id)


def handle_input(
    user: User,
    api_component: NngApi,
    message_text: str,
    attachments: list[dict] | None = None,
):
    if actions.support.inputs.awaiting_input(user):
        return actions.support.inputs.handle_inputs(user, api_component, message_text)
    if actions.tickets.input_storage.is_in_input_lists(user):
        return actions.tickets.inputs.handle_inputs(
            user, api_component, message_text, attachments
        )
    raise RuntimeError("User is not in input lists")


def has_stickers(attachments: list[dict] | None) -> bool:
    if not attachments:
        return False

    for element in attachments:
        if element.get("type") == "sticker":
            return True


# https://dev.vk.com/ru/api/community-events/json-schema#%D0%A1%D0%BE%D0%BE%D0%B1%D1%89%D0%B5%D0%BD%D0%B8%D1%8F
def handle_message_new(message_new: dict):
    invite_command_pattern: str = r"/hi (.*)"

    message: dict = message_new["message"]
    user_id: int = message["from_id"]
    profile: User = ensure_user_has_profile(user_id)
    payload: Optional[str] = message.get("payload")
    text: str = message.get("text")
    attachments: list[dict] | None = message.get("attachments")

    is_match, referral_string = check_pattern(text, invite_command_pattern)

    if is_match:
        handle_invite_command(profile, api, referral_string)
        return

    awaiting_input = actions.support.inputs.awaiting_input(
        profile
    ) or actions.tickets.input_storage.awaiting_input(profile)

    if payload and awaiting_input:
        reset_all_inputs(profile)
        awaiting_input = False

    if has_stickers(attachments):
        send_message(user_id, sticker_id=get_random_fun_sticker())
        reset_all_inputs(profile)
        return

    if not payload and not awaiting_input:
        query = api.tickets.algolia_search(text)
        if query:
            target_query: AlgoliaOutput = query[0]
            keyboard = (
                Payloads.from_algolia(target_query.action)
                if target_query.action
                else main_menu_keyboard()
            )

            send_message(
                user_id,
                query[0].answer,
                keyboard,
                attachment=target_query.attachment or None,
                dont_parse_links=True,
            )
            return

        send_message(user_id, MAIN_MENU, main_menu_keyboard())
        return

    if payload == '{"command":"start"}':
        send_message(user_id, MAIN_MENU, main_menu_keyboard())
        send_message(user_id, sticker_id=get_random_greeting_sticker())
        return

    if awaiting_input and len(text) < 1:
        reset_all_inputs(profile)
    elif awaiting_input:
        handle_input(profile, api, text, attachments)
        return

    try:
        payload = json.loads(payload)
    except TypeError:
        reset_all_inputs(profile)
        send_message(user_id, MAIN_MENU, main_menu_keyboard())

    match payload:
        case Payloads.main_menu_profile:
            handle_profile(profile, api)
            return
        case Payloads.main_menu_editor:
            handle_editor(profile, api)
            return
        case Payloads.main_menu_support:
            handle_support(profile)
            return

    if len(text) < 1:
        send_message(user_id, MAIN_MENU, main_menu_keyboard())
        return


def handle_message_event(message_event: dict):
    user_id: int = message_event["user_id"]
    peer_id: int = message_event["peer_id"]
    event_id: str = message_event["event_id"]
    profile: User = ensure_user_has_profile(user_id)
    message_id: int = message_event["conversation_message_id"]
    payload: str = message_event.get("payload")

    if not payload:
        send_message_event_answer(
            event_id,
            user_id,
            peer_id,
            {"type": "show_snackbar", "text": BUTTON_BROKEN},
        )
        return

    if PatternPayloads.inline_invite_confirm.check(payload):
        handle_invite_command_confirm(
            profile,
            api,
            message_id,
            PatternPayloads.inline_invite_confirm.unbox(payload),
        )
        return

    try:
        handle_inline_requests(profile, api, message_id, event_id, payload)
        return
    except RuntimeError:
        pass

    try:
        handle_inline_tickets(profile, api, message_id, event_id, payload)
        return
    except RuntimeError:
        pass

    match payload:
        case Payloads.inline_editor:
            inline_handle_editor(profile, api, message_id)
        case Payloads.inline_editor_agree_with_rules:
            inline_handle_editor_agree_with_rules(profile, api, message_id)

        case Payloads.inline_invite_refuse:
            handle_invite_cancel(profile.user_id, message_id)
        case Payloads.inline_invite:
            inline_handle_invites(profile, api, message_id)

        case Payloads.inline_my_violations:
            inline_handle_my_violations(profile, api, message_id, event_id)

        case Payloads.inline_go_to_profile:
            inline_handle_profile(profile, message_id, api)

        case Payloads.inline_support:
            inline_handle_support(profile, message_id)

        case Payloads.inline_requests:
            inline_handle_requests(profile, message_id)

        case Payloads.inline_unban:
            inline_handle_unban(profile, message_id)
        case Payloads.inline_unban_profile:
            inline_handle_unban(profile, message_id, True)
        case Payloads.inline_unban_attach_message:
            inline_handle_unban_attach_message(profile, message_id)
        case Payloads.inline_unban_attach_message_profile:
            inline_handle_unban_attach_message(profile, message_id, True)
        case Payloads.inline_unban_send:
            inline_handle_unban_send(profile, api, message_id, event_id)
        case Payloads.inline_unban_send_profile:
            inline_handle_unban_send(profile, api, message_id, event_id, True)
        case Payloads.inline_unban_cancel:
            inline_handle_unban_cancel(profile, api, message_id)
        case Payloads.inline_unban_cancel_profile:
            inline_handle_unban_cancel(profile, api, message_id, True)
        case Payloads.inline_unban_send_empty:
            inline_handle_unban_send_empty(profile, api, message_id, event_id)
        case Payloads.inline_unban_send_empty_profile:
            inline_handle_unban_send_empty(profile, api, message_id, event_id, True)

        case Payloads.inline_complaint:
            inline_handle_complaint(profile, message_id)
        case Payloads.inline_complaint_confirm:
            inline_handle_complaint_confirm(profile, api, message_id, event_id)
        case Payloads.inline_complaint_go_to_first_phase:
            inline_handle_complaint_go_to_first_phase(profile, message_id)
        case Payloads.inline_complaint_go_to_second_phase:
            inline_handle_complaint_go_to_second_phase(profile, message_id)

        case Payloads.inline_complaint_cancel:
            inline_handle_complaint_cancel(profile, message_id)

        case Payloads.inline_algolia_success:
            actions.tickets.inputs.inline_handle_algolia_success(
                profile, event_id, message_id
            )
        case Payloads.inline_algolia_fail:
            actions.tickets.inputs.inline_handle_algolia_fail(profile, api, message_id)

        case Payloads.inline_cancel_ticket_answer_input:
            inline_handle_ticket_cancel_answer(profile, api, message_id, event_id)

        case Payloads.inline_ticket_cancel:
            inline_handle_ticket_cancel(profile, api, message_id)

        case Payloads.inline_cancel_feature_answer_input:
            inline_handle_feature_cancel(profile, message_id)

        case _:
            send_message_event_answer(
                event_id,
                user_id,
                peer_id,
                {"type": "show_snackbar", "text": BUTTON_BROKEN},
            )


@app.post("/", response_class=PlainTextResponse)
def post(event: VkEvent, background_tasks: BackgroundTasks):
    if not event.secret:
        return "ok"

    op_group: OpCallbackGroup

    try:
        op_group = op.get_bot_group()
        if not op_group:
            raise FailedToRetrieveItemException()
    except FailedToRetrieveItemException:
        sentry_sdk.capture_message(
            f"failed to retrieve group {event.group_id} from 1pass"
        )
        return "ok"

    if op_group.group_id != event.group_id:
        return "ok"

    if event.secret != op_group.secret:
        return "ok"

    if event.type == "confirmation":
        return op_group.confirm

    if op_group.secret != event.secret or not event.object:
        return "ok"

    match event.type:
        case "message_event":
            background_tasks.add_task(handle_message_event, event.object)
        case "message_new":
            background_tasks.add_task(handle_message_new, event.object)

    return "ok"
