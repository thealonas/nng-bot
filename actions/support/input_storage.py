from enum import StrEnum

from helpers.dialog_stages import DialogStages


class SupportStages(StrEnum):
    complaint_message_input = "complaint_message_input"
    complaint_comment_input = "complaint_comment_input"
    unban_message_input = "unban_message_input"


class UnbanPayloads(StrEnum):
    attach = "attach"
    send = "send"


stages = DialogStages()
