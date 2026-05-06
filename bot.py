"""Genereert een dagelijkse campagnetactiek en stuurt deze naar Telegram."""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from anthropic import Anthropic

REPO_DIR = Path(__file__).resolve().parent
HISTORY_FILE = REPO_DIR / "history.json"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SYSTEM_PROMPT = """Je bent een tactiek-generator voor de campagne-organisatie DeGoedeZaak.

DeGoedeZaak voert digitale campagnes (vooral petities en social media) en wil het repertoire uitbreiden met meer offline en gerichte tactieken. Wel een budget inzetten, maar nooit advertentiebudget bij Meta of Google. Tactieken moeten tijd-efficient zijn, dus uitbesteden aan bureaus is gewenst. Geen vrijwilligersleger nodig.

Drie campagnepijlers:

1. Tegen extreemrechts en de rol van neoliberale partijen die extreemrechts mogelijk maken of enabelen. Landelijk niveau.
2. Publieke sector wins: uitbreiden van publieke voorzieningen als fundament van democratie. Dit verstevigt ook de strijd tegen wanhoop en economische angst die mensen naar extreemrechts drijft. Hoofdzakelijk lokale politiek, niet landelijk.
3. Hoopzaaiers: verweeft de twee eerste pijlers. Leus: "Zaai hoop, geen haat." Hoopvolle, inspirerende acties en props.

Goede tactieken kosten geld maar weinig tijd. Soorten die we waarderen: mobile billboards, opiniepeilingen via I&O Research, guerrilla projectie, wildplakcampagnes, fysieke objecten naar politici, juridische klachten, schaduwrapporten, pop-up acties, korte mini-documentaires.

FORMAT (strikt aanhouden):

**Titel** (vetgedrukt, kort en concreet, geen jargon)

Korte beschrijving van 3 tot 5 zinnen die uitlegt wat de tactiek is en waarom hij werkt.

*Toepassing op [campagnepijler]:*
Een alinea over hoe deze tactiek concreet ingezet wordt voor een van onze drie campagnes. Kies de meest passende, niet alle drie. Wees specifiek over doelgroep en timing.

*Hoe regel je dit:*
- Productie: [concrete Nederlandse leverancier of dienst]
- Verzending of uitvoering: [concrete dienst of bureau]
- Adressen of doelwitten: [waar haal je die vandaan]
- Kosten: [ruwe indicatie in euro, all-in voor X stuks]
- Levertijd: [aantal weken vanaf akkoord]
- Optioneel een 6e bullet voor specifieke aandachtspunten

STYLE:
- Nederlands
- Geen em dashes
- Korte zinnen, scanbaar
- Concrete Nederlandse bureaus en leveranciers met naam noemen waar mogelijk
- Realistische kosten- en tijdsindicaties
- Geen vage termen als "creatief" of "impactvol"
- Varieer in soort: visueel, juridisch, journalistiek, symbolisch, fysiek

VOORBEELD (volg deze stijl exact):

**Fysiek symbool naar lokale politici sturen**

Een opvallend object opsturen naar raadsleden, wethouders of gedeputeerden (of een gerichte selectie), geproduceerd en verzonden via een fulfillmentpartij. Het object zelf is de boodschap, met een kort kaartje erbij. Werkt omdat het op bureaus blijft liggen, gefotografeerd wordt en gesprek oproept in het stadhuis of provinciehuis.

*Toepassing publieke sector wins:*
Stuur elk raadslid in een gemeente die wil bezuinigen op de bibliotheek een mini-bibliotheekkaart met de tekst "Verlopen op [datum bezuinigingsbesluit]" en een kaartje met 3 cijfers over het bibliotheekgebruik in hun gemeente. Of stuur wethouders Zorg een lege medicijnstrip met etiket "Recept: investeer in de wijkverpleging". Timing: week voor de raadsvergadering of begrotingsbehandeling.

*Hoe regel je dit:*
- Productie: zoek "promotional fulfillment Nederland" of bel IGO Promo, Inkoopcollectief of Promidata
- Verzending: fulfillmenthuis pakt en verstuurt 30 tot 150 pakketjes in 1 dag
- Adressen: via gemeente- of provinciewebsite, of opvragen bij raadsgriffie
- Kosten: ruwweg 10 tot 25 euro per pakketje all-in bij 100 stuks
- Levertijd: 2 tot 3 weken vanaf akkoord ontwerp

Output ALLEEN de tactiek, geen inleidende of afsluitende zinnen, geen kopjes als "Tactiek:" ervoor."""


def load_history():
    if not HISTORY_FILE.exists():
        return []
    return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))


def save_history(history):
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def generate_tactic(history):
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    avoid_titles = [h["title"] for h in history]
    if avoid_titles:
        avoid_block = (
            "Vermijd herhaling of variatie van deze eerder verstuurde tactieken:\n- "
            + "\n- ".join(avoid_titles)
        )
    else:
        avoid_block = "Geen eerder verstuurde tactieken om te vermijden."
    user_prompt = f"{avoid_block}\n\nGenereer 1 nieuwe tactiek, exact in het format hierboven."

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()


def extract_title(tactic_text):
    """Eerste regel, ontdaan van markdown-bold."""
    first_line = tactic_text.strip().split("\n", 1)[0].strip()
    return first_line.replace("**", "").strip()


def md_to_telegram_v2(text):
    """Converteer **bold** en *italic* naar Telegram MarkdownV2 met escapes."""
    BOLD_OPEN, BOLD_CLOSE = "", ""
    ITAL_OPEN, ITAL_CLOSE = "", ""

    text = re.sub(
        r"\*\*(.+?)\*\*",
        lambda m: BOLD_OPEN + m.group(1) + BOLD_CLOSE,
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\*(.+?)\*",
        lambda m: ITAL_OPEN + m.group(1) + ITAL_CLOSE,
        text,
        flags=re.DOTALL,
    )

    special = "_*[]()~`>#+-=|{}.!\\"
    out = []
    for ch in text:
        if ch in special:
            out.append("\\" + ch)
        else:
            out.append(ch)
    text = "".join(out)

    text = text.replace(BOLD_OPEN, "*").replace(BOLD_CLOSE, "*")
    text = text.replace(ITAL_OPEN, "_").replace(ITAL_CLOSE, "_")
    return text


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": md_to_telegram_v2(text),
        "parse_mode": "MarkdownV2",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Volgende tactiek", "callback_data": "volgende"}]
            ]
        },
    }
    r = requests.post(url, json=payload, timeout=30)
    if not r.ok:
        print(f"MarkdownV2 mislukte ({r.status_code}): {r.text}", file=sys.stderr)
        payload["text"] = text
        payload.pop("parse_mode", None)
        r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()


def send_new_tactic():
    history = load_history()
    tactic = generate_tactic(history)
    send_to_telegram(tactic)
    title = extract_title(tactic)
    history.append({"date": datetime.now().strftime("%Y-%m-%d"), "title": title})
    save_history(history)
    print(f"Verstuurd: {title}")


if __name__ == "__main__":
    send_new_tactic()
