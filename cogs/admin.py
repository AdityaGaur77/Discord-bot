import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_admin, is_leadership

# Recommended FTC roles to auto-create
DEFAULT_FTC_ROLES = [
    ("Coach",            0xE53935),  # Red
    ("Mentor",           0xF4511E),  # Deep Orange
    ("Captain",          0xFB8C00),  # Orange
    ("Programming Lead", 0x00897B),  # Teal
    ("Build Lead",       0x8E24AA),  # Purple
    ("CAD Lead",         0x3949AB),  # Indigo
    ("Drive Team",       0x1E88E5),  # Blue
    ("Driver",           0x039BE5),  # Light Blue
    ("Human Player",     0x00ACC1),  # Cyan
    ("Scouting Lead",    0x43A047),  # Green
    ("Scout",            0x7CB342),  # Light Green
    ("Notebooker",       0xF9A825),  # Amber
    ("Outreach Lead",    0xFFB300),  # Yellow
    ("Safety Lead",      0xE53935),  # Red
    ("New Member",       0x757575),  # Grey
]


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /setup ────────────────────────────────────────────────────────────────

    setup_group = app_commands.Group(name="setup", description="Initial server setup commands")

    @setup_group.command(name="team", description="Configure your team number and season")
    @app_commands.describe(
        team_number="Your FTC team number",
        season="Current FTC season year (e.g. 2024 for INTO THE DEEP)"
    )
    @is_admin()
    async def setup_team(self, interaction: discord.Interaction,
                         team_number: int, season: int = 2024):
        await self.bot.db.set_config(
            interaction.guild_id,
            team_number=team_number,
            season=season,
        )
        embed = discord.Embed(
            title="✅ Team Configured",
            description=f"Team **{team_number}** • Season **{season}**",
            color=0x1565C0,
        )
        embed.set_footer(text="Run /setup roles next to create FTC roles.")
        await interaction.response.send_message(embed=embed)

    @setup_group.command(name="roles", description="Auto-create all standard FTC team roles")
    @is_admin()
    async def setup_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        created, skipped = [], []

        for role_name, color in DEFAULT_FTC_ROLES:
            existing = discord.utils.get(interaction.guild.roles, name=role_name)
            if existing:
                skipped.append(role_name)
                continue
            await interaction.guild.create_role(
                name=role_name,
                color=discord.Color(color),
                reason="FTC Bot: /setup roles",
            )
            created.append(role_name)

        embed = discord.Embed(title="🎭 FTC Roles Setup", color=0x1565C0)
        if created:
            embed.add_field(
                name=f"✅ Created ({len(created)})",
                value="\n".join(f"• {r}" for r in created) or "None",
                inline=False,
            )
        if skipped:
            embed.add_field(
                name=f"⏭️ Already existed ({len(skipped)})",
                value="\n".join(f"• {r}" for r in skipped) or "None",
                inline=False,
            )
        embed.set_footer(text="Members can now use /role join to pick their role.")
        await interaction.followup.send(embed=embed)

    @setup_group.command(name="channels", description="Point the bot to your team's channels")
    @app_commands.describe(
        tasks="Channel for task notifications",
        scouting="Channel for scouting reports",
        modlog="Channel for moderation logs",
    )
    @is_admin()
    async def setup_channels(
        self,
        interaction: discord.Interaction,
        tasks: discord.TextChannel = None,
        scouting: discord.TextChannel = None,
        modlog: discord.TextChannel = None,
    ):
        kwargs = {}
        if tasks:    kwargs["tasks_channel"]    = tasks.id
        if scouting: kwargs["scouting_channel"] = scouting.id
        if modlog:   kwargs["modlog_channel"]   = modlog.id

        if not kwargs:
            await interaction.response.send_message("❌ Provide at least one channel.", ephemeral=True)
            return

        await self.bot.db.set_config(interaction.guild_id, **kwargs)

        lines = []
        if tasks:    lines.append(f"Tasks → {tasks.mention}")
        if scouting: lines.append(f"Scouting → {scouting.mention}")
        if modlog:   lines.append(f"Mod log → {modlog.mention}")

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Channels Configured",
                description="\n".join(lines),
                color=0x1565C0,
            )
        )

    # ── /config ───────────────────────────────────────────────────────────────

    config_group = app_commands.Group(name="config", description="View or update bot configuration")

    @config_group.command(name="view", description="View current bot configuration for this server")
    @is_leadership()
    async def config_view(self, interaction: discord.Interaction):
        cfg = await self.bot.db.get_config(interaction.guild_id)
        if not cfg:
            await interaction.response.send_message(
                "No config yet. Run `/setup team` first.", ephemeral=True
            )
            return

        def ch(cid):
            return f"<#{cid}>" if cid else "*(not set)*"

        embed = discord.Embed(title="⚙️ Bot Configuration", color=0x1565C0)
        embed.add_field(name="Team Number", value=str(cfg.get("team_number") or "*(not set)*"))
        embed.add_field(name="Season",      value=str(cfg.get("season", 2024)))
        embed.add_field(name="Timezone",    value=cfg.get("timezone", "America/Los_Angeles"))
        embed.add_field(name="Tasks Channel",    value=ch(cfg.get("tasks_channel")),    inline=False)
        embed.add_field(name="Scouting Channel", value=ch(cfg.get("scouting_channel")), inline=False)
        embed.add_field(name="Mod Log Channel",  value=ch(cfg.get("modlog_channel")),   inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config_group.command(name="timezone", description="Set the server timezone for deadlines/reminders")
    @app_commands.describe(tz="Timezone string, e.g. America/Los_Angeles, America/New_York")
    @is_admin()
    async def config_timezone(self, interaction: discord.Interaction, tz: str):
        await self.bot.db.set_config(interaction.guild_id, timezone=tz)
        await interaction.response.send_message(f"✅ Timezone set to `{tz}`")


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
