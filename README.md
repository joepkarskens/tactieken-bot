# tactieken-bot

Telegram-bot die elke dag om 12:30 (Nederlandse tijd) een nieuwe campagnetactiek stuurt voor DeGoedeZaak.

## Hoe het werkt

- Elke dag om 12:30 NL-tijd genereert de bot een nieuwe tactiek via de Anthropic API en stuurt 'm naar Telegram.
- Onder elk bericht staat een **Volgende tactiek**-knop. Druk erop om binnen ongeveer 5 minuten een nieuwe tactiek te krijgen (de polling-workflow draait elke 5 minuten).
- Eerder verstuurde tactieken staan in `history.json`, zodat de bot zichzelf niet herhaalt.

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
