"""Alert Engine — in-app (WebSocket + feed), Telegram, and email (SMTP).

Channels activate from Settings/env; in-app always works. Triggers:
signal armed/entry/target/SL, setup forming, scanner events.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import time
import uuid
from email.message import EmailMessage

import httpx

from ..ws.manager import manager

log = logging.getLogger("alerts")

config: dict[str, str] = {
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "smtp_host": "", "smtp_port": "587", "smtp_user": "", "smtp_pass": "", "email_to": "",
}

_feed: list[dict] = []


def feed(limit: int = 100) -> list[dict]:
    return list(reversed(_feed[-limit:]))


async def send(kind: str, title: str, body: str, symbol: str = "",
               data: dict | None = None) -> dict:
    alert = {
        "id": str(uuid.uuid4())[:8],
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,            # ENTRY | TARGET | SL | ARMED | SETUP | SCANNER | SYSTEM | MOVE
        "symbol": symbol,
        "title": title,
        "body": body,
        # RC1.16.16 — optional structured payload so consumers (Voice Tanglish
        # composer, future Telegram templates) format from real fields instead
        # of parsing display strings. Additive; existing consumers unaffected.
        "data": data or None,
    }
    _feed.append(alert)
    del _feed[:-300]

    # in-app push over the live socket (also drives browser notifications)
    await manager.broadcast("alert", alert)

    if config["telegram_bot_token"] and config["telegram_chat_id"]:
        asyncio.create_task(_telegram(f"*{title}*\n{body}"))
    if config["smtp_host"] and config["email_to"]:
        asyncio.create_task(asyncio.to_thread(_email, title, body))
    return alert


async def _telegram(text: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage",
                json={"chat_id": config["telegram_chat_id"], "text": text, "parse_mode": "Markdown"},
            )
    except Exception as e:
        log.warning("telegram send failed: %s", e)


def _email(title: str, body: str) -> None:
    try:
        msg = EmailMessage()
        msg["Subject"] = f"[Cloud AI Trader] {title}"
        msg["From"] = config["smtp_user"]
        msg["To"] = config["email_to"]
        msg.set_content(body)
        with smtplib.SMTP(config["smtp_host"], int(config["smtp_port"] or 587)) as s:
            s.starttls()
            if config["smtp_user"]:
                s.login(config["smtp_user"], config["smtp_pass"])
            s.send_message(msg)
    except Exception as e:
        log.warning("email send failed: %s", e)
