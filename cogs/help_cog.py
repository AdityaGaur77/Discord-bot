import discord
from discord import app_commands
from discord.ext import commands


CURRENT_SEASON_NAME = "INTO THE DEEP (2024-2025)"
GAME_MANUAL_URL = "https://ftc-resources.firstinspires.org/file/ftc/game/manual"
FTCSCOUT_URL    = "https://ftcscout.org"
FTC_EVENTS_URL  = "https://ftc-events.firstinspires.org"

FEATURE_CATEGORIES = {
    "competition": {
        "name": "Competition Tools",
        "description": "Live FTC data and event tracking",
        "color": 0xFB8C00,
        "commands": [
            ("`/ftc myteam`",               "Quick lookup of your configured team"),
            ("`/ftc team <number>`",         "Look up any FTC team"),
            ("`/ftc teamevents <number>`",   "Events a team competed in this season"),
            ("`/ftc teamawards <number>`",   "Awards won by a team"),
            ("`/ftc event <code>`",          "Event info and details"),
            ("`/ftc rankings <code>`",       "Current event standings"),
            ("`/ftc scores <code>`",         "Recent match results"),
            ("`/ftc schedule <code>`",       "Upcoming matches"),
            ("`/ftc awards <code>`",         "Awards given at event"),
            ("`/ftc teams <code>`",          "All teams attending an event"),
            ("`/countdown set <code>`",      "Track days until competition"),
            ("`/countdown view`",            "View all active countdowns"),
            ("`/countdown next`",            "Show nearest upcoming event"),
        ],
    },
    "scouting": {
        "name": "Match Scouting",
        "description": "Track and analyze team performance",
        "color": 0x43A047,
        "commands": [
            ("`/scout add <team>`",       "Submit a match scouting report"),
            ("`/scout report <team>`",    "View aggregated team data"),
            ("`/scout top`",              "Leaderboard of top-scouted teams"),
            ("`/scout compare <a> <b>`",  "Compare two teams side by side"),
            ("`/scout export`",           "Download all scouting data as CSV"),
        ],
    },
    "team-management": {
        "name": "Team Management",
        "description": "Tasks and attendance tracking",
        "color": 0x1565C0,
        "commands": [
            ("`/task add <title>`",          "Create a task (with priority)"),
            ("`/task list`",                 "View open tasks"),
            ("`/task done <id>`",            "Mark task complete"),
            ("`/task assign`",               "Reassign a task (leadership)"),
            ("`/attendance checkin`",        "Check in to today's practice"),
            ("`/attendance list`",           "See who's checked in today"),
            ("`/attendance report`",         "View attendance stats (leadership)"),
        ],
    },
    "documentation": {
        "name": "Engineering Notebook",
        "description": "Log work for Inspire/Notebook awards",
        "color": 0x8E24AA,
        "commands": [
            ("`/buildlog add <entry>`",  "Log build/mechanical work"),
            ("`/codelog add <entry>`",   "Log programming work"),
            ("`/cadlog add <entry>`",    "Log CAD/design work"),
            ("`/notebook summary`",      "View recent log entries"),
            ("`/notebook remind`",       "Post a logging reminder"),
        ],
    },
    "outreach": {
        "name": "Outreach Tracking",
        "description": "Track community events for Connect Award",
        "color": 0x00897B,
        "commands": [
            ("`/outreach add <event>`",  "Log an outreach event"),
            ("`/outreach summary`",      "View season statistics"),
        ],
    },
    "admin": {
        "name": "Server Setup",
        "description": "Configure the bot for your team",
        "color": 0x757575,
        "commands": [
            ("`/config team <number>`",   "Set your team number and season"),
            ("`/config channels`",        "Set notification channels"),
            ("`/config view`",            "View current configuration"),
            ("`/config timezone`",        "Set server timezone"),
        ],
    },
    "moderation": {
        "name": "Moderation",
        "description": "Keep your server safe",
        "color": 0xE53935,
        "commands": [
            ("`/mod warn <member>`",        "Warn a member"),
            ("`/mod warnings <member>`",    "View member warnings"),
            ("`/mod word_add <word>`",      "Add a custom word to the filter"),
            ("`/mod word_remove <word>`",   "Remove a custom word from the filter"),
            ("`/mod word_list`",            "View custom filtered words"),
        ],
    },
}


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="features", description="Overview of all bot features")
    async def features(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="FTC Team Assistant — Features",
            description=(
                "A complete toolkit for FTC teams. "
                "Use `/help <category>` for detailed commands.\n\n"
                "**Feature Categories:**"
            ),
            color=0x1565C0,
        )

        for key, cat in FEATURE_CATEGORIES.items():
            embed.add_field(
                name=cat["name"],
                value=f"{cat['description']}\n`/help {key}` — {len(cat['commands'])} commands",
                inline=True,
            )

        embed.add_field(
            name="Quick Start",
            value=(
                "1. `/config team <number>` — Configure your team\n"
                "2. `/config channels` — Set notification channels\n"
                "3. `/ftc myteam` — Test FTC data lookup"
            ),
            inline=False,
        )
        embed.set_footer(text="Use /help <category> for detailed command info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Show commands for a feature category")
    @app_commands.describe(category="Feature category to show commands for")
    @app_commands.choices(category=[
        app_commands.Choice(name="Competition Tools",       value="competition"),
        app_commands.Choice(name="Match Scouting",         value="scouting"),
        app_commands.Choice(name="Team Management",        value="team-management"),
        app_commands.Choice(name="Engineering Notebook",   value="documentation"),
        app_commands.Choice(name="Outreach Tracking",      value="outreach"),
        app_commands.Choice(name="Server Setup (Admin)",   value="admin"),
        app_commands.Choice(name="Moderation",             value="moderation"),
    ])
    async def help_cmd(self, interaction: discord.Interaction, category: str = None):
        if category is None:
            await self.features.callback(self, interaction)
            return

        if category not in FEATURE_CATEGORIES:
            await interaction.response.send_message(
                "Unknown category. Use `/features` to see all categories.", ephemeral=True
            )
            return

        cat = FEATURE_CATEGORIES[category]
        embed = discord.Embed(
            title=cat["name"],
            description=cat["description"],
            color=cat["color"],
        )
        cmd_text = "\n".join(f"{cmd} — {desc}" for cmd, desc in cat["commands"])
        embed.add_field(name="Commands", value=cmd_text, inline=False)

        if category == "competition":
            embed.add_field(
                name="Tip",
                value="Event codes look like `USCANC1`. Find them at ftc-events.firstinspires.org",
                inline=False,
            )
        elif category == "scouting":
            embed.add_field(
                name="Tip",
                value="Scout multiple matches per team for better averages. Use `/scout top` to quickly identify strong alliance partners.",
                inline=False,
            )
        elif category == "team-management":
            embed.add_field(
                name="Priority Levels",
                value="`high` | `medium` | `low`",
                inline=False,
            )
        elif category == "documentation":
            embed.add_field(
                name="Tip",
                value="Regular logging helps with Inspire Award submissions. Use `/notebook remind` to prompt your team.",
                inline=False,
            )
        elif category == "moderation":
            embed.add_field(
                name="Note",
                value="The bot has a built-in profanity filter that is always active. Custom words can be added on top of it.",
                inline=False,
            )

        embed.set_footer(text="Use /features to see all categories")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check if the bot is responsive")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        color = 0x43A047 if latency_ms < 150 else (0xFB8C00 if latency_ms < 300 else 0xE53935)
        embed = discord.Embed(
            title="Pong!",
            description=f"WebSocket latency: **{latency_ms}ms**",
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="About this bot")
    async def about(self, interaction: discord.Interaction):
        cfg = await self.bot.db.get_config(interaction.guild_id)
        team_num = cfg.get("team_number", "Not configured") if cfg else "Not configured"

        embed = discord.Embed(
            title="FTC Team Assistant",
            description=(
                "A Discord bot built for FIRST Tech Challenge teams.\n"
                "Manage tasks, scouting, attendance, engineering notebook logs, "
                "outreach tracking, and live FTC event data."
            ),
            color=0x1565C0,
        )
        embed.add_field(name="Team",        value=str(team_num))
        embed.add_field(name="Season",      value=CURRENT_SEASON_NAME)
        embed.add_field(name="Servers",     value=str(len(self.bot.guilds)))
        embed.add_field(name="Data Source", value=f"[ftcscout.org]({FTCSCOUT_URL}) (public API)")
        embed.add_field(name="discord.py",  value=discord.__version__)
        embed.set_footer(text="Built for FTC teams | /features for all commands")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="links", description="Useful FTC links and resources")
    async def links(self, interaction: discord.Interaction):
        embed = discord.Embed(title="FTC Resources", color=0x1565C0)
        embed.add_field(
            name="Official Documentation",
            value=(
                f"[Game Manual]({GAME_MANUAL_URL})\n"
                f"[FTC Events & Scores]({FTC_EVENTS_URL})\n"
                "[FTC Forum](https://ftcforum.firstinspires.org)\n"
                "[FTC Docs](https://ftc-docs.firstinspires.org)"
            ),
            inline=False,
        )
        embed.add_field(
            name="Community Tools",
            value=(
                f"[FTC Scout (stats/OPR)]({FTCSCOUT_URL})\n"
                "[FTC Stats](https://www.ftcstats.org)\n"
                "[FTC ML (predictions)](https://www.ftcml.com)\n"
                "[Road Runner](https://rr.brott.dev/docs/v1-0/guides/quickstart/)"
            ),
            inline=False,
        )
        embed.add_field(
            name="Programming",
            value=(
                "[FTC SDK](https://github.com/FIRST-Tech-Challenge/FtcRobotController)\n"
                "[Java Docs](https://javadoc.io/doc/org.firstinspires.ftc)\n"
                "[Blocks Guide](https://ftc-docs.firstinspires.org/en/latest/programming_resources/blocks/Blocks-Tutorial.html)"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="season", description="Current FTC season info")
    async def season(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"FTC Season — {CURRENT_SEASON_NAME}",
            color=0xFB8C00,
        )
        embed.add_field(
            name="Game",
            value="INTO THE DEEP — collect samples and specimens, ascend the submersible",
            inline=False,
        )
        embed.add_field(
            name="Key Dates (2024-25)",
            value=(
                "**Sep 7, 2024** — Kickoff\n"
                "**Oct–Jan** — League meets / qualifiers\n"
                "**Jan–Feb** — State/regional championships\n"
                "**Apr 2025** — World Championship (Houston)"
            ),
            inline=False,
        )
        embed.add_field(
            name="Resources",
            value=f"[Game Manual]({GAME_MANUAL_URL}) | [FTC Events]({FTC_EVENTS_URL})",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a quick yes/no poll")
    @app_commands.describe(question="The poll question")
    async def poll(self, interaction: discord.Interaction, question: str):
        embed = discord.Embed(title="Poll", description=question, color=0x1565C0)
        embed.set_footer(text=f"Asked by {interaction.user.display_name} | React to vote")
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await message.add_reaction("🤷")


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
