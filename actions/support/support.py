from actions.support.input_storage import stages
from keyboard import (
    support_keyboard,
    requests_keyboard,
)
from nng_sdk.pydantic_models.user import User
from nng_sdk.vk.actions import edit_message, send_message
from configuration.phrases import (
    SUPPORT_PAGE,
    REQUESTS_PAGE,
)


def handle_support(user: User):
    stages.remove_user(user.user_id)
    send_message(user.user_id, SUPPORT_PAGE, support_keyboard())


def inline_handle_support(user: User, message_id: int):
    stages.remove_user(user.user_id)
    edit_message(user.user_id, SUPPORT_PAGE, message_id, support_keyboard())


def inline_handle_requests(user: User, message_id: int):
    stages.remove_user(user.user_id)
    edit_message(user.user_id, REQUESTS_PAGE, message_id, requests_keyboard(user))
