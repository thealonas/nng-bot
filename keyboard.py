import json
import re

from nng_sdk.api.tickets_category import TicketShort
from nng_sdk.pydantic_models.request import Request
from nng_sdk.pydantic_models.ticket import Ticket, TicketStatus
from nng_sdk.pydantic_models.user import User
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from configuration.complex_phrases import (
    PAGINATION_TICKET_TEMPLATE,
    PAGINATION_REQUEST_TEMPLATE,
)
from configuration.keyboard_phrases import (
    KEYBOARD_PAGINATION_FORWARD,
    KEYBOARD_PAGINATION_BACKWARD,
    KEYBOARD_GO_BACK,
    KEYBOARD_PAGINATION_CREATE,
    KEYBOARD_REQUEST_UNBLOCK,
    KEYBOARD_REQUEST_COMPLAIN,
    KEYBOARD_REQUEST_NEW_FEATURE,
    KEYBOARD_REQUESTS_HISTORY,
    KEYBOARD_AGREE_WITH_RULES,
    KEYBOARD_MAIN_MENU_EDITOR,
    KEYBOARD_MAIN_MENU_PROFILE,
    KEYBOARD_MAIN_MENU_SUPPORT,
    KEYBOARD_PROFILE_INVITES,
    KEYBOARD_PROFILE_VIOLATIONS,
    KEYBOARD_SUPPORT_REQUEST,
    KEYBOARD_SUPPORT_QUESTION,
    KEYBOARD_TICKETS_REPLY,
    KEYBOARD_TICKETS_DIALOG,
    KEYBOARD_GO_TO_TICKET,
    KEYBOARD_CLOSE_TICKET,
)


class PatternPayload:
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.regex = re.compile(rf"^{pattern} (\S+)$")

    def box(self, value: str) -> str:
        return f"{self.pattern} {value}"

    def unbox(self, value: str) -> str:
        match = self.regex.match(value)
        if match:
            return match.group(1)
        raise RuntimeError("Can't retrieve value from boxed value")

    def check(self, value: str) -> bool:
        return bool(self.regex.match(value))


class Payloads:
    main_menu_editor = "main_menu_editor"
    main_menu_profile = "main_menu_profile"
    main_menu_support = "main_menu_support"

    inline_editor = "inline_editor"
    inline_editor_agree_with_rules = "inline_editor_agree_with_rules"

    inline_invite_refuse = "inline_invite_refuse"

    inline_invite = "inline_invite"

    inline_my_violations = "inline_my_violations"

    inline_support = "inline_support"

    inline_go_to_profile = "inline_go_to_profile"

    inline_requests = "inline_requests"

    inline_unban = "inline_unban"
    inline_unban_profile = "inline_unban_from_profile"
    inline_unban_attach_message = "inline_unban_attach_message"
    inline_unban_attach_message_profile = "inline_unban_attach_message_profile"
    inline_unban_send = "inline_unban_send"
    inline_unban_send_profile = "inline_unban_send_profile"
    inline_unban_send_empty = "inline_unban_send_empty"
    inline_unban_send_empty_profile = "inline_unban_send_empty_profile"
    inline_unban_cancel = "inline_unban_cancel"
    inline_unban_cancel_profile = "inline_unban_cancel_profile"

    inline_complaint = "inline_complaint"
    inline_complaint_confirm = "inline_complaint_confirm"
    inline_complaint_go_to_first_phase = "inline_complaint_go_to_first_phase"
    inline_complaint_go_to_second_phase = "inline_complaint_go_to_second_phase"
    inline_complaint_cancel = "inline_complaint_cancel"

    inline_requests_history = "inline_requests_history"

    inline_tickets = "inline_tickets"
    inline_new_ticket = "inline_new_ticket"
    inline_cancel_ticket_answer_input = "inline_cancel_ticket_answer_input"
    inline_ticket_cancel = "inline_ticket_cancel"

    inline_algolia_success = "inline_algolia_success"
    inline_algolia_fail = "inline_algolia_fail"

    inline_new_feature = "inline_new_feature"
    inline_cancel_feature_answer_input = "inline_cancel_feature_answer_input"

    @staticmethod
    def from_algolia(payload: list) -> str:
        return json.dumps({"buttons": payload, "inline": True})


