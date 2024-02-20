import json

import sentry_sdk
from nng_sdk.pydantic_models.group import Group
from requests import HTTPError
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from actions.utils import priority_to_string, trust_to_string, get_group_screen_name
from configuration.phrases import (
    INVALID_REQUEST,
    VIOLATION_TYPE_BANNED,
    VIOLATION_TYPE_WARNED,
    PROFILE_VIOLATION_HEADING,
)
from keyboard import profile_keyboard, Payloads
from nng_sdk.api.api import NngApi
from nng_sdk.pydantic_models.user import User, Violation, ViolationType
from nng_sdk.vk.actions import edit_message, send_message, send_message_event_answer
from configuration.complex_phrases import (
    PROFILE_STRING,
    PROFILE_GROUPS,
    PROFILE_INVITE_HEADING,
    PROFILE_INVITED_BY,
    PROFILE_USER_INVITED,
    PROFILE_VIOLATION_GROUP,
    PROFILE_VIOLATION_DATE,
    PROFILE_VIOLATION_COMPLAINT,
    PROFILE_VIOLATION_PRIORITY,
)
from configuration.keyboard_phrases import KEYBOARD_GO_BACK, KEYBOARD_REQUEST_UNBLOCK


def handle_profile(user: User, api: NngApi):
    profile_string: str = get_profile_string(user, api)

    send_message(
        user.user_id,
        profile_string,
        profile_keyboard(user.has_warning(), user.has_active_violation()),
    )


def inline_handle_profile(user: User, message_id: int, api: NngApi):
    profile_string: str = get_profile_string(user, api)
    edit_message(
        user.user_id,
        profile_string,
        message_id,
        profile_keyboard(user.has_warning(), user.has_active_violation()),
    )


def inline_handle_invites(user: User, api: NngApi, message_id: int):
    try:
        invite_string: str = get_invite_string(user, api)
    except HTTPError:
        edit_message(user.user_id, get_profile_string(user, api), message_id)
        return

    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.inline_go_to_profile),
    )

    edit_message(user.user_id, invite_string, message_id, keyboard.get_keyboard())


def inline_handle_my_violations(
    user: User, api: NngApi, message_id: int, event_id: str
):
    try:
        violation_string: str = get_violations_string(user, api)
    except RuntimeError:
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
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        edit_message(user.user_id, get_profile_string(user, api), message_id)
        return

    keyboard = VkKeyboard(inline=True)

    if user.has_active_violation():
        keyboard.add_callback_button(
            KEYBOARD_REQUEST_UNBLOCK,
            VkKeyboardColor.NEGATIVE,
            json.dumps(Payloads.inline_unban_profile),
        )

        keyboard.add_line()

    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_go_to_profile),
    )

    edit_message(user.user_id, violation_string, message_id, keyboard.get_keyboard())


def try_get_user(user_id: int, api: NngApi) -> User | None:
    try:
        return api.users.get_user(user_id)
    except HTTPError:
        return None


def get_profile_string(user: User, api: NngApi) -> str:
    profile_string = PROFILE_STRING.build(
        user_id=user.user_id,
        user_name=user.name,
        trust=trust_to_string(user.trust_info.trust),
        telegram="❌",
    )

    groups = api.groups.get_groups()

    if user.groups:
        limit: int = api.users.get_groups_limit(user.user_id)
        all_user_groups = [f"@{get_group_screen_name(i, groups)}" for i in user.groups]
        all_user_groups_phrase = (", ".join(all_user_groups)).strip()

        profile_string += PROFILE_GROUPS.build(
            group_list=all_user_groups_phrase, limit=f"{len(all_user_groups)}/{limit}"
        )

    return profile_string


def get_invite_string(user: User, api: NngApi) -> str:
    invite_string = ""

    try:
        invite_code = api.invites.get_my_code(user.user_id)
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
    else:
        invite_string = PROFILE_INVITE_HEADING.build(invite=invite_code)

    if user.invited_by:
        referral_profile = try_get_user(user.invited_by, api)
        if referral_profile:
            invite_string += PROFILE_INVITED_BY.build(
                user_id=referral_profile.user_id, user_name=referral_profile.name
            )
        else:
            invite_string += PROFILE_INVITED_BY.build(user_id=user.invited_by)

    invited_users: list[User] = api.invites.get_users_invited_by_referral(user.user_id)
    if invited_users:
        invited_users_phrase = ", ".join(
            [f"[id{i.user_id}|{i.name}]" for i in invited_users]
        )

        invite_string += PROFILE_USER_INVITED.build(user_list=invited_users_phrase)

    return invite_string


def get_violation_string(violation: Violation, groups: list[Group]) -> str:
    phrase = (
        VIOLATION_TYPE_BANNED
        if violation.type == ViolationType.banned
        else VIOLATION_TYPE_WARNED
    )

    phrase += PROFILE_VIOLATION_PRIORITY.build(
        priority=priority_to_string(violation.priority)
    )

    if violation.group_id:
        phrase += PROFILE_VIOLATION_GROUP.build(
            group_screen_name=get_group_screen_name(violation.group_id, groups)
        )

    if violation.date:
        phrase += PROFILE_VIOLATION_DATE.build(date=violation.date.strftime("%d.%m.%Y"))

    if violation.complaint:
        phrase += PROFILE_VIOLATION_COMPLAINT.build(user_id=violation.complaint)

    return phrase


def get_violations_string(user: User, api: NngApi) -> str:
    active_bans = [
        ban
        for ban in user.violations
        if ban.type == ViolationType.banned and ban.active
    ]

    active_warnings = [
        warning
        for warning in user.violations
        if warning.type == ViolationType.warned and not warning.is_expired()
    ]

    all_violations = active_bans + active_warnings

    if not all_violations:
        raise RuntimeError("No active violations")
    all_violations.sort(key=lambda x: x.date, reverse=True)

    groups = api.groups.get_groups()
    phrase = PROFILE_VIOLATION_HEADING

    for violation in all_violations:
        phrase += get_violation_string(violation, groups) + "\n\n"

    return phrase
