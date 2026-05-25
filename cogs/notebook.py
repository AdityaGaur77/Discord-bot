import discord
from discord import app_commands
from discord.ext import commands

LOG_TYPE_META = {
    "build": {"emoji": "🔧", "color": 0x8E24AA, "label": "Build Log"},
    "code":  {"emoji": "💻", "color": 0x00897B, "label": "Code Log"},
    "cad":   {"emoji": "📐", "color": 0x3949AB, "label": "CAD Log"},
}


def log_embed(log_type: str, entry: str, author: discord.Member, log_id: int) -> discord.Embed:
    meta = LOG_TYPE_META[log_type]
    embed = discord.Embed(
        title=f"{meta['emoji']} {meta['label']} Entry #{log_id}",
        description=entry,
        color=meta["color"],
    )
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    return embed


class NotebookCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Build / Code / CAD logs ───────────────────────────────────────────────

    buildlog_group = app_commands.Group(name="buildlog", description="Mechanical build log entries")
    codelog_group  = app_commands.Group(name="codelog",  description="Programming log entries")
    cadlog_group   = app_commands.Group(name="cadlog",   description="CAD design log entries")

    async def _add_log(self, interaction: discord.Interaction, log_type: str, entry: str):
        log_id = await self.bot.db.add_log(
            interaction.guild_id, interaction.user.id, log_type, entry
        )
        embed = log_embed(log_type, entry, interaction.user, log_id)
        await interaction.response.send_message(embed=embed)

    async def _view_logs(self, interaction: discord.Interaction, log_type: str, count: int):
        logs = await self.bot.db.get_logs(interaction.guild_id, log_type, min(count, 20))
        if not logs:
            meta = LOG_TYPE_META[log_type]
            await interaction.response.send_message(
                f"No {meta['label']} entries yet.", ephemeral=True
            )
            return

        meta = LOG_TYPE_META[log_type]
        embed = discord.Embed(
            title=f"{meta['emoji']} Recent {meta['label']} Entries",
            color=meta["color"],
        )
        for log in logs:
            ts    = log["created_at"][:10]
            entry = log["entry"]
            if len(entry) > 200:
                entry = entry[:197] + "..."
            embed.add_field(
                name=f"#{log['id']} — {ts} — <@{log['author_id']}>",
                value=entry,
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @buildlog_group.command(name="add", description="Add a build log entry for today")
    @app_commands.describe(entry="What did you build, fix, or test?")
    async def buildlog_add(self, interaction: discord.Interaction, entry: str):
        await self._add_log(interaction, "build", entry)

    @buildlog_group.command(name="view", description="View recent build log entries")
    @app_commands.describe(count="Number of entries to show (default 5)")
    async def buildlog_view(self, interaction: discord.Interaction, count: int = 5):
        await self._view_logs(interaction, "build", count)

    @codelog_group.command(name="add", description="Add a programming log entry")
    @app_commands.describe(entry="What did you code, fix, or test?")
    async def codelog_add(self, interaction: discord.Interaction, entry: str):
        await self._add_log(interaction, "code", entry)

    @codelog_group.command(name="view", description="View recent code log entries")
    @app_commands.describe(count="Number of entries to show (default 5)")
    async def codelog_view(self, interaction: discord.Interaction, count: int = 5):
        await self._view_logs(interaction, "code", count)

    @cadlog_group.command(name="add", description="Add a CAD log entry")
    @app_commands.describe(entry="What did you design, modify, or print?")
    async def cadlog_add(self, interaction: discord.Interaction, entry: str):
        await self._add_log(interaction, "cad", entry)

    @cadlog_group.command(name="view", description="View recent CAD log entries")
    @app_commands.describe(count="Number of entries to show (default 5)")
    async def cadlog_view(self, interaction: discord.Interaction, count: int = 5):
        await self._view_logs(interaction, "cad", count)

    # ── /notebook ─────────────────────────────────────────────────────────────

    notebook_group = app_commands.Group(name="notebook", description="Engineering notebook tools")

    @notebook_group.command(name="remind", description="Post a notebook documentation reminder")
    async def notebook_remind(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📓 Notebook Reminder",
            description=(
                "Don't forget to document your work! Good notebook entries include:\n\n"
                "• **What** you worked on\n"
                "• **Why** you made the decisions you did\n"
                "• **Results** — what worked, what didn't\n"
                "• **Next steps**\n\n"
                "Use the commands below to log your work:"
            ),
            color=0xF9A825,
        )
        embed.add_field(name="🔧 Build",  value="`/buildlog add`", inline=True)
        embed.add_field(name="💻 Code",   value="`/codelog add`",  inline=True)
        embed.add_field(name="📐 CAD",    value="`/cadlog add`",   inline=True)
        embed.set_footer(
            text="Consistent documentation = stronger Inspire Award submission 🏅"
        )
        await interaction.response.send_message(embed=embed)

    @notebook_group.command(
        name="summary", description="Show a summary of all recent log entries"
    )
    @app_commands.describe(count="Entries per category to include (default 5)")
    async def notebook_summary(self, interaction: discord.Interaction, count: int = 5):
        await interaction.response.defer(thinking=True)

        embed = discord.Embed(
            title="📓 Engineering Notebook Summary",
            color=0xF9A825,
        )

        total = 0
        for log_type, meta in LOG_TYPE_META.items():
            logs = await self.bot.db.get_logs(interaction.guild_id, log_type, count)
            if logs:
                lines = []
                for log in logs:
                    ts    = log["created_at"][:10]
                    entry = log["entry"][:80] + ("..." if len(log["entry"]) > 80 else "")
                    lines.append(f"• [{ts}] {entry}")
                embed.add_field(
                    name=f"{meta['emoji']} {meta['label']} ({len(logs)} recent)",
                    value="\n".join(lines),
                    inline=False,
                )
                total += len(logs)

        if total == 0:
            embed.description = "No log entries yet. Use `/buildlog add`, `/codelog add`, or `/cadlog add` to start."
        else:
            embed.set_footer(text=f"Showing last {count} entries per category")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(NotebookCog(bot))
