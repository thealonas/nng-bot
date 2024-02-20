from typing import Optional


class DialogStage:
    user_id: int
    current_stage: str
    stages_history: dict[str, str]
    initial_back_payload: dict[str, str]

    def __init__(
        self,
        user_id: int,
        initial_stage: str,
        initial_back_payload: Optional[dict[str, str]] = None,
    ):
        self.user_id = user_id
        self.current_stage = initial_stage
        self.stages_history = {initial_stage: ""}
        self.initial_back_payload = initial_back_payload

    def get_stage_value(self, stage: str) -> Optional[str]:
        return self.stages_history.get(stage)

    def write_stage_value(self, value: str):
        self.stages_history[self.current_stage] = value

    def get_payload(self, key: str) -> Optional[str]:
        return self.initial_back_payload.get(key) if self.initial_back_payload else None

    def move_to_stage(self, stage: str):
        self.current_stage = stage
        self.stages_history[stage] = self.current_stage

    def finish(self):
        self.current_stage = ""


class DialogStages:
    __users_and_steps: dict[int, DialogStage]

    def __init__(self):
        self.__users_and_steps = {}

    def get_user(self, user_id: int) -> Optional[DialogStage]:
        return self.__users_and_steps.get(user_id)

    def add_or_reset_user(
        self,
        user_id: int,
        initial_stage: str,
        initial_back_payload: Optional[dict[str, str]] = None,
    ) -> DialogStage:
        self.__users_and_steps[user_id] = DialogStage(
            user_id, initial_stage, initial_back_payload
        )
        return self.__users_and_steps[user_id]

    def remove_user(self, user_id: int):
        if user_id in self.__users_and_steps:
            del self.__users_and_steps[user_id]
