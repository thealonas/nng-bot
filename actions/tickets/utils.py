import sentry_sdk
from nng_sdk.pydantic_models.ticket import Ticket, TicketMessage
from configuration.complex_phrases import (
    TICKET_PHRASE_CONSTRUCTOR,
    TICKET_WITH_DIALOG_CONSTRUCTOR,
    ONE_ATTACHED_FILE,
    SOME_ATTACHED_FILES,
    MANY_ATTACHED_FILES,
    TICKET_MESSAGE_ADMIN_AUTHOR,
    TICKET_MESSAGE_USER_AUTHOR,
    TICKET_MESSAGE_CONSTRUCTOR,
)


def get_ticket_string(ticket: Ticket) -> str:
    return TICKET_PHRASE_CONSTRUCTOR.build(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        created_on=ticket.opened.strftime("%d.%m.%Y"),
        ticket_message=ticket.dialog[0].message_text,
    )


def get_ticket_dialog_string(ticket: Ticket) -> str:
    return TICKET_WITH_DIALOG_CONSTRUCTOR.build(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        created_on=ticket.opened.strftime("%d.%m.%Y"),
        dialog=construct_ticket_dialog(ticket.dialog),
    )


def try_get_attachments(attachments: list[dict]) -> list[str]:
    photo_links = []

    for attachment in attachments:
        try:
            if attachment["type"] == "photo":
                sizes = attachment["photo"]["sizes"]
                # сортировка по произведению ширины на высоту
                best_quality_url = sorted(
                    sizes, key=lambda x: x["width"] * x["height"]
                )[-1]["url"]
                photo_links.append(best_quality_url)
        except (KeyError, TypeError, IndexError) as e:
            sentry_sdk.capture_exception(e)
            continue

    return photo_links


def get_attachment_string(attachments_length: int) -> str:
    last_digit = attachments_length % 10

    if last_digit == 1:
        return ONE_ATTACHED_FILE.build(count=attachments_length)
    elif 2 <= last_digit <= 4:  # если ласт цифра от 2 до 4
        return SOME_ATTACHED_FILES.build(count=attachments_length)
    else:
        return MANY_ATTACHED_FILES.build(count=attachments_length)


def construct_message(message: TicketMessage) -> str:
    message_string = TICKET_MESSAGE_CONSTRUCTOR.build(
        time_dmy=message.added.strftime("%d.%m.%Y"),
        time_hm=message.added.strftime("%H:%M"),
        author=(
            TICKET_MESSAGE_ADMIN_AUTHOR
            if message.author_admin
            else TICKET_MESSAGE_USER_AUTHOR
        ),
        text=message.message_text,
    )

    if not message.attachments:
        return message_string

    return f"{message_string}\n{get_attachment_string(len(message.attachments))}"


def construct_ticket_dialog(messages: list[TicketMessage]) -> str:
    phrase = ""
    for message in messages:
        phrase += f"{construct_message(message)}\n\n"

    return phrase
