import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv
from services.database import Database

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
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
            "cogs.ftc_api",
            "cogs.tasks",
            "cogs.notebook",
            "cogs.scouting",
            "cogs.outreach",
            "cogs.moderation",
            "cogs.attendance",
            "cogs.countdown",
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
        config   = await self.db.get_config(member.guild.id)
        team_num = config.get("team_number", "????") if config else "????"

        # Public greeting — posted in the server's system channel (Discord's designated welcome channel)
        public_embed = discord.Embed(
            title=f"Welcome to Team {team_num}'s Server!",
            description=f"Hey {member.mention}, welcome aboard! 👋\nUse `/help` to see everything the bot can do.",
            color=0x1565C0,
        )
        public_embed.set_thumbnail(url=member.display_avatar.url)
        public_embed.set_footer(text=f"{member.guild.name} • FTC Team Assistant")

        channel = member.guild.system_channel
        if channel and channel.permissions_for(member.guild.me).send_messages:
            await channel.send(embed=public_embed)

        # Private DM with full getting-started guide
        dm_embed = discord.Embed(
            title=f"Welcome to Team {team_num}'s Server!",
            description=(
                f"Hey {member.mention}, glad you're here!\n\n"
                "Here's how to get started:"
            ),
            color=0x1565C0,
        )
        dm_embed.add_field(
            name="Competition",
            value=(
                "`/ftc team <number>` — look up any FTC team\n"
                "`/scout add` — submit a scouting report\n"
                "`/countdown view` — upcoming competitions"
            ),
            inline=False,
        )
        dm_embed.add_field(
            name="Team Tools",
            value=(
                "`/task list` — open tasks\n"
                "`/buildlog add` — log build work\n"
                "`/attendance checkin` — check into practice"
            ),
            inline=False,
        )
        dm_embed.add_field(
            name="Help",
            value="`/help` — full command list | `/features` — overview",
            inline=False,
        )
        dm_embed.set_footer(text="FTC Team Assistant Bot — /help for all commands")

        try:
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # Member has DMs disabled — public greeting already sent above


bot = FTCBot()
bot.run(os.getenv("DISCORD_TOKEN"), log_handler=handler, log_level=logging.INFO)
