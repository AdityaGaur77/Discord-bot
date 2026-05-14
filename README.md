# FTC Team Assistant Discord Bot

A Discord bot for **FIRST Tech Challenge (FTC)** teams. Manage roles, tasks, meetings, scouting, outreach, and engineering notebook logs — all from Discord. Includes live FTC event data with no API key required.

---

## Features

| Category | Commands |
|---|---|
| 🔭 Live FTC Data | `/ftc team`, `/ftc event`, `/ftc rankings`, `/ftc scores`, `/ftc schedule`, `/ftc awards` |
| 🎭 Role Management | `/role join`, `/role assign`, `/role remove`, `/role list` |
| 📋 Task Tracking | `/task add`, `/task list`, `/task done`, `/task assign` |
| 📋 Meetings | `/meeting start`, `/meeting end`, `/meeting summary` |
| 📓 Engineering Notebook | `/buildlog`, `/codelog`, `/cadlog`, `/notebook summary` |
| 📊 Scouting | `/scout add`, `/scout report`, `/scout compare`, `/scout export` |
| 🌍 Outreach | `/outreach add`, `/outreach summary` |
| ⚙️ Admin | `/setup team`, `/setup roles`, `/setup channels`, `/config view` |
| 🛡️ Moderation | `/mod warn`, `/mod word_add`, `/mod warnings` |

## Setup

### 1. Clone and install
```bash
git clone https://github.com/yourteam/ftc-discord-bot
cd ftc-discord-bot
pip install -r requirements.txt
```

### 2. Create your `.env` file
```bash
cp .env.example .env
# Edit .env and add your DISCORD_TOKEN
```

### 3. Create a Discord bot
1. Go to https://discord.com/developers/applications
2. New Application → Bot → Reset Token → copy token into `.env`
3. Under **Privileged Gateway Intents**, enable: `Server Members Intent` and `Message Content Intent`
4. Under **OAuth2 → URL Generator**: select `bot` + `applications.commands`, then these permissions:
   - Manage Roles, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Manage Messages
5. Copy the generated URL, open in browser, invite bot to your server

### 4. Run the bot
```bash
python main.py
```

Slash commands sync automatically on first run.

### 5. First-time server setup
After the bot joins your server:
```
/setup team team_number:12345 season:2024
/setup roles
/setup channels tasks:#tasks scouting:#scouting modlog:#mod-log
```

---

## FTC Data Source

Live event data uses **[ftcscout.org](https://ftcscout.org)'s public GraphQL API** — no API key or registration needed. This means any team can run this bot immediately without requesting credentials.

The official **FTC Events API** (ftc-events.firstinspires.org) is supported as an optional enhancement via `.env` credentials.

---

## Project Structure

```
ftc-discord-bot/
├── main.py                  # Bot entry point
├── requirements.txt
├── .env                     # Your secrets (never commit)
├── .env.example             # Template
│
├── cogs/                    # Feature modules (slash commands)
│   ├── admin.py             # /setup, /config
│   ├── roles.py             # /role
│   ├── ftc_api.py           # /ftc
│   ├── tasks.py             # /task
│   ├── meetings.py          # /meeting
│   ├── notebook.py          # /buildlog /codelog /cadlog /notebook
│   ├── scouting.py          # /scout
│   ├── outreach.py          # /outreach
│   ├── moderation.py        # /mod
│   └── help_cog.py          # /help /ping /about /links /season /poll
│
├── services/                # Shared utilities
│   ├── database.py          # SQLite async database layer
│   ├── ftc_client.py        # FTC Scout GraphQL API client
│   └── permissions.py       # Role-gated command decorators
│
└── data/
    └── bot.db               # Auto-created SQLite database
```

---

## Recommended FTC Roles

Created automatically by `/setup roles`:

`Coach` · `Mentor` · `Captain` · `Programming Lead` · `Build Lead` · `CAD Lead` · `Drive Team` · `Driver` · `Human Player` · `Scouting Lead` · `Scout` · `Notebooker` · `Outreach Lead` · `Safety Lead` · `New Member`

---

## Deployment

### Local
```bash
python main.py
```

### Railway / Render / Replit
- Set `DISCORD_TOKEN` as an environment variable in the dashboard
- Start command: `python main.py`

### systemd (Linux VPS)
Create `/etc/systemd/system/ftcbot.service`:
```ini
[Unit]
Description=FTC Discord Bot

[Service]
WorkingDirectory=/home/user/ftc-discord-bot
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable ftcbot && sudo systemctl start ftcbot
```

---

## Version Roadmap

**v1 (current)** — Core team management + live FTC data  
**v2** — `/compare` OPR, `/deadline`, `/countdown`, `/attendance`  
**v3** — Web dashboard, Google Sheets export, AI notebook summary  

---

## Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Built with [discord.py](https://discordpy.readthedocs.io) • Data by [ftcscout.org](https://ftcscout.org)
