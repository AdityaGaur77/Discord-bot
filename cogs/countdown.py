import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import services.ftc_client as ftc
from services.permissions import is_leadership


class CountdownCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    countdown_group = app_commands.Group(name="countdown", description="Competition countdown tracking")

    @countdown_group.command(name="set", description="Set a countdown to a competition")
    @app_commands.describe(
        event_code="Event code (e.g. USCANC1)",
        date="Event date in YYYY-MM-DD format (optional if event found)",
    )
    @is_leadership()
    async def countdown_set(
        self, interaction: discord.Interaction, event_code: str, date: str = None
    ):
        """Set a countdown to track days until competition."""
        await interaction.response.defer(thinking=True)
        
        cfg = await self.bot.db.get_config(interaction.guild_id)
        season = cfg.get("season", ftc.CURRENT_SEASON) if cfg else ftc.CURRENT_SEASON
        
        # Try to fetch event info from FTC Scout
        event = await ftc.get_event(event_code, season)
        event_name = event.get("name", event_code.upper()) if event else event_code.upper()
        
        # Use provided date or try to get from event
        event_date = date
        if not event_date and event:
            event_date = event.get("start")
        
        if not event_date:
            await interaction.followup.send(
                f"Could not find event **{event_code.upper()}**. "
                "Please provide the date manually: `/countdown set {event_code} date:YYYY-MM-DD`",
                ephemeral=True,
            )
            return
        
        await self.bot.db.set_countdown(
            interaction.guild_id,
            event_code,
            event_name,
            event_date,
            interaction.channel_id,
        )
        
        # Calculate days until event
        try:
            event_dt  = datetime.strptime(event_date[:10], "%Y-%m-%d")
            days_until = (event_dt - datetime.now()).days
            days_str   = f"**{days_until}** days" if days_until > 0 else ("**Today!**" if days_until == 0 else "Already passed")
        except ValueError:
            await interaction.followup.send(
                f"Invalid date format `{event_date}`. Expected YYYY-MM-DD (e.g. 2025-03-15).",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title="Countdown Set",
            description=f"**{event_name}**\n`{event_code.upper()}`",
            color=0xFB8C00,
        )
        embed.add_field(name="Date", value=event_date[:10])
        embed.add_field(name="Days Until", value=days_str)
        embed.set_footer(text="Use /countdown view to check progress")
        await interaction.followup.send(embed=embed)

    @countdown_group.command(name="view", description="View all competition countdowns")
    async def countdown_view(self, interaction: discord.Interaction):
        """View all active countdowns."""
        countdowns = await self.bot.db.get_countdowns(interaction.guild_id)
        
        if not countdowns:
            await interaction.response.send_message(
                "No countdowns set. Use `/countdown set <event_code>` to add one.",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title="Competition Countdowns",
            color=0xFB8C00,
        )
        
        for c in countdowns:
            try:
                event_dt   = datetime.strptime(c["event_date"][:10], "%Y-%m-%d")
                days_until = (event_dt - datetime.now()).days
                if days_until > 0:
                    status = f"**{days_until}** days away"
                elif days_until == 0:
                    status = "**TODAY!**"
                else:
                    status = f"{abs(days_until)} days ago"
            except ValueError:
                status = f"Invalid date: `{c.get('event_date', '?')}`"
            
            embed.add_field(
                name=f"{c['event_name']}",
                value=f"`{c['event_code']}` - {c['event_date'][:10]}\n{status}",
                inline=False,
            )
        
        embed.set_footer(text=f"{len(countdowns)} countdown(s) tracked")
        await interaction.response.send_message(embed=embed)

    @countdown_group.command(name="remove", description="Remove a countdown")
    @app_commands.describe(event_code="Event code to remove")
    @is_leadership()
    async def countdown_remove(self, interaction: discord.Interaction, event_code: str):
        """Remove a countdown."""
        success = await self.bot.db.remove_countdown(interaction.guild_id, event_code)
        if success:
            await interaction.response.send_message(
                f"Removed countdown for **{event_code.upper()}**."
            )
        else:
            await interaction.response.send_message(
                f"No countdown found for **{event_code.upper()}**.",
                ephemeral=True,
            )

    @countdown_group.command(name="next", description="Show countdown to your next competition")
    async def countdown_next(self, interaction: discord.Interaction):
        """Quick view of the nearest upcoming competition."""
        countdowns = await self.bot.db.get_countdowns(interaction.guild_id)
        
        if not countdowns:
            await interaction.response.send_message(
                "No countdowns set. Use `/countdown set <event_code>` to add one.",
                ephemeral=True,
            )
            return
        
        # Find the next upcoming event
        upcoming = []
        for c in countdowns:
            try:
                event_dt = datetime.strptime(c["event_date"][:10], "%Y-%m-%d")
                days_until = (event_dt - datetime.now()).days
                if days_until >= 0:
                    upcoming.append((days_until, c))
            except ValueError:
                pass
        
        if not upcoming:
            await interaction.response.send_message(
                "All tracked competitions have passed. Add a new one with `/countdown set`.",
                ephemeral=True,
            )
            return
        
        upcoming.sort(key=lambda x: x[0])
        days, event = upcoming[0]
        
        if days == 0:
            message = f"**{event['event_name']}** is **TODAY!**"
            color = 0xE53935  # Red for urgency
        elif days <= 7:
            message = f"**{days}** days until **{event['event_name']}**"
            color = 0xFB8C00  # Orange
        else:
            message = f"**{days}** days until **{event['event_name']}**"
            color = 0x43A047  # Green
        
        embed = discord.Embed(
            title="Next Competition",
            description=message,
            color=color,
        )
        embed.add_field(name="Event Code", value=f"`{event['event_code']}`")
        embed.add_field(name="Date", value=event["event_date"][:10])
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(CountdownCog(bot))
