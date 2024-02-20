import json

import sentry_sdk
from nng_sdk.api.api import NngApi
from nng_sdk.api.requests_category import PutRequestResponse, PutRequest
from nng_sdk.pydantic_models.request import RequestType
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import edit_message, send_message_event_answer
from requests import HTTPError
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from actions.profile import inline_handle_profile
from actions.support.input_storage import stages, SupportStages, UnbanPayloads
from actions.support.support import inline_handle_requests
from configuration.complex_phrases import FAILED_TO_OPEN_REQUEST
from configuration.keyboard_phrases import (
    KEYBOARD_UNBLOCK_ATTACH,
    KEYBOARD_SEND,
    KEYBOARD_GO_BACK,
)
from configuration.phrases import (
    SUPPORT_UNBLOCK_NOT_BANNED,
    SUPPORT_UNBLOCK_INITIAL,
    SUPPORT_UNBLOCK_ATTACH_MESSAGE,
    UNEXPECTED_ERROR,
    SUPPORT_UNBLOCK_SUCCESS,
)
from keyboard import back_to_requests_keyboard, Payloads, back_to_violations_keyboard


def inline_handle_unban_send_empty(
    user: User,
    api: NngApi,
    message_id: int,
    event_id: str,
    back_to_profile: bool = False,
):
    inline_handle_unban_send(user, api, message_id, event_id, back_to_profile)


def inline_handle_unban(user: User, message_id: int, back_to_profile: bool = False):
    stages.remove_user(user.user_id)
    if not user.has_active_violation():
        edit_message(
            user.user_id,
            SUPPORT_UNBLOCK_NOT_BANNED,
            message_id,
            back_to_requests_keyboard(),
        )
        return

    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_UNBLOCK_ATTACH,
        VkKeyboardColor.POSITIVE,
        json.dumps(
            Payloads.inline_unban_attach_message_profile
            if back_to_profile
            else Payloads.inline_unban_attach_message
        ),
    )
    keyboard.add_line()

    # отправить запрос на разблокировку без сообщения
    keyboard.add_callback_button(
        KEYBOARD_SEND,
        VkKeyboardColor.SECONDARY,
        json.dumps(
            Payloads.inline_unban_send_empty_profile
            if back_to_profile
            else Payloads.inline_unban_send_empty
        ),
    )

    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(
            Payloads.inline_requests
            if not back_to_profile
            else Payloads.inline_my_violations
        ),
    )

    edit_message(
        user.user_id,
        SUPPORT_UNBLOCK_INITIAL,
        message_id,
        keyboard.get_keyboard(),
    )


def inline_handle_unban_attach_message(
    user: User, message_id: int, back_to_profile: bool = False
):
    keyboard: VkKeyboard = VkKeyboard(inline=True)
    # отмена отправки запроса на разблокировку
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(
            Payloads.inline_unban_profile if back_to_profile else Payloads.inline_unban
        ),
    ),

    attach = (
        Payloads.inline_unban_attach_message
        if back_to_profile
        else Payloads.inline_unban_attach_message_profile
    )

    send = (
        Payloads.inline_unban_send_profile
        if back_to_profile
        else Payloads.inline_unban_send
    )

    stages.add_or_reset_user(
        user.user_id,
        SupportStages.unban_message_input,
        {UnbanPayloads.attach: attach, UnbanPayloads.send: send},
    )

    # ввод сообщения к запросу на разблокировку
    edit_message(
        user.user_id,
        SUPPORT_UNBLOCK_ATTACH_MESSAGE,
        message_id,
        keyboard.get_keyboard(),
    )


def inline_handle_unban_cancel(
    user: User, api: NngApi, message_id: int, back_to_profile: bool = False
):
    stages.remove_user(user.user_id)
    return (
        inline_handle_requests(user, message_id)
        if not back_to_profile
        else inline_handle_profile(user, message_id, api)
    )


def inline_handle_unban_send(
    user: User,
    api: NngApi,
    message_id: int,
    event_id: str,
    back_to_profile: bool = False,
):
    if not user.has_active_violation():
        send_message_event_answer(
            event_id,
            user.user_id,
            user.user_id,
            {"type": "show_snackbar", "text": SUPPORT_UNBLOCK_NOT_BANNED},
        )
        return

    back_keyboard = (
        back_to_violations_keyboard()
        if back_to_profile
        else back_to_requests_keyboard()
    )

    stage = stages.get_user(user.user_id)

    message = (
        stage.get_stage_value(SupportStages.unban_message_input)
        if stage is not None
        else ""
    )

    stages.remove_user(user.user_id)

    response: PutRequestResponse
    try:
        response: PutRequestResponse = api.requests.open_request(
            PutRequest(
                request_type=RequestType.unblock,
                user_id=user.user_id,
                user_message=message,
            )
        )
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        edit_message(
            user.user_id,
            UNEXPECTED_ERROR,
            message_id,
            back_keyboard,
        )
        return

    if not response.success:
        edit_message(
            user.user_id,
            FAILED_TO_OPEN_REQUEST.build(response=response.response),
            message_id,
            back_keyboard,
        )
        return

    edit_message(
        user.user_id,
        SUPPORT_UNBLOCK_SUCCESS,
        message_id,
        back_keyboard,
    )
