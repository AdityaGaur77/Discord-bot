import datetime
import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_leadership


def _today_session_id() -> int:
    """Generate a pseudo-session ID from today's date (YYYYMMDD as int)."""
    return int(datetime.date.today().strftime("%Y%m%d"))


class AttendanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    attendance_group = app_commands.Group(name="attendance", description="Track practice attendance")

    @attendance_group.command(name="checkin", description="Check in to today's practice session")
    async def attendance_checkin(self, interaction: discord.Interaction):
        session_id = _today_session_id()
        success = await self.bot.db.check_in(interaction.guild_id, interaction.user.id, session_id)
        if success:
            await interaction.response.send_message(
                f"✅ Checked in to today's practice ({datetime.date.today()})!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "You're already checked in for today.", ephemeral=True
            )

    @attendance_group.command(name="list", description="See who's checked in today")
    async def attendance_list(self, interaction: discord.Interaction):
        session_id = _today_session_id()
        records    = await self.bot.db.get_attendance_for_meeting(interaction.guild_id, session_id)

        if not records:
            await interaction.response.send_message(
                "No one has checked in today yet. Use `/attendance checkin`.",
                ephemeral=True,
            )
            return

        lines = [f"<@{r['user_id']}>" for r in records]
        embed = discord.Embed(
            title=f"Today's Attendance — {datetime.date.today()}",
            description="\n".join(lines),
            color=0x43A047,
        )
        embed.set_footer(text=f"{len(records)} member(s) present")
        await interaction.response.send_message(embed=embed)

    @attendance_group.command(name="report", description="View attendance statistics (leadership only)")
    @is_leadership()
    async def attendance_report(self, interaction: discord.Interaction):
        stats = await self.bot.db.get_attendance_stats(interaction.guild_id, limit=20)

        if not stats:
            await interaction.response.send_message(
                "No attendance data yet. Members can use `/attendance checkin` during practice.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="Attendance Report", color=0x1565C0)
        lines = [
            f"**{i}.** <@{s['user_id']}> — {s['count']} session(s)"
            for i, s in enumerate(stats[:15], 1)
        ]
        embed.add_field(name="Most Sessions Attended", value="\n".join(lines), inline=False)
        embed.set_footer(text="Use /attendance checkin at each practice to track attendance")
        await interaction.response.send_message(embed=embed)

    @attendance_group.command(name="add", description="[Leadership] Manually add someone to today's attendance")
    @app_commands.describe(member="Member to mark as present")
    @is_leadership()
    async def attendance_add(self, interaction: discord.Interaction, member: discord.Member):
        session_id = _today_session_id()
        success    = await self.bot.db.check_in(interaction.guild_id, member.id, session_id)
        if success:
            await interaction.response.send_message(
                f"Added {member.mention} to today's attendance."
            )
        else:
            await interaction.response.send_message(
                f"{member.mention} is already checked in today.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AttendanceCog(bot))
