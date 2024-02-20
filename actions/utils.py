from typing import Optional

from nng_sdk.pydantic_models.group import Group
from nng_sdk.pydantic_models.request import Request, RequestType
from nng_sdk.pydantic_models.user import BanPriority
from configuration.phrases import (
    PRIORITY_GREEN,
    PRIORITY_TEAL,
    PRIORITY_ORANGE,
    PRIORITY_RED,
    COMPLAIN_STATUS_APPROVED,
    COMPLAIN_STATUS_DENIED,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_INVALID,
    TRUST_LEVEL_HIGH,
    TRUST_LEVEL_MEDIUM,
    TRUST_LEVEL_LOW,
    TRUST_LEVEL_VERY_LOW,
    TICKET_STATUS_UNREVIEWED,
    TRUST_LEVEL_MAX,
)


def priority_to_string(priority: BanPriority) -> str:
    match priority:
        case BanPriority.green:
            return PRIORITY_GREEN
        case BanPriority.teal:
            return PRIORITY_TEAL
        case BanPriority.orange:
            return PRIORITY_ORANGE
        case BanPriority.red:
            return PRIORITY_RED
    return "-"


def request_status_phrase(request: Request) -> str:
    if not request.answered:
        return TICKET_STATUS_UNREVIEWED

    if request.request_type == RequestType.complaint:  # если запрос - жалоба
        match request.decision:
            case True:
                return COMPLAIN_STATUS_APPROVED
            case False:
                return COMPLAIN_STATUS_DENIED

    if request.request_type == RequestType.unblock:  # если запрос на разблокировку
        match request.decision:
            case True:
                return REQUEST_STATUS_APPROVED
            case False:
                return REQUEST_STATUS_DENIED

    return REQUEST_STATUS_INVALID


def trust_to_string(trust: int) -> str:
    if trust < 20:
        return TRUST_LEVEL_VERY_LOW
    if trust < 40:
        return TRUST_LEVEL_LOW
    if trust < 60:
        return TRUST_LEVEL_MEDIUM
    if trust < 80:
        return TRUST_LEVEL_HIGH

    return TRUST_LEVEL_MAX


def try_get_group_screen_name(group_id: int, groups: list[Group]) -> Optional[str]:
    for group in groups:
        if group.group_id == group_id:
            return group.screen_name


def get_group_screen_name(group_id: int, groups: list[Group]) -> str:
    result = try_get_group_screen_name(group_id, groups)
    if result is None:
        return f"club{group_id}"

    return result
