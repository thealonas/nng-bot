from typing import Callable

import sentry_sdk
from nng_sdk.api.api import NngApi
from nng_sdk.api.editor_category import GiveEditorResponse, OperationStatus
from nng_sdk.pydantic_models.group import Group
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import send_message, edit_message
from requests import HTTPError
from vk_api.keyboard import VkKeyboard

import keyboard
from actions.utils import get_group_screen_name
from configuration.complex_phrases import EDITOR_SUCCESS, EDITOR_JOIN_GROUP, EDITOR_FAIL
from configuration.phrases import (
    EDITOR_VIOLATION_ACTIVE,
    EDITOR_AGREE_WITH_RULES,
    EDITOR_GIVEN_ERROR,
    EDITOR_COOLDOWN,
)
from configuration.stickers import get_random_editor_sticker


def handle_editor_base(
    user: User,
    api: NngApi,
    send_callback: Callable[[str, str | None], None],
    force: bool = False,
):
    if user.has_active_violation():
        send_callback(EDITOR_VIOLATION_ACTIVE, None)
        return

    if not user.groups and not force:
        send_callback(EDITOR_AGREE_WITH_RULES, keyboard.agree_with_rules_keyboard())
        return

    api_answer: GiveEditorResponse

    try:
        api_answer = api.editor.give_editor(user.user_id)
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        send_callback(EDITOR_GIVEN_ERROR, None)
        return

    groups: list[Group] = api.groups.get_groups()

    match api_answer.status:
        case OperationStatus.success:
            group_id: int = int(api_answer.argument)
            send_callback(
                EDITOR_SUCCESS.build(
                    group_screen_name=get_group_screen_name(group_id, groups)
                ),
                None,
            )
            send_message(user.user_id, sticker_id=get_random_editor_sticker())
        case OperationStatus.join_group:
            group_id: int = int(api_answer.argument)

            join_group_keyboard = VkKeyboard(inline=True)
            join_group_keyboard.add_openlink_button(
                label="↗️ Перейти", link=f"https://vk.com/club{group_id}"
            )

            send_callback(
                EDITOR_JOIN_GROUP.build(
                    group_screen_name=get_group_screen_name(group_id, groups)
                ),
                join_group_keyboard.get_keyboard(),
            )
        case OperationStatus.cooldown:
            send_callback(EDITOR_COOLDOWN, None)
        case OperationStatus.fail:
            if api_answer.argument:
                send_callback(EDITOR_FAIL.build(reason=api_answer.argument), None)
            else:
                send_callback(EDITOR_GIVEN_ERROR, None)


def handle_editor(user: User, api: NngApi, force: bool = False):
    send_callback: Callable[[str, str | None], None] = lambda text, kb: send_message(
        user.user_id, text, kb
    )
    return handle_editor_base(user, api, send_callback, force)


def inline_handle_editor(user: User, api: NngApi, message_id: int):
    send_callback: Callable[[str, str | None], None] = lambda text, kb: edit_message(
        user.user_id, text, message_id, kb
    )
    return handle_editor_base(user, api, send_callback)


def inline_handle_editor_agree_with_rules(user: User, api: NngApi, message_id: int):
    send_callback: Callable[[str, str | None], None] = lambda text, kb: edit_message(
        user.user_id, text, message_id, kb
    )
    return handle_editor_base(user, api, send_callback, force=True)
