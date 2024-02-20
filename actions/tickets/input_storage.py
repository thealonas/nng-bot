from nng_sdk.pydantic_models.user import User


class TicketInputData:
    user_id: int
    ticket_id: str | None
    message_text: str | None

    def __init__(self, user_id: int, ticket_id: str | None, message_text: str | None):
        self.user_id = user_id
        self.ticket_id = ticket_id
        self.message_text = message_text


class TicketInputList:
    _users: list[TicketInputData]

    def __init__(self):
        self._users = []

    def add_user(
        self, user_id: int, ticket_id: str | None = None, message: str | None = None
    ):
        self.remove_user(user_id)
        self._users.append(TicketInputData(user_id, ticket_id, message))

    def remove_user_from_awaiting_input(self, user_id: int):
        for index, user in enumerate(
            [i for i in self._users if i.message_text is None]
        ):
            if user.user_id == user_id:
                del self._users[index]
                break

    def remove_user_from_has_text(self, user_id: int):
        for index, user in enumerate(
            [i for i in self._users if i.message_text is not None]
        ):
            if user.user_id == user_id:
                del self._users[index]
                break

    def remove_user(self, user_id: int):
        for index, user in enumerate(self._users):
            if user.user_id == user_id:
                del self._users[index]
                break

    def get_user(self, user_id: int) -> TicketInputData:
        for user in self._users:
            if user.user_id == user_id:
                return user
        raise RuntimeError("User is not in input lists")

    def awaiting_input(self, user_id: int) -> bool:
        return user_id in [
            user.user_id for user in self._users if user.message_text is None
        ]

    def user_has_text(self, user_id: int) -> bool:
        return user_id in [
            user.user_id for user in self._users if user.message_text is not None
        ]


tickets_answer_message_input: TicketInputList = TicketInputList()
features_answer_message_input: TicketInputList = TicketInputList()
tickets: TicketInputList = TicketInputList()
features: TicketInputList = TicketInputList()


def is_in_input_lists(user: User) -> bool:
    return (
        tickets_answer_message_input.awaiting_input(user.user_id)
        or features_answer_message_input.awaiting_input(user.user_id)
        or tickets.awaiting_input(user.user_id)
        or features.awaiting_input(user.user_id)
    )


def awaiting_input(user: User) -> bool:
    if tickets.awaiting_input(user.user_id):
        return True
    if features.awaiting_input(user.user_id):
        return True
    if tickets_answer_message_input.awaiting_input(user.user_id):
        return True
    if features_answer_message_input.awaiting_input(user.user_id):
        return True

    return False


def reset_user_inputs(user_id: int):
    tickets_answer_message_input.remove_user_from_awaiting_input(user_id)
    features_answer_message_input.remove_user_from_awaiting_input(user_id)
    features.remove_user_from_awaiting_input(user_id)
    tickets.remove_user_from_awaiting_input(user_id)


def reset_user_texts(user_id: int):
    tickets_answer_message_input.remove_user_from_has_text(user_id)
    features_answer_message_input.remove_user_from_has_text(user_id)
    features.remove_user_from_has_text(user_id)
    tickets.remove_user_from_has_text(user_id)