class PatternPayloads:
    inline_invite_confirm = PatternPayload("inline_invite_confirm")

    inline_request_overview = PatternPayload("inline_request_overview")
    inline_request_go_to_page = PatternPayload("inline_request_go_to_page")

    inline_ticket_overview = PatternPayload("inline_ticket_overview")
    inline_ticket_dialog = PatternPayload("inline_ticket_dialog")
    inline_ticket_cancel = PatternPayload("inline_ticket_cancel")
    inline_ticket_close = PatternPayload("inline_ticket_close")
    inline_ticket_go_to_page = PatternPayload("inline_ticket_go_to_page")
    inline_reply_to_ticket = PatternPayload("inline_reply_to_ticket")


PAGE_SIZE = 4


def pagination_requests_keyboard(
    requests: list[Request], current_page: int = 1
) -> VkKeyboard:
    keyboard = VkKeyboard(inline=True)

    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    current_page_requests = requests[start_idx:end_idx]

    is_button_added = False

    for count, request in enumerate(current_page_requests, start=1):
        keyboard.add_callback_button(
            label=PAGINATION_REQUEST_TEMPLATE.build(request_id=request.request_id),
            color=VkKeyboardColor.PRIMARY,
            payload=json.dumps(
                PatternPayloads.inline_request_overview.box(str(request.request_id))
            ),
        )
        is_button_added = True

        if count % 2 == 0 and count < PAGE_SIZE and count < len(current_page_requests):
            keyboard.add_line()
            is_button_added = False

    add_back_button = current_page > 1
    add_forward_button = end_idx < len(requests)

    if (add_back_button or add_forward_button) and is_button_added:
        keyboard.add_line()
        is_button_added = False

    if add_back_button:
        keyboard.add_callback_button(
            label=KEYBOARD_PAGINATION_BACKWARD,
            color=VkKeyboardColor.SECONDARY,
            payload=json.dumps(
                PatternPayloads.inline_request_go_to_page.box(str(current_page - 1))
            ),
        )
        is_button_added = True

    if add_forward_button:
        keyboard.add_callback_button(
            label=KEYBOARD_PAGINATION_FORWARD,
            color=VkKeyboardColor.SECONDARY,
            payload=json.dumps(
                PatternPayloads.inline_request_go_to_page.box(str(current_page + 1))
            ),
        )
        is_button_added = True

    if is_button_added:
        keyboard.add_line()

    keyboard.add_callback_button(
        label=KEYBOARD_GO_BACK,
        color=VkKeyboardColor.NEGATIVE,
        payload=json.dumps(Payloads.inline_requests),
    )

    return keyboard


def pagination_tickets_keyboard(
    tickets: list[TicketShort],
    current_page: int = 1,
    back_callback: str = Payloads.inline_support,
    new_callback: str = Payloads.inline_new_ticket,
    overview_callback: PatternPayload = PatternPayloads.inline_ticket_overview,
    go_to_page_callback: PatternPayload = PatternPayloads.inline_ticket_go_to_page,
) -> VkKeyboard:
    keyboard = VkKeyboard(inline=True)

    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE

    current_tickets_page = tickets[start_idx:end_idx]

    count = 0
    if len(current_tickets_page) >= 1:
        for ticket in current_tickets_page:
            keyboard.add_callback_button(
                label=PAGINATION_TICKET_TEMPLATE.build(ticket_id=ticket.ticket_id),
                color=VkKeyboardColor.PRIMARY,
                payload=json.dumps(overview_callback.box(str(ticket.ticket_id))),
            )
            count += 1
            if (
                count % 2 == 0
                and count < PAGE_SIZE
                and count < len(current_tickets_page)
            ):
                keyboard.add_line()

    add_back_button = current_page > 1
    add_forward_button = end_idx < len(tickets)

    if add_forward_button or add_back_button:
        keyboard.add_line()

    if add_back_button:
        keyboard.add_callback_button(
            label=KEYBOARD_PAGINATION_BACKWARD,
            color=VkKeyboardColor.SECONDARY,
            payload=json.dumps(go_to_page_callback.box(str(current_page - 1))),
        )

    if add_forward_button:
        keyboard.add_callback_button(
            label=KEYBOARD_PAGINATION_FORWARD,
            color=VkKeyboardColor.SECONDARY,
            payload=json.dumps(go_to_page_callback.box(str(current_page + 1))),
        )

    if (
        add_forward_button
        or add_back_button
        or (current_tickets_page and count % 2 == 0)
    ):
        keyboard.add_line()

    keyboard.add_callback_button(
        label=KEYBOARD_PAGINATION_CREATE,
        color=VkKeyboardColor.SECONDARY,
        payload=json.dumps(new_callback),
    )

    keyboard.add_line()

    keyboard.add_callback_button(
        label=KEYBOARD_GO_BACK,
        color=VkKeyboardColor.NEGATIVE,
        payload=json.dumps(back_callback),
    )

    return keyboard


