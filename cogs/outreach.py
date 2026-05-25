import discord
from discord import app_commands
from discord.ext import commands
import datetime
from typing import Optional


class OutreachCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    outreach_group = app_commands.Group(name="outreach", description="Track outreach and community events")

    @outreach_group.command(name="add", description="Log an outreach event")
    @app_commands.describe(
        event="Name of the outreach event",
        hours="Total volunteer hours",
        students="Number of students/people reached",
        date="Date of the event (e.g. 2026-01-15)",
        notes="Any notes or highlights",
    )
    async def outreach_add(
        self,
        interaction: discord.Interaction,
        event: str,
        hours: float = 0,
        students: Optional[int] = None,
        date: str = None,
        notes: str = "",
    ):
        if not date:
            date = datetime.date.today().isoformat()
        students_val = students if students is not None else 0

        entry_id = await self.bot.db.add_outreach(
            interaction.guild_id, event, hours, students_val, date, notes
        )

        embed = discord.Embed(
            title=f"🌍 Outreach Event Logged — #{entry_id}",
            description=f"**{event}**",
            color=0xFFB300,
        )
        embed.add_field(name="Date",             value=date)
        embed.add_field(name="Volunteer Hours",  value=str(hours))
        embed.add_field(name="People Reached",   value=str(students_val))
        if notes:
            embed.add_field(name="Notes", value=notes, inline=False)
        embed.set_footer(text=f"Logged by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @outreach_group.command(name="summary", description="View outreach stats for the season")
    async def outreach_summary(self, interaction: discord.Interaction):
        events = await self.bot.db.get_outreach(interaction.guild_id)

        if not events:
            await interaction.response.send_message(
                "No outreach events logged yet. Use `/outreach add` to start!", ephemeral=True
            )
            return

        total_hours    = sum(e["hours"]    for e in events)
        total_students = sum(e["students"] for e in events)

        embed = discord.Embed(
            title="🌍 Outreach Season Summary",
            color=0xFFB300,
        )
        embed.add_field(name="Events",           value=str(len(events)))
        embed.add_field(name="Total Hours",      value=f"{total_hours:.1f}")
        embed.add_field(name="People Reached",   value=str(total_students))

        # Recent events
        recent = events[:8]
        lines = []
        for e in recent:
            lines.append(
                f"• **{e['event_name']}** [{e['date']}] "
                f"— {e['hours']}h, {e['students']} people"
            )
        if lines:
            embed.add_field(
                name=f"Recent Events (last {len(recent)})",
                value="\n".join(lines),
                inline=False,
            )

        # FTC award context
        embed.add_field(
            name="💡 Award Tip",
            value=(
                "Strong outreach documentation helps with the "
                "**Connect Award** and **Inspire Award**. "
                "Make sure to note student impact and STEM connections!"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(OutreachCog(bot))
