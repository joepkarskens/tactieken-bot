# tactieken-bot

Telegram-bot die elke dag om 12:30 (Nederlandse tijd) een nieuwe campagnetactiek stuurt voor DeGoedeZaak.

## Hoe het werkt

- Elke dag om 12:30 NL-tijd genereert de bot een nieuwe tactiek via de Anthropic API en stuurt 'm naar Telegram.
- Onder elk bericht staan drie knoppen, in twee rijen:
  - **⭐ Favoriet** - markeert de tactiek als favoriet (`favorite: true`). Klik nogmaals om te ontmarkeren. Knop wordt ✅ na markeren.
  - **👎 Niet geschikt** - markeert de tactiek als niet-geschikt (`downvote: true`). Klik nogmaals om te ontmarkeren. Knop wordt ⛔ na markeren.
  - **Volgende tactiek** - vraagt direct een nieuwe tactiek aan (verschijnt binnen ~5 minuten via de polling-workflow).
- Favoriet en Niet geschikt zijn wederzijds uitsluitend: één van beide markeren maakt de andere automatisch ongedaan.
- **Notitie toevoegen:** beantwoord het bot-bericht met een tekst-reply. De tekst wordt opgeslagen in `notes` van die tactiek-entry.
- Eerder verstuurde tactieken staan in `history.json`, zodat de bot zichzelf niet herhaalt.

## Hoe favorieten en downvotes het model sturen

- **Downvotes** worden actief als grens gebruikt: tactieken van hetzelfde type worden sterk vermeden.
- **Favorieten** worden als zachte inspiratie meegegeven, niet als blueprint. Het model wordt expliciet aangespoord om te varieren en niet te overfitten op je voorkeuren.
- **Wildcard-modus:** met ~33% kans (alleen als je al voorkeuren hebt gemarkeerd) negeert het model je favorieten en genereert juist iets buiten je comfort zone, om creatieve diversiteit te behouden.

## Database voor Claude Cowork

`history.json` is je database. Lees 'm in een Claude Cowork-project via deze URL:

```
https://raw.githubusercontent.com/joepkarskens/tactieken-bot/main/history.json
```

Schema per entry:

```json
{
  "id": 1714998000,
  "date": "2026-05-06",
  "title": "Naam van de tactiek",
  "favorite": true,
  "downvote": false,
  "notes": [{ "date": "2026-05-06", "text": "Korte notitie" }],
  "telegram_message_id": 12345
}
```

## Handmatig een nieuwe tactiek triggeren

Open: https://github.com/joepkarskens/tactieken-bot/actions/workflows/daily-tactic.yml en klik **Run workflow**.

## Een tactiek voor altijd skippen (negatief voorbeeld toevoegen)

Voeg een entry toe aan `history.json`:

```json
[
  { "date": "2026-05-06", "title": "Naam van een tactiek die je nooit meer wilt zien" }
]
```

Commit en push. De bot vermijdt vanaf dat moment herhaling van die titel.

## Setup en geheimen

GitHub Secrets die ingesteld moeten zijn (eenmalig):

- `ANTHROPIC_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Zet ze met `gh secret set NAAM` of via de UI: Settings -> Secrets and variables -> Actions.

## Externe trigger (cron-job.org)

Cron-job.org doet elke dag om 12:30 NL-tijd een POST naar:

```
POST https://api.github.com/repos/joepkarskens/tactieken-bot/dispatches
Headers:
  Authorization: Bearer <PAT met repo-scope>
  Accept: application/vnd.github+json
  X-GitHub-Api-Version: 2022-11-28
Body:
  {"event_type":"daily-tactic"}
```

## Bestanden

- `bot.py` - genereert tactiek en stuurt naar Telegram
- `poll.py` - polt elke 5 min op `Volgende tactiek`-button
- `history.json` - lijst van eerder verstuurde tactieken
- `offset.txt` - Telegram update_id bookmark voor de poller
- `.github/workflows/daily-tactic.yml` - draait via cron-job.org of handmatig
- `.github/workflows/poll-volgende.yml` - draait elke 5 min via schedule
