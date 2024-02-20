import json

import sentry_sdk
from nng_sdk.api.api import NngApi
from nng_sdk.api.invites_category import UseInviteResponseType, UseInviteResponse
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import send_message, edit_message
from requests import HTTPError
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from keyboard import Payloads, PatternPayloads
from configuration.complex_phrases import (
    USER_SCREEN_NAME_ALREADY_INVITED,
    USER_ID_ALREADY_INVITED,
    INVITE_CONFIRM,
    INVITE_SUCCESS,
)
from configuration.keyboard_phrases import (
    KEYBOARD_INVITE_CONFIRM,
    KEYBOARD_INVITE_REFUSE,
)
from configuration.phrases import (
    INVITES_INVALID_COMMAND,
    INVITES_VIOLATION_ACTIVE,
    CANT_INVITE_MYSELF,
    INVITED_USER_INVALID,
    INVITES_INVALID_PROFILE,
    ALREADY_INVITED_BY_SOMEONE,
    CANT_BE_INVITED_BY_REFERRAL,
    UNEXPECTED_ERROR,
    INVITE_REFUSE_PAGE,
    TOO_LOW_TRUST,
    TOO_LOW_REFERRAL_TRUST,
)


def handle_invite_command(user: User, api: NngApi, referral_command: str):
    def answer_invalid():
        send_message(
            user.user_id,
            INVITES_INVALID_COMMAND,
        )

    referral_split = referral_command.split(":")

    if len(referral_split) != 2:
        answer_invalid()
        return

    referral_value = referral_split[0]
    if not referral_value.isdigit():
        answer_invalid()
        return

    referral: int = int(referral_value)

    if user.has_active_violation():
        send_message(
            user.user_id,
            INVITES_VIOLATION_ACTIVE,
        )
        return

    if user.invited_by is not None:
        invited_by: User | None = try_get_user(user.invited_by, api)
        if invited_by is not None:
            send_message(
                user.user_id,
                USER_SCREEN_NAME_ALREADY_INVITED.build(
                    user_id=invited_by.user_id, user_name=invited_by.name
                ),
            )
        else:
            USER_ID_ALREADY_INVITED.build(user_id=user.invited_by)
        return

    if user.user_id == referral:
        send_message(user.user_id, CANT_INVITE_MYSELF)
        return

    try:
        referral_profile = api.users.get_user(referral)
    except HTTPError:
        send_message(
            user.user_id,
            INVITED_USER_INVALID,
        )
        return

    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_INVITE_CONFIRM,
        VkKeyboardColor.POSITIVE,
        json.dumps(PatternPayloads.inline_invite_confirm.box(referral_command)),
    )
    keyboard.add_callback_button(
        KEYBOARD_INVITE_REFUSE,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_invite_refuse),
    )

    send_message(
        user.user_id,
        INVITE_CONFIRM.build(user_id=referral, user_name=referral_profile.name),
        keyboard.get_keyboard(),
    )
    return


def try_get_user(user_id: int, api: NngApi) -> User | None:
    try:
        return api.users.get_user(user_id)
    except HTTPError:
        return None


def handle_invite_command_confirm(
    user: User, api: NngApi, message_id: int, referral_command: str
):
    def answer_invalid():
        edit_message(
            user.user_id,
            INVITES_INVALID_COMMAND,
            message_id,
        )

    referral_split = referral_command.split(":")

    if len(referral_split) != 2:
        answer_invalid()
        return

    referral_id = referral_split[0]
    if not referral_id.isdigit():
        answer_invalid()
        return

    referral: int = int(referral_id)

    if user.has_active_violation():
        edit_message(
            user.user_id,
            INVITES_VIOLATION_ACTIVE,
            message_id,
        )
        return

    if user.invited_by is not None:
        invited_by: User | None = try_get_user(user.invited_by, api)
        if invited_by is not None:
            edit_message(
                user.user_id,
                USER_SCREEN_NAME_ALREADY_INVITED.build(
                    user_id=referral, user_name=invited_by.name
                ),
                message_id,
            )
        else:
            edit_message(
                user.user_id,
                USER_ID_ALREADY_INVITED.build(user_id=user.invited_by),
                message_id,
            )
        return

    if user.user_id == referral:
        edit_message(user.user_id, CANT_INVITE_MYSELF, message_id)
        return

    response: UseInviteResponse

    try:
        response = api.invites.use_invite(referral_command, user.user_id)
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        response = UseInviteResponse.model_validate(e.response.json())

    referral_profile = api.users.get_user(referral)

    match response.response_type:
        case UseInviteResponseType.invalid_or_banned_referral:
            edit_message(
                user.user_id,
                INVITED_USER_INVALID,
                message_id,
            )
        case UseInviteResponseType.invalid_user:
            sentry_sdk.capture_exception(RuntimeError(response))
            edit_message(user.user_id, INVITES_INVALID_PROFILE, message_id)
        case UseInviteResponseType.cannot_invite_yourself:
            edit_message(user.user_id, CANT_INVITE_MYSELF, message_id)
        case UseInviteResponseType.banned_user:
            edit_message(
                user.user_id,
                INVITES_VIOLATION_ACTIVE,
                message_id,
            )
        case UseInviteResponseType.user_already_invited:
            edit_message(
                user.user_id,
                ALREADY_INVITED_BY_SOMEONE,
                message_id,
            )
        case UseInviteResponseType.user_is_invited_by_you:
            edit_message(
                user.user_id,
                CANT_BE_INVITED_BY_REFERRAL,
                message_id,
            )
        case UseInviteResponseType.too_low_trust:
            edit_message(
                user.user_id,
                TOO_LOW_TRUST,
                message_id,
            )
        case UseInviteResponseType.too_low_trust_referral:
            edit_message(
                user.user_id,
                TOO_LOW_REFERRAL_TRUST,
                message_id,
            )
        case UseInviteResponseType.success:
            edit_message(
                user.user_id,
                INVITE_SUCCESS.build(user_id=referral, user_name=referral_profile.name),
                message_id,
            )
        case _:
            sentry_sdk.capture_exception(RuntimeError(response))
            edit_message(user.user_id, UNEXPECTED_ERROR, message_id)


def handle_invite_cancel(user_id: int, message_id: int):
    edit_message(user_id, INVITE_REFUSE_PAGE, message_id)
