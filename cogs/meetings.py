import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_leadership


class MeetingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    meeting_group = app_commands.Group(name="meeting", description="Log and track team meetings")

    @meeting_group.command(name="start", description="Start logging a meeting")
    async def meeting_start(self, interaction: discord.Interaction):
        # Check if there's already an active meeting
        active = await self.bot.db.get_active_meeting(interaction.guild_id)
        if active:
            await interaction.response.send_message(
                f"⚠️ There's already an active meeting (started by <@{active['started_by']}>). "
                "End it first with `/meeting end`.",
                ephemeral=True,
            )
            return

        meeting_id = await self.bot.db.start_meeting(
            interaction.guild_id, interaction.user.id
        )
        embed = discord.Embed(
            title="📋 Meeting Started",
            description=(
                f"Meeting **#{meeting_id}** is now open.\n\n"
                "Use `/meeting end` with meeting notes when you're done.\n"
                "Use `/buildlog add`, `/codelog add`, or `/cadlog add` to log work during the meeting."
            ),
            color=0x43A047,
        )
        embed.set_footer(text=f"Started by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @meeting_group.command(name="end", description="End the current meeting and log notes")
    @app_commands.describe(notes="Summary of what was accomplished this meeting")
    async def meeting_end(self, interaction: discord.Interaction, notes: str = ""):
        active = await self.bot.db.get_active_meeting(interaction.guild_id)
        if not active:
            await interaction.response.send_message(
                "❌ No active meeting. Start one with `/meeting start`.", ephemeral=True
            )
            return

        await self.bot.db.end_meeting(active["id"], notes)

        # Calculate duration
        import datetime
        start = datetime.datetime.fromisoformat(active["started_at"])
        end   = datetime.datetime.utcnow()
        delta = end - start
        mins  = int(delta.total_seconds() // 60)

        embed = discord.Embed(
            title="✅ Meeting Ended",
            description=notes or "*(no notes recorded)*",
            color=0xFB8C00,
        )
        embed.add_field(name="Duration", value=f"{mins} minutes")
        embed.add_field(name="Meeting #", value=str(active["id"]))
        embed.set_footer(text=f"Ended by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @meeting_group.command(name="summary", description="View recent meeting summaries")
    @app_commands.describe(count="How many recent meetings to show (default 5)")
    async def meeting_summary(self, interaction: discord.Interaction, count: int = 5):
        meetings = await self.bot.db.get_recent_meetings(interaction.guild_id, min(count, 10))

        if not meetings:
            await interaction.response.send_message(
                "No completed meetings yet.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📋 Recent Meetings ({len(meetings)})",
            color=0x1565C0,
        )
        for m in meetings:
            notes = m.get("notes") or "*(no notes)*"
            if len(notes) > 200:
                notes = notes[:197] + "..."
            embed.add_field(
                name=f"Meeting #{m['id']} — {m['started_at'][:10]}",
                value=notes,
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(MeetingsCog(bot))
