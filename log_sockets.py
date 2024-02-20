import asyncio
import json
import os
from typing import Callable

import sentry_sdk
import websockets
from nng_sdk.api.api import NngApi
from nng_sdk.api.models import EditorLog
from nng_sdk.api.requests_category import RequestWebsocketLog
from nng_sdk.api.tickets_category import TicketWebsocketLog
from nng_sdk.api.watchdog_category import WatchdogWebsocketLog
from nng_sdk.one_password.op_connect import OpConnect
from nng_sdk.vk.actions import tick_online_as_user
from vk_api import ApiError
from websockets import WebSocketException

from actions.notify import notify_editor, notify_ticket, notify_request, notify_watchdog
from logger import get_logger

api_url = str(os.environ.get("NNG_API_URL"))
logger = get_logger()


def raw_websocket_url(target_url: str, path: str):
    return (
        target_url.replace("http://", "ws://").replace("https://", "wss://")
        + f"/{path}"
    )


def auth_websocket_url(target_url: str, path: str, token: str):
    return raw_websocket_url(target_url, path) + "?token=" + token


async def online_ticker(op: OpConnect):
    bot_group_id = op.get_bot_group()
    while True:
        try:
            tick_online_as_user(bot_group_id.group_id)
        except ApiError:
            pass
        await asyncio.sleep(60 * 60)


async def connect_and_receive(url: str, on_receive: Callable[[dict], None]):
    while True:
        async with websockets.connect(url) as websocket:
            try:
                message = await websocket.recv()
                json_dict = json.loads(message)
                on_receive(json_dict)
            except WebSocketException as e:
                sentry_sdk.capture_exception(e)
                logger.warning(
                    f"соеденение {websocket.path} закрыто, пытаюсь переподключиться..."
                )
                await asyncio.sleep(5)
                continue


async def receive_editor_logs(api: NngApi):
    def receive(json_dict: dict):
        try:
            log: EditorLog = EditorLog.model_validate(json_dict)
            notify_editor(log, api)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception(e)

    uri = auth_websocket_url(api_url, "editor/logs", api.token)
    await connect_and_receive(uri, receive)


async def receive_requests_logs(api: NngApi):
    def receive(json_dict: dict):
        try:
            log: RequestWebsocketLog = RequestWebsocketLog.model_validate(json_dict)
            notify_request(log, api)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception(e)

    uri = auth_websocket_url(api_url, "requests/logs", api.token)
    await connect_and_receive(uri, receive)


async def receive_tickets_logs(api: NngApi):
    def receive(json_dict: dict):
        try:
            log: TicketWebsocketLog = TicketWebsocketLog.model_validate(json_dict)
            notify_ticket(log, api)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception(e)

    uri = auth_websocket_url(api_url, "tickets/logs", api.token)
    await connect_and_receive(uri, receive)


async def receive_watchdog_logs(api: NngApi):
    def receive(json_dict: dict):
        try:
            log: WatchdogWebsocketLog = WatchdogWebsocketLog.model_validate(json_dict)
            notify_watchdog(log, api)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception(e)

    uri = auth_websocket_url(api_url, "watchdog/logs", api.token)
    await connect_and_receive(uri, receive)
