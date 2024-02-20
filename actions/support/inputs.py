import json

from nng_sdk.api.api import NngApi
from nng_sdk.api.utils_category import GetCommentInfoResponse
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import send_message
from vk_api.keyboard import VkKeyboardColor, VkKeyboard

from actions.support.input_storage import SupportStages, stages, UnbanPayloads
from configuration.complex_phrases import (
    EDITOR_COMPLAIN_CONFIRM,
    SUPPORT_UNBLOCK_CONFIRM,
)
from configuration.keyboard_phrases import KEYBOARD_GO_BACK, KEYBOARD_SEND
from configuration.phrases import (
    EDITOR_COMPLAIN_ATTACH_MESSAGE,
    NOT_NNG_COMMENT,
    INVALID_LINK,
)
from helpers.dialog_stages import DialogStage
from keyboard import Payloads


def reset_user_inputs(user_id: int):
    stages.remove_user(user_id)


def handle_inputs(user: User, api: NngApi, message_text: str):
    stage = stages.get_user(user.user_id)
    if not stage:
        return

    handle_unban_inputs(user, stage, message_text)
    handle_complaint_inputs(user, api, stage, message_text)


def handle_unban_inputs(user: User, stage: DialogStage, message_text: str):
    if stage.current_stage != SupportStages.unban_message_input:
        return

    keyboard: VkKeyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        KEYBOARD_SEND,
        VkKeyboardColor.POSITIVE,
        json.dumps(stage.get_payload(UnbanPayloads.send) or Payloads.inline_unban_send),
    )

    keyboard.add_callback_button(
        KEYBOARD_GO_BACK,
        VkKeyboardColor.NEGATIVE,
        json.dumps(
            stage.get_payload(UnbanPayloads.attach)
            or Payloads.inline_unban_attach_message
        ),
    ),

    send_message(
        user.user_id,
        SUPPORT_UNBLOCK_CONFIRM.build(message=message_text or "❌"),
        keyboard.get_keyboard(),
    )


def handle_complaint_inputs(
    user: User, api: NngApi, stage: DialogStage, message_text: str
):
    current_stage = stage.current_stage

    if current_stage not in [
        SupportStages.complaint_comment_input,
        SupportStages.complaint_message_input,
    ]:
        return

    if current_stage == SupportStages.complaint_message_input:
        keyboard: VkKeyboard = VkKeyboard(inline=True)
        keyboard.add_callback_button(
            KEYBOARD_SEND,
            VkKeyboardColor.POSITIVE,
            json.dumps(Payloads.inline_complaint_confirm),
        )

        keyboard.add_callback_button(
            KEYBOARD_GO_BACK,
            VkKeyboardColor.NEGATIVE,
            json.dumps(Payloads.inline_complaint_go_to_second_phase),
        ),

        send_message(
            user.user_id,
            EDITOR_COMPLAIN_CONFIRM.build(
                comment=stage.get_stage_value(SupportStages.complaint_comment_input),
                message=message_text,
            ),
            keyboard.get_keyboard(),
        )

        stage.write_stage_value(message_text)
        return

    if current_stage == SupportStages.complaint_comment_input:
        link: str = message_text.strip()
        comment_info: GetCommentInfoResponse = api.utils.get_comment_info(link)

        back_to_keyboard = VkKeyboard(inline=True)
        back_to_keyboard.add_callback_button(
            KEYBOARD_GO_BACK,
            VkKeyboardColor.NEGATIVE,
            json.dumps(Payloads.inline_complaint_go_to_first_phase),
        )

        if not comment_info.valid:
            send_message(
                user.user_id,
                INVALID_LINK,
                back_to_keyboard.get_keyboard(),
            )
            return

        if not comment_info.is_nng:
            send_message(
                user.user_id,
                NOT_NNG_COMMENT,
                back_to_keyboard.get_keyboard(),
            )
            return

        stage.write_stage_value(comment_info.normalized_link)
        stage.move_to_stage(SupportStages.complaint_message_input)

        send_message(
            user.user_id,
            EDITOR_COMPLAIN_ATTACH_MESSAGE,
            back_to_keyboard.get_keyboard(),
        )


def awaiting_input(user: User) -> bool:
    return stages.get_user(user.user_id) is not None