def cancel_request_keyboard() -> str:
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_unban_cancel),
    )
    return keyboard.get_keyboard()


def cancel_ticket_keyboard() -> str:
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_ticket_cancel),
    )
    return keyboard.get_keyboard()


def profile_keyboard(has_warnings: bool, is_banned: bool) -> str:
    keyboard = VkKeyboard(inline=True)
    if not is_banned:
        keyboard.add_callback_button(
            KEYBOARD_PROFILE_INVITES,
            VkKeyboardColor.SECONDARY,
            json.dumps(Payloads.inline_invite),
        )

    if has_warnings or is_banned:
        keyboard.add_callback_button(
            KEYBOARD_PROFILE_VIOLATIONS,
            VkKeyboardColor.SECONDARY,
            json.dumps(Payloads.inline_my_violations),
        )
    return keyboard.get_keyboard()


def support_keyboard() -> str:
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_SUPPORT_REQUEST,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.inline_requests),
    )
    keyboard.add_callback_button(
        KEYBOARD_SUPPORT_QUESTION,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.inline_tickets),
    )
    return keyboard.get_keyboard()


def _back_to_keyboard(payload: str) -> str:
    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(payload),
    )
    return keyboard.get_keyboard()


def back_to_violations_keyboard() -> str:
    return _back_to_keyboard(Payloads.inline_my_violations)


def back_to_requests_keyboard() -> str:
    return _back_to_keyboard(Payloads.inline_requests)


def back_to_requests_history_keyboard() -> str:
    return _back_to_keyboard(Payloads.inline_requests_history)


def tickets_keyboard(ticket_id: int, is_closed: bool) -> str:
    keyboard = VkKeyboard(inline=True)
    payload = PatternPayloads.inline_reply_to_ticket.box(str(ticket_id))
    back_payload = Payloads.inline_tickets

    if not is_closed:
        keyboard.add_callback_button(
            KEYBOARD_TICKETS_REPLY,
            VkKeyboardColor.SECONDARY,
            json.dumps(payload),
        )

    keyboard.add_callback_button(
        KEYBOARD_TICKETS_DIALOG,
        VkKeyboardColor.SECONDARY,
        json.dumps(PatternPayloads.inline_ticket_dialog.box(str(ticket_id))),
    )

    keyboard.add_line()

    if not is_closed:
        keyboard.add_callback_button(
            KEYBOARD_CLOSE_TICKET,
            VkKeyboardColor.SECONDARY,
            json.dumps(PatternPayloads.inline_ticket_close.box(str(ticket_id))),
        )

        keyboard.add_line()

    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(back_payload),
    )

    return keyboard.get_keyboard()


def go_to_ticket_keyboard(ticket_id: int) -> str:
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_TO_TICKET,
        VkKeyboardColor.SECONDARY,
        json.dumps(PatternPayloads.inline_ticket_overview.box(str(ticket_id))),
    )
    keyboard.add_line()
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_support),
    )
    return keyboard.get_keyboard()


