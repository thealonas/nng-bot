import json

from nng_sdk.api.api import NngApi
from nng_sdk.api.requests_category import PutRequestResponse, PutRequest
from nng_sdk.pydantic_models.request import RequestType
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import send_message_event_answer, edit_message
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from actions.support.input_storage import stages, SupportStages
from actions.support.support import inline_handle_requests
from configuration.complex_phrases import (
    FAILED_TO_OPEN_REQUEST,
    COMPLAINT_SUCCESS,
)
from configuration.keyboard_phrases import KEYBOARD_GO_BACK
from configuration.phrases import (
    REQUEST_FAILED_SNACKBAR,
    SUPPORT_PAGE,
    EDITOR_COMPLAIN,
    EDITOR_COMPLAIN_ATTACH_MESSAGE,
)
from keyboard import support_keyboard, back_to_requests_keyboard, Payloads


def inline_handle_complaint_confirm(
    user: User, api: NngApi, message_id: int, event_id: str
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

    message: str | None
    comment: str | None
    message, comment = get_message_and_comment(user.user_id)
    stages.remove_user(user.user_id)

    if message is None or comment is None:
        answer(REQUEST_FAILED_SNACKBAR)
        edit_message(user.user_id, SUPPORT_PAGE, message_id, support_keyboard())
        return

    response: PutRequestResponse = api.requests.open_request(
        PutRequest(
            request_type=RequestType.complaint,
            user_id=user.user_id,
            user_message=message,
            vk_comment=comment,
        )
    )

    if not response.success:
        edit_message(
            user.user_id,
            FAILED_TO_OPEN_REQUEST.build(response=response.response),
            message_id,
            support_keyboard(),
        )
        return

    edit_message(
        user.user_id,
        COMPLAINT_SUCCESS.build(id=response.request_id),
        message_id,
        back_to_requests_keyboard(),
    )


def inline_handle_complaint_go_to_first_phase(user: User, message_id: int):
    stages.add_or_reset_user(user.user_id, SupportStages.complaint_comment_input)
    edit_message(
        user.user_id,
        EDITOR_COMPLAIN,
        message_id,
        back_to_requests_keyboard(),
    )


def inline_handle_complaint_go_to_second_phase(user: User, message_id: int):
    user_stage = stages.get_user(user.user_id)
    if not user_stage:
        return inline_handle_complaint_go_to_first_phase(user, message_id)

    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_complaint_go_to_first_phase),
    )

    user_stage.move_to_stage(SupportStages.complaint_message_input)
    edit_message(
        user.user_id,
        EDITOR_COMPLAIN_ATTACH_MESSAGE,
        message_id,
        keyboard.get_keyboard(),
    )


def inline_handle_complaint_cancel(user: User, message_id: int):
    stages.remove_user(user.user_id)
    return inline_handle_requests(user, message_id)


def inline_handle_complaint(user: User, message_id: int):
    stages.add_or_reset_user(user.user_id, SupportStages.complaint_comment_input)

    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(Payloads.inline_complaint_cancel),
    )

    edit_message(
        user.user_id,
        EDITOR_COMPLAIN,
        message_id,
        keyboard.get_keyboard(),
    )


def get_message_and_comment(user_id: int) -> tuple[str, str] | tuple[None, None]:
    user_stage = stages.get_user(user_id)
    if user_stage is None:
        return None, None

    return user_stage.get_stage_value(
        SupportStages.complaint_message_input
    ), user_stage.get_stage_value(SupportStages.complaint_comment_input)
