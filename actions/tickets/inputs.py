import json
from typing import Callable

import sentry_sdk
from nng_sdk.api.api import NngApi
from nng_sdk.api.tickets_category import AlgoliaOutput, PutTicket, UploadMessage
from nng_sdk.pydantic_models.ticket import TicketType, Ticket
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import (
    send_message,
    edit_message,
    get_by_conversation_message_id,
    vk_action,
    send_message_event_answer,
)
from nng_sdk.vk.vk_manager import VkManager
from requests import HTTPError
from vk_api import VkApiError
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import sjson_dumps

from actions.tickets.input_storage import (
    tickets_answer_message_input,
    tickets,
    features,
    reset_user_inputs,
    reset_user_texts,
)
from actions.tickets.utils import try_get_attachments
from configuration.complex_phrases import ALGOLIA_ANSWER_TEMPLATE, TICKET_SUCCESS
from configuration.keyboard_phrases import (
    KEYBOARD_ALGOLIA_ACCEPT,
    KEYBOARD_ALGOLIA_REFUSE,
    KEYBOARD_GO_BACK,
)
from configuration.phrases import (
    UNEXPECTED_ERROR,
    FEATURE_INPUT_SUCCESS,
    ALGOLIA_SUCCESS,
    REQUEST_FAILED,
    BUTTON_BROKEN,
    ALGOLIA_ANSWER,
    TICKET_ANSWER_ADDED,
)
from keyboard import (
    Payloads,
    back_to_tickets_keyboard,
    go_to_ticket_keyboard,
)


def handle_algolia_inputs(
    user: User, api: NngApi, message_text: str, attachments: str | None
):
    def rollback():  # снимает все инпуты и создаёт тикет
        reset_user_inputs(user.user_id)
        reset_user_texts(user.user_id)
        create_ticket(
            user,
            api,
            message_text,
            lambda text, lambda_keyboard: send_message(
                user.user_id, text, lambda_keyboard
            ),
            attachments,
        )
        return

    algolia_answers: list[AlgoliaOutput]
    try:
        algolia_answers = api.tickets.algolia_search(message_text.strip())
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        return rollback()  # если не получилось достать ответы алголии, то создаем тикет

    if not algolia_answers:
        return rollback()  # аналогично

    algolia = algolia_answers[0]

    ticket_keyboard: VkKeyboard = VkKeyboard(inline=True)

    ticket_keyboard.add_callback_button(
        KEYBOARD_ALGOLIA_ACCEPT,
        VkKeyboardColor.POSITIVE,
        json.dumps(Payloads.inline_algolia_success),
    )

    ticket_keyboard.add_callback_button(
        KEYBOARD_ALGOLIA_REFUSE,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_algolia_fail),
    )

    if not algolia.action:
        keyboard = ticket_keyboard.get_keyboard()
    else:
        buttons = algolia.action
        buttons.append(ticket_keyboard.lines[0])
        keyboard = sjson_dumps({"one_time": False, "inline": True, "buttons": buttons})

    send_message(
        user.user_id,
        ALGOLIA_ANSWER_TEMPLATE.build(algolia_answer=algolia.answer),
        keyboard,
    )

    tickets.add_user(user.user_id, None, message_text)


def handle_feature_input(
    user: User, api: NngApi, message_text: str, attachments: list[dict] | None
):
    if len(message_text.strip()) < 1:
        reset_user_inputs(user.user_id)

    attachments_to_link: list[str] = []
    if attachments:
        attachments_to_link = try_get_attachments(attachments)

    try:
        api.tickets.add_ticket(
            PutTicket(
                user_id=user.user_id,
                type=TicketType.new_feature,
                text=message_text.strip(),
                attachments=attachments_to_link,
            )
        )
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        keyboard = back_to_tickets_keyboard()
        send_message(user.user_id, UNEXPECTED_ERROR, keyboard)
        reset_user_inputs(user.user_id)
        return

    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.SECONDARY,
        json.dumps(Payloads.inline_requests),
    )

    reset_user_inputs(user.user_id)
    send_message(
        user.user_id,
        FEATURE_INPUT_SUCCESS,
        keyboard.get_keyboard(),
    )


def create_ticket(
    user: User,
    api: NngApi,
    text: str,
    send_callback: Callable[[str, str], None],
    attachments: list[dict] | None,
):
    attachments_to_link: list[str] = []
    if attachments:
        attachments_to_link = try_get_attachments(attachments)

    try:
        ticket_type = TicketType.question
        ticket: Ticket = api.tickets.add_ticket(
            PutTicket(
                user_id=user.user_id,
                type=ticket_type,
                text=text.strip(),
                attachments=attachments_to_link,
            )
        )
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        keyboard = back_to_tickets_keyboard()
        send_callback(UNEXPECTED_ERROR, keyboard)
        reset_user_inputs(user.user_id)
        return

    reset_user_inputs(user.user_id)
    send_callback(
        TICKET_SUCCESS.build(id=ticket.ticket_id),
        go_to_ticket_keyboard(ticket.ticket_id),
    )


