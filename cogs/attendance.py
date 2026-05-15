import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_leadership


class AttendanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    attendance_group = app_commands.Group(name="attendance", description="Track meeting attendance")

    @attendance_group.command(name="checkin", description="Check in to the current meeting")
    async def attendance_checkin(self, interaction: discord.Interaction):
        """Allow members to check in to the current active meeting."""
        meeting = await self.bot.db.get_active_meeting(interaction.guild_id)
        if not meeting:
            await interaction.response.send_message(
                "No active meeting. Ask a leader to start one with `/meeting start`.",
                ephemeral=True,
            )
            return

        success = await self.bot.db.check_in(
            interaction.guild_id, interaction.user.id, meeting["id"]
        )
        if success:
            await interaction.response.send_message(
                f"Checked in to meeting #{meeting['id']}!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "You're already checked in to this meeting.",
                ephemeral=True,
            )

    @attendance_group.command(name="list", description="View who's checked in to the current meeting")
    async def attendance_list(self, interaction: discord.Interaction):
        """Show attendance for the current meeting."""
        meeting = await self.bot.db.get_active_meeting(interaction.guild_id)
        if not meeting:
            await interaction.response.send_message(
                "No active meeting right now.",
                ephemeral=True,
            )
            return

        records = await self.bot.db.get_attendance_for_meeting(
            interaction.guild_id, meeting["id"]
        )
        if not records:
            await interaction.response.send_message(
                f"No one has checked in to meeting #{meeting['id']} yet.\n"
                "Members can use `/attendance checkin` to check in.",
                ephemeral=True,
            )
            return

        lines = [f"<@{r['user_id']}>" for r in records]
        embed = discord.Embed(
            title=f"Attendance - Meeting #{meeting['id']}",
            description="\n".join(lines),
            color=0x43A047,
        )
        embed.set_footer(text=f"{len(records)} member(s) checked in")
        await interaction.response.send_message(embed=embed)

    @attendance_group.command(name="report", description="View attendance statistics")
    @is_leadership()
    async def attendance_report(self, interaction: discord.Interaction):
        """Show attendance stats across all meetings."""
        stats = await self.bot.db.get_attendance_stats(interaction.guild_id, limit=20)
        total_meetings = await self.bot.db.get_total_meetings_count(interaction.guild_id)

        if not stats:
            await interaction.response.send_message(
                "No attendance data yet. Start tracking with `/meeting start` "
                "and have members use `/attendance checkin`.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Attendance Report",
            description=f"Based on **{total_meetings}** completed meetings",
            color=0x1565C0,
        )

        lines = []
        for i, s in enumerate(stats[:15], 1):
            pct = (s["count"] / total_meetings * 100) if total_meetings > 0 else 0
            lines.append(f"**{i}.** <@{s['user_id']}> — {s['count']} meetings ({pct:.0f}%)")

        embed.add_field(
            name="Top Attendance",
            value="\n".join(lines) if lines else "No data",
            inline=False,
        )
        embed.set_footer(text="Use /attendance checkin during meetings to track")
        await interaction.response.send_message(embed=embed)

    @attendance_group.command(name="add", description="[Leadership] Manually add someone's attendance")
    @app_commands.describe(member="Member to mark as present")
    @is_leadership()
    async def attendance_add(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        """Manually add attendance for a member."""
        meeting = await self.bot.db.get_active_meeting(interaction.guild_id)
        if not meeting:
            await interaction.response.send_message(
                "No active meeting. Start one with `/meeting start` first.",
                ephemeral=True,
            )
            return

        success = await self.bot.db.check_in(
            interaction.guild_id, member.id, meeting["id"]
        )
        if success:
            await interaction.response.send_message(
                f"Added {member.mention} to meeting #{meeting['id']} attendance."
            )
        else:
            await interaction.response.send_message(
                f"{member.mention} is already checked in.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(AttendanceCog(bot))
