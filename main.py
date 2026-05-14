import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv
from services.database import Database

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
logging.basicConfig(level=logging.INFO)

# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class FTCBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.db = Database("data/bot.db")

    async def setup_hook(self):
        await self.db.init()

        cogs = [
            "cogs.admin",
            "cogs.roles",
            "cogs.ftc_api",
            "cogs.tasks",
            "cogs.meetings",
            "cogs.notebook",
            "cogs.scouting",
            "cogs.outreach",
            "cogs.moderation",
            "cogs.help_cog",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"  ✓ Loaded {cog}")
            except Exception as e:
                print(f"  ✗ Failed to load {cog}: {e}")

        await self.tree.sync()
        print("✓ Slash commands synced globally")

    async def on_ready(self):
        print(f"\n{'='*40}")
        print(f"  FTC Bot ready — logged in as {self.user}")
        print(f"  Serving {len(self.guilds)} server(s)")
        print(f"{'='*40}\n")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/help • FTC Team Assistant",
            )
        )

    async def on_member_join(self, member: discord.Member):
        """Send a rich welcome embed to new members."""
        config = await self.db.get_config(member.guild.id)
        team_num = config.get("team_number", "????") if config else "????"

        embed = discord.Embed(
            title=f"👋 Welcome to Team {team_num}'s Server!",
            description=(
                f"Hey {member.mention}, glad you're here!\n\n"
                "Here's how to get started:"
            ),
            color=0x1565C0,
        )
        embed.add_field(
            name="📋 Assign Your Role",
            value="Use `/role join` to pick your subteam role\n"
            "*(Programming, Build, Drive Team, etc.)*",
            inline=False,
        )
        embed.add_field(
            name="📖 Useful Commands",
            value="`/help` — all commands\n"
            "`/ftc team <number>` — look up any FTC team\n"
            "`/task list` — open tasks\n"
            "`/meeting start` — log a meeting",
            inline=False,
        )
        embed.set_footer(text="FTC Team Assistant Bot • /help for full command list")

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass  # Member has DMs disabled


bot = FTCBot()
bot.run(os.getenv("DISCORD_TOKEN"), log_handler=handler, log_level=logging.INFO)
