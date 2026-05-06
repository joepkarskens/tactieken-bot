"""Polt Telegram op 'Volgende tactiek'/'Favoriet'-button-presses en notitie-replies."""
import json
import os
from datetime import datetime
from pathlib import Path

import requests

from bot import load_history, save_history, send_new_tactic

REPO_DIR = Path(__file__).resolve().parent
OFFSET_FILE = REPO_DIR / "offset.txt"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])


def load_offset():
    if not OFFSET_FILE.exists():
        return 0
    raw = OFFSET_FILE.read_text().strip()
    return int(raw) if raw else 0


def save_offset(offset):
    OFFSET_FILE.write_text(str(offset))


def get_updates(offset):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {
        "timeout": 0,
        "allowed_updates": json.dumps(["callback_query", "message"]),
    }
    if offset:
        params["offset"] = offset
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("result", [])


def answer_callback(cb_id, text=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": cb_id}
    if text:
        payload["text"] = text
    requests.post(url, json=payload, timeout=15)


def send_message(text, reply_to_message_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ALLOWED_CHAT_ID, "text": text}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    requests.post(url, json=payload, timeout=15)


def edit_keyboard(chat_id, message_id, tactic_id, is_favorite):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup"
    fav_label = "✅ Favoriet" if is_favorite else "⭐ Favoriet"
    keyboard = [
        [
            {"text": fav_label, "callback_data": f"fav:{tactic_id}"},
            {"text": "Volgende tactiek", "callback_data": "volgende"},
        ]
    ]
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": {"inline_keyboard": keyboard},
    }
    requests.post(url, json=payload, timeout=15)


def handle_callback(cb):
    from_chat = str(cb.get("message", {}).get("chat", {}).get("id", ""))
    if from_chat != ALLOWED_CHAT_ID:
        answer_callback(cb["id"])
        return

    data = cb.get("data", "")

    if data == "volgende":
        answer_callback(cb["id"], text="Nieuwe tactiek onderweg...")
        try:
            send_new_tactic()
        except Exception as e:
            print(f"Fout bij genereren: {e}")
        return

    if data.startswith("fav:"):
        try:
            tactic_id = int(data[4:])
        except ValueError:
            answer_callback(cb["id"])
            return

        history = load_history()
        target = next((e for e in history if e.get("id") == tactic_id), None)
        if not target:
            answer_callback(cb["id"], text="Tactiek niet gevonden")
            return

        target["favorite"] = not target.get("favorite", False)
        save_history(history)

        msg = cb.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        message_id = msg.get("message_id")
        if chat_id and message_id:
            edit_keyboard(chat_id, message_id, tactic_id, target["favorite"])

        state = "favoriet" if target["favorite"] else "niet meer favoriet"
        answer_callback(cb["id"], text=f"Gemarkeerd als {state}")
        return

    answer_callback(cb["id"])


def handle_message(msg):
    from_chat = str(msg.get("chat", {}).get("id", ""))
    if from_chat != ALLOWED_CHAT_ID:
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return
    reply_to = msg.get("reply_to_message") or {}
    reply_to_id = reply_to.get("message_id")
    if not reply_to_id:
        return

    history = load_history()
    target = next(
        (e for e in history if e.get("telegram_message_id") == reply_to_id), None
    )
    if not target:
        return

    target.setdefault("notes", []).append(
        {"date": datetime.now().strftime("%Y-%m-%d"), "text": text}
    )
    save_history(history)
    send_message(
        f'Notitie opgeslagen bij "{target.get("title", "?")}"',
        reply_to_message_id=msg.get("message_id"),
    )


def main():
    offset = load_offset()
    print(f"Start offset: {offset}")
    updates = get_updates(offset)
    print(f"Aantal updates: {len(updates)}")
    if not updates:
        return

    new_offset = offset
    for update in updates:
        new_offset = max(new_offset, update["update_id"] + 1)
        print(f"Update {update['update_id']}: keys={list(update.keys())}")
        msg_inspect = update.get("message")
        if msg_inspect:
            print(
                f"  message text={msg_inspect.get('text')!r} "
                f"reply_to={(msg_inspect.get('reply_to_message') or {}).get('message_id')}"
            )

        cb = update.get("callback_query")
        if cb:
            handle_callback(cb)
            continue

        msg = update.get("message")
        if msg:
            handle_message(msg)

    save_offset(new_offset)


if __name__ == "__main__":
    main()
