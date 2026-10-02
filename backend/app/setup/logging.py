"""Stdlib logging bootstrap and structured event helpers."""

import json
import logging
from contextvars import ContextVar, Token
from typing import Any

from app.setup.config import Settings, get_settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_LOG_FORMAT = "%(levelname)s %(name)s %(message)s"


def set_request_id(request_id: str) -> Token:
    return request_id_var.set(request_id)


def reset_request_id(token: Token) -> None:
    request_id_var.reset(token)


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    payload: dict[str, Any] = {"event": event}
    request_id = request_id_var.get()
    if request_id is not None:
        payload["request_id"] = request_id
    payload.update(fields)

    if get_settings().log_json:
        logger.log(level, json.dumps(payload, default=str))
        return

    parts = [f"event={event}"]
    for key in sorted(payload.keys()):
        if key == "event":
            continue
        parts.append(f"{key}={payload[key]}")
    logger.log(level, " ".join(parts))