def tickets_dialog_keyboard(ticket_id: int | str, is_closed: bool) -> str:
    keyboard = VkKeyboard(inline=True)
    payload = PatternPayloads.inline_reply_to_ticket.box(str(ticket_id))
    back_payload = Payloads.inline_tickets

    if not is_closed:
        keyboard.add_callback_button(
            KEYBOARD_TICKETS_REPLY,
            VkKeyboardColor.SECONDARY,
            json.dumps(payload),
        )
        keyboard.add_line()

        keyboard.add_callback_button(
            KEYBOARD_CLOSE_TICKET,
            VkKeyboardColor.SECONDARY,
            json.dumps(PatternPayloads.inline_ticket_close.box(str(ticket_id))),
        )

        keyboard.add_line()

    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(back_payload),
    )

    return keyboard.get_keyboard()


def tickets_logs_keyboard(ticket: Ticket) -> str:
    keyboard = VkKeyboard(inline=True)

    ticket_id = ticket.ticket_id
    is_closed = ticket.status == TicketStatus.closed

    payload = PatternPayloads.inline_reply_to_ticket.box(str(ticket_id))
    go_to_payload = PatternPayloads.inline_ticket_overview.box(str(ticket_id))

    if not is_closed:
        keyboard.add_callback_button(
            KEYBOARD_TICKETS_REPLY,
            VkKeyboardColor.SECONDARY,
            json.dumps(payload),
        )

    keyboard.add_callback_button(
        KEYBOARD_GO_TO_TICKET,
        VkKeyboardColor.SECONDARY,
        json.dumps(go_to_payload),
    )

    if not is_closed:
        keyboard.add_line()

        keyboard.add_callback_button(
            KEYBOARD_CLOSE_TICKET,
            VkKeyboardColor.SECONDARY,
            json.dumps(PatternPayloads.inline_ticket_close.box(str(ticket_id))),
        )

    return keyboard.get_keyboard()


def back_to_tickets_keyboard() -> str:
    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_tickets),
    )
    return keyboard.get_keyboard()


def cancel_ticket_answer_input_with_id(ticket_id: str) -> str:
    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(PatternPayloads.inline_ticket_cancel.box(ticket_id)),
    )
    return keyboard.get_keyboard()


def cancel_ticket_answer_input() -> str:
    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_tickets),
    )
    return keyboard.get_keyboard()


def cancel_feature_answer_input() -> str:
    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_cancel_feature_answer_input),
    )
    return keyboard.get_keyboard()


def requests_keyboard(user: User) -> str:
    keyboard = VkKeyboard(inline=True)
    is_banned: bool = user.has_active_violation()
    if is_banned:
        keyboard.add_callback_button(
            KEYBOARD_REQUEST_UNBLOCK,
            VkKeyboardColor.NEGATIVE,
            json.dumps(Payloads.inline_unban),
        )
        keyboard.add_line()

    keyboard.add_callback_button(
        KEYBOARD_REQUEST_COMPLAIN,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_complaint),
    )

    keyboard.add_callback_button(
        KEYBOARD_REQUEST_NEW_FEATURE,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_new_feature),
    )

    keyboard.add_line()

    keyboard.add_callback_button(
        KEYBOARD_REQUESTS_HISTORY,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.inline_requests_history),
    )

    keyboard.add_line()

    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.inline_support),
    )

    return keyboard.get_keyboard()


def agree_with_rules_keyboard() -> str:
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_AGREE_WITH_RULES,
        VkKeyboardColor.POSITIVE,
        json.dumps(Payloads.inline_editor_agree_with_rules),
    )
    return keyboard.get_keyboard()


def main_menu_keyboard() -> str:
    keyboard = VkKeyboard(one_time=False, inline=False)
    keyboard.add_button(
        KEYBOARD_MAIN_MENU_EDITOR,
        VkKeyboardColor.PRIMARY,
        json.dumps(Payloads.main_menu_editor),
    )
    keyboard.add_line()
    keyboard.add_button(
        KEYBOARD_MAIN_MENU_PROFILE,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.main_menu_profile),
    )
    keyboard.add_button(
        KEYBOARD_MAIN_MENU_SUPPORT,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.main_menu_support),
    )
    return keyboard.get_keyboard()