def handle_answer_message_input(
    user: User, api: NngApi, message_text: str, attachments: list[dict] | None
):
    ticket_id = tickets_answer_message_input.get_user(user.user_id).ticket_id

    attachments_to_link: list[str] = []
    if attachments:
        attachments_to_link = try_get_attachments(attachments)

    back_keyboard = back_to_tickets_keyboard()

    upload = UploadMessage(
        author_admin=False,
        message_text=message_text.strip(),
        attachments=attachments_to_link,
    )

    try:
        api.tickets.add_message(ticket_id, upload)
        ticket: Ticket = api.tickets.get_ticket(ticket_id)
    except HTTPError as e:
        sentry_sdk.capture_exception(e)
        send_message(user.user_id, UNEXPECTED_ERROR, back_keyboard)
        reset_user_inputs(user.user_id)
        return

    reset_user_inputs(user.user_id)
    send_message(
        user.user_id,
        TICKET_ANSWER_ADDED,
        go_to_ticket_keyboard(ticket.ticket_id),
    )


@vk_action
def get_message(message_id: int, peer: int) -> dict:
    return (VkManager().bot.messages.getById(cmids=f"{message_id}", peer_id=peer))[
        "items"
    ][0]


def get_message_keyboard(message: dict) -> dict:
    keyboard: dict = message.get("keyboard")
    if not keyboard:
        raise RuntimeError("No keyboard in message")

    buttons = keyboard.get("buttons")
    if not buttons:
        raise RuntimeError("No buttons in keyboard")

    new_button_list = []
    for inner in buttons:
        to_append = []
        for button in inner:
            if "color" in button and button.get("action").get("type") == "open_link":
                button.pop("color")
            to_append.append(button)
        new_button_list.append(to_append)

    keyboard["buttons"] = new_button_list

    if "author_id" in keyboard:
        keyboard.pop("author_id")

    return keyboard


def is_valid_keyboard(buttons: list) -> bool:
    if not buttons:
        return False

    for inner in buttons:
        if inner:
            return True

    return False


def inline_handle_algolia_success(user: User, event_id: str, message_id: int):
    try:
        old_message = get_message(message_id, user.user_id)
    except VkApiError as e:
        sentry_sdk.capture_exception(e)
        send_message_event_answer(
            event_id,
            user.user_id,
            user.user_id,
            {"type": "show_snackbar", "text": BUTTON_BROKEN},
        )
        return

    keyboard = get_message_keyboard(old_message)
    if not is_valid_keyboard(keyboard.get("buttons")):
        new_keyboard = back_to_tickets_keyboard()
    else:
        new_buttons = keyboard.get("buttons")
        # заменяем кнопки алголии на вернуться назад в тикеты
        return_button_row = [
            {
                "action": {
                    "type": "callback",
                    "payload": sjson_dumps(Payloads.inline_tickets),
                    "label": KEYBOARD_GO_BACK,
                },
                "color": "negative",
            }
        ]

        new_buttons[-1] = return_button_row

        new_keyboard = sjson_dumps(
            {"one_time": False, "inline": True, "buttons": new_buttons}
        )

    reset_user_inputs(user.user_id)
    edit_message(
        user.user_id,
        old_message["text"].replace(ALGOLIA_ANSWER, ALGOLIA_SUCCESS),
        message_id,
        new_keyboard,
    )


def inline_handle_algolia_fail(user: User, api: NngApi, message_id: int):
    if not tickets.user_has_text(user.user_id):
        edit_message(
            user.user_id,
            REQUEST_FAILED,
            message_id,
            back_to_tickets_keyboard(),
        )
        return

    user_text = tickets.get_user(user.user_id).message_text

    reset_user_inputs(user.user_id)
    reset_user_texts(user.user_id)

    attachments: dict | None = get_by_conversation_message_id(
        user.user_id, message_id
    ).get("attachments")
    create_ticket(
        user,
        api,
        user_text,
        lambda text, keyboard: edit_message(user.user_id, text, message_id, keyboard),
        attachments,
    )


def handle_inputs(
    user: User, api: NngApi, message_text: str, attachments: list[dict] | None = None
):
    if tickets.awaiting_input(user.user_id):
        return handle_algolia_inputs(user, api, message_text, attachments)

    if features.awaiting_input(user.user_id):
        return handle_feature_input(user, api, message_text, attachments)

    if tickets_answer_message_input.awaiting_input(user.user_id):
        return handle_answer_message_input(user, api, message_text, attachments)

    raise RuntimeError(f"{user.user_id} is not presented in input lists")
