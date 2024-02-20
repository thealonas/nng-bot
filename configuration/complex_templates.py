from configuration.service.compex_phrase import ComplexPhrase

YOUR_ATTACHMENT = ComplexPhrase("💬 Примечание: {message}")
YOUR_MESSAGE = ComplexPhrase("Твоё сообщение: {message}")
ADMIN_ANSWER = ComplexPhrase("Ответ администрации: {response}")

COMPLAINT_LOG_RECEIVED_TITLE = ComplexPhrase(
    "‼️ Пришло обновление по твоей жалобе №{id}"
)
COMPLAINT_REQUEST_CONSTRUCTOR = ComplexPhrase(
    "‼️ Жалоба №{id}\nСтатус: {request_status}\nЖалоба отправлена: {created_on}"
)
UNBLOCK_REQUEST_CONSTRUCTOR = ComplexPhrase(
    "👁️ Запрос на разблокировку №{id}\n\n"
    "Статус: {request_status}\n"
    "Запрос подан: {created_on}"
)
UNBLOCK_REQUEST_LOG_RECEIVED_TITLE = ComplexPhrase(
    "👁️ Пришло обновление по твоему запросу на разблокировку №{id}"
)


def build_complaint_notify_log(
    log_id: any,
    request_status: str,
    user_message: str = "",
    admin_response: str = "",
) -> str:
    phrase = COMPLAINT_LOG_RECEIVED_TITLE.build(id=log_id)
    if user_message:
        phrase += "\n" + YOUR_MESSAGE.build(message=user_message)

    phrase += "\n\n"

    if request_status:
        phrase += request_status + "\n"

    if admin_response:
        phrase += ADMIN_ANSWER.build(response=admin_response)

    return phrase


def build_complaint_request(
    request_id: any,
    request_status: str,
    created_on: str,
    admin_response: str = "",
) -> str:
    phrase = COMPLAINT_REQUEST_CONSTRUCTOR.build(
        id=request_id, request_status=request_status, created_on=created_on
    )

    if admin_response:
        phrase += "\n" + ADMIN_ANSWER.build(response=admin_response)

    return phrase


def build_unblock_notify_log(
    request_id: any,
    request_status: str,
    user_message: str = "",
    admin_response: str = "",
) -> str:
    phrase = UNBLOCK_REQUEST_LOG_RECEIVED_TITLE.build(id=request_id)

    if user_message:
        phrase += "\n" + YOUR_MESSAGE.build(message=user_message)

    phrase += "\n\n" + request_status + "\n"

    if admin_response:
        phrase += ADMIN_ANSWER.build(response=admin_response)

    return phrase


def build_unblock_request(
    request_id: any, request_status: str, created_on: str, admin_response: str = ""
) -> str:
    phrase = UNBLOCK_REQUEST_CONSTRUCTOR.build(
        id=request_id, request_status=request_status, created_on=created_on
    )

    if admin_response:
        phrase += "\n" + ADMIN_ANSWER.build(response=admin_response)

    return phrase
