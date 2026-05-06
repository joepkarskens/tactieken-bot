"""Polt Telegram op 'Volgende tactiek'-button-presses en stuurt nieuwe tactieken."""
import json
import os
from pathlib import Path

import requests

from bot import send_new_tactic

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
        "allowed_updates": json.dumps(["callback_query"]),
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


def get_webhook_info():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    r = requests.get(url, timeout=15)
    return r.json()


def main():
    info = get_webhook_info()
    print(f"WebhookInfo: {info}")
    webhook_url = info.get("result", {}).get("url", "")
    if webhook_url:
        print(f"WAARSCHUWING: Webhook actief op {webhook_url}. Callbacks gaan daarheen, niet naar getUpdates.")
        print("Verwijder met: curl 'https://api.telegram.org/bot<TOKEN>/deleteWebhook'")

    offset = load_offset()
    print(f"Start offset: {offset}")
    updates = get_updates(offset)
    print(f"Aantal updates: {len(updates)}")
    if not updates:
        return

    new_offset = offset
    for update in updates:
        new_offset = max(new_offset, update["update_id"] + 1)
        cb = update.get("callback_query")
        if not cb:
            continue

        from_chat = str(cb.get("message", {}).get("chat", {}).get("id", ""))
        if from_chat != ALLOWED_CHAT_ID:
            answer_callback(cb["id"])
            continue

        if cb.get("data") != "volgende":
            answer_callback(cb["id"])
            continue

        answer_callback(cb["id"], text="Nieuwe tactiek onderweg...")
        try:
            send_new_tactic()
        except Exception as e:
            print(f"Fout bij genereren: {e}")

    save_offset(new_offset)


if __name__ == "__main__":
    main()
