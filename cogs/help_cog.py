import discord
from discord import app_commands
from discord.ext import commands
import time


CURRENT_SEASON_NAME = "INTO THE DEEP (2024-2025)"
GAME_MANUAL_URL     = "https://ftc-resources.firstinspires.org/file/ftc/game/manual"
FTCSCOUT_URL        = "https://ftcscout.org"
FTC_EVENTS_URL      = "https://ftc-events.firstinspires.org"


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available commands")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 FTC Team Assistant — Command Reference",
            description="All commands use `/`. Type `/` in Discord to browse them.",
            color=0x1565C0,
        )

        embed.add_field(
            name="🔭 FTC Live Data",
            value=(
                "`/ftc team <number>` — Team stats\n"
                "`/ftc event <code>` — Event info\n"
                "`/ftc rankings <code>` — Event standings\n"
                "`/ftc scores <code>` — Match results\n"
                "`/ftc schedule <code>` — Upcoming matches\n"
                "`/ftc awards <code>` — Event awards\n"
                "`/ftc teams <code>` — Teams at event"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎭 Roles",
            value=(
                "`/role join <role>` — Self-assign a role\n"
                "`/role list` — View available roles\n"
                "`/role assign` *(leadership)* — Assign to member\n"
                "`/role remove` *(leadership)* — Remove from member"
            ),
            inline=False,
        )
        embed.add_field(
            name="📋 Tasks",
            value=(
                "`/task add <title>` — Add a task\n"
                "`/task list` — View open tasks\n"
                "`/task done <id>` — Mark task complete\n"
                "`/task assign` *(leadership)* — Reassign a task"
            ),
            inline=False,
        )
        embed.add_field(
            name="📋 Meetings",
            value=(
                "`/meeting start` — Start a meeting\n"
                "`/meeting end <notes>` — End with summary\n"
                "`/meeting summary` — View recent meetings"
            ),
            inline=False,
        )
        embed.add_field(
            name="📓 Engineering Notebook",
            value=(
                "`/buildlog add <entry>` — Log build work\n"
                "`/codelog add <entry>` — Log code work\n"
                "`/cadlog add <entry>` — Log CAD work\n"
                "`/notebook remind` — Post reminder\n"
                "`/notebook summary` — All recent logs"
            ),
            inline=False,
        )
        embed.add_field(
            name="📊 Scouting",
            value=(
                "`/scout add <team>` — Submit a report\n"
                "`/scout report <team>` — View team data\n"
                "`/scout compare <a> <b>` — Compare teams\n"
                "`/scout export` — Download CSV"
            ),
            inline=False,
        )
        embed.add_field(
            name="🌍 Outreach",
            value=(
                "`/outreach add <event>` — Log an event\n"
                "`/outreach summary` — Season stats"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚙️ Setup (Admin)",
            value=(
                "`/setup team <number>` — Set team number\n"
                "`/setup roles` — Create FTC roles\n"
                "`/setup channels` — Configure channels\n"
                "`/config view` — View current config"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛡️ Moderation (Mod roles)",
            value=(
                "`/mod warn @member` — Warn a member\n"
                "`/mod warnings @member` — View warnings\n"
                "`/mod word_add <word>` — Add filter word\n"
                "`/mod word_list` — View filter"
            ),
            inline=False,
        )
        embed.set_footer(text="FTC Team Assistant • Data via ftcscout.org (no API key needed)")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check if the bot is responsive")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        color = 0x43A047 if latency_ms < 150 else (0xFB8C00 if latency_ms < 300 else 0xE53935)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"WebSocket latency: **{latency_ms}ms**",
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="About this bot")
    async def about(self, interaction: discord.Interaction):
        cfg = await self.bot.db.get_config(interaction.guild_id)
        team_num = cfg.get("team_number", "Not configured") if cfg else "Not configured"

        embed = discord.Embed(
            title="🤖 FTC Team Assistant",
            description=(
                "A Discord bot built for FIRST Tech Challenge teams.\n"
                "Manage roles, tasks, meetings, scouting, outreach, "
                "engineering notebook logs, and live FTC event data — all from Discord."
            ),
            color=0x1565C0,
        )
        embed.add_field(name="Team",    value=str(team_num))
        embed.add_field(name="Season",  value=CURRENT_SEASON_NAME)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Data Source", value=f"[ftcscout.org]({FTCSCOUT_URL}) (public API, no key needed)")
        embed.add_field(name="discord.py", value=discord.__version__)
        embed.set_footer(text="Built with ❤️ for FTC teams everywhere")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="links", description="Useful FTC links and resources")
    async def links(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔗 FTC Resources",
            color=0x1565C0,
        )
        embed.add_field(
            name="📖 Official Docs",
            value=(
                f"[Game Manual]({GAME_MANUAL_URL})\n"
                f"[FTC Events & Scores]({FTC_EVENTS_URL})\n"
                "[FTC Forum (FIRST Answers)](https://ftcforum.firstinspires.org)\n"
                "[FTC Dashboard](https://ftc-events.firstinspires.org)"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔍 Community Tools",
            value=(
                f"[FTC Scout (stats & OPR)]({FTCSCOUT_URL})\n"
                "[FTC Stats](https://www.ftcstats.org)\n"
                "[FTC ML (match predictions)](https://www.ftcml.com)\n"
                "[Road Runner Quickstart](https://rr.brott.dev/docs/v1-0/guides/quickstart/)"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛠️ Technical Resources",
            value=(
                "[FTC SDK GitHub](https://github.com/FIRST-Tech-Challenge/FtcRobotController)\n"
                "[FTC Java Docs](https://javadoc.io/doc/org.firstinspires.ftc)\n"
                "[Blocks Programming Guide](https://ftc-docs.firstinspires.org/en/latest/programming_resources/blocks/Blocks-Tutorial.html)"
            ),
            inline=False,
        )
        embed.set_footer(text="Run /setup team to configure team-specific links")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="season", description="Current FTC season info")
    async def season(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"🏆 FTC Season — {CURRENT_SEASON_NAME}",
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
            name="🔗 Resources",
            value=f"[Game Manual]({GAME_MANUAL_URL}) • [FTC Events]({FTC_EVENTS_URL})",
            inline=False,
        )
        embed.set_footer(text="Update /config for your season year")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a quick yes/no or choice poll")
    @app_commands.describe(question="The poll question")
    async def poll(self, interaction: discord.Interaction, question: str):
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=0x1565C0,
        )
        embed.set_footer(text=f"Asked by {interaction.user.display_name} • React to vote")
        msg = await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await message.add_reaction("🤷")


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
