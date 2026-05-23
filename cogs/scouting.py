import discord
from discord import app_commands
from discord.ext import commands
import io
import csv


class ScoutingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    scout_group = app_commands.Group(name="scout", description="Match and pit scouting tools")

    @scout_group.command(name="add", description="Submit a match scouting report")
    @app_commands.describe(
        team_number="Team number you're scouting",
        auto="Autonomous score",
        teleop="TeleOp (driver-controlled) score",
        endgame="Endgame score",
        event="Event code (optional, e.g. USCANC1)",
        notes="Any notes on this team's performance",
    )
    async def scout_add(
        self,
        interaction: discord.Interaction,
        team_number: int,
        auto: int = 0,
        teleop: int = 0,
        endgame: int = 0,
        event: str = None,
        notes: str = "",
    ):
        event_code = event.upper() if event else None

        scout_id = await self.bot.db.add_scout(
            interaction.guild_id, team_number, event_code,
            interaction.user.id, auto, teleop, endgame, notes,
        )

        total = auto + teleop + endgame
        embed = discord.Embed(
            title=f"📊 Scout Report #{scout_id} — Team {team_number}",
            color=0x43A047,
        )
        embed.add_field(name="Auto",       value=str(auto))
        embed.add_field(name="TeleOp",     value=str(teleop))
        embed.add_field(name="Endgame",    value=str(endgame))
        embed.add_field(name="Total",      value=f"**{total}**")
        if event_code:
            embed.add_field(name="Event",  value=event_code)
        if notes:
            embed.add_field(name="Notes",  value=notes, inline=False)
        embed.set_footer(text=f"Scouted by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

        # Also post to scouting channel if configured
        cfg = await self.bot.db.get_config(interaction.guild_id)
        if cfg and cfg.get("scouting_channel") and cfg["scouting_channel"] != interaction.channel_id:
            ch = interaction.guild.get_channel(cfg["scouting_channel"])
            if ch:
                await ch.send(embed=embed)

    @scout_group.command(name="report", description="View all scouting data for a team")
    @app_commands.describe(team_number="The team number to look up")
    async def scout_report(self, interaction: discord.Interaction, team_number: int):
        reports = await self.bot.db.get_scout_reports(interaction.guild_id, team_number)

        if not reports:
            await interaction.response.send_message(
                f"No scouting data for team **{team_number}** yet.", ephemeral=True
            )
            return

        # Calculate averages
        avg_auto    = sum(r["auto_score"]    for r in reports) / len(reports)
        avg_teleop  = sum(r["teleop_score"]  for r in reports) / len(reports)
        avg_endgame = sum(r["endgame_score"] for r in reports) / len(reports)
        avg_total   = avg_auto + avg_teleop + avg_endgame
        max_total   = max(r["auto_score"] + r["teleop_score"] + r["endgame_score"] for r in reports)

        embed = discord.Embed(
            title=f"📊 Scouting Report — Team {team_number}",
            color=0x43A047,
        )
        embed.add_field(name="Reports",      value=str(len(reports)))
        embed.add_field(name="Avg Total",    value=f"{avg_total:.1f}")
        embed.add_field(name="Best Total",   value=str(max_total))
        embed.add_field(name="Avg Auto",     value=f"{avg_auto:.1f}")
        embed.add_field(name="Avg TeleOp",   value=f"{avg_teleop:.1f}")
        embed.add_field(name="Avg Endgame",  value=f"{avg_endgame:.1f}")

        # Show latest 3 notes
        notes_with_text = [r for r in reports if r.get("notes")][:3]
        if notes_with_text:
            notes_str = "\n".join(
                f"• [{r['created_at'][:10]}] {r['notes']}" for r in notes_with_text
            )
            embed.add_field(name="Recent Notes", value=notes_str, inline=False)

        await interaction.response.send_message(embed=embed)

    @scout_group.command(name="export", description="Export all scouting data as a CSV file")
    @app_commands.describe(event="Filter by event code (optional)")
    async def scout_export(self, interaction: discord.Interaction, event: str = None):
        await interaction.response.defer(thinking=True)
        event_code = event.upper() if event else None
        reports = await self.bot.db.get_all_scouts(interaction.guild_id, event_code)

        if not reports:
            await interaction.followup.send("No scouting data to export.", ephemeral=True)
            return

        # Build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Team Number", "Event", "Scout", "Auto", "TeleOp",
            "Endgame", "Total", "Notes", "Date"
        ])
        for r in reports:
            total = r["auto_score"] + r["teleop_score"] + r["endgame_score"]
            writer.writerow([
                r["team_number"],
                r.get("event_code") or "",
                r["scout_id"],
                r["auto_score"],
                r["teleop_score"],
                r["endgame_score"],
                total,
                r.get("notes") or "",
                r["created_at"][:10],
            ])

        output.seek(0)
        filename = f"scouting_{event_code or 'all'}.csv"
        await interaction.followup.send(
            f"📊 Exported **{len(reports)}** scouting records:",
            file=discord.File(fp=io.BytesIO(output.getvalue().encode()), filename=filename),
        )

    @scout_group.command(name="compare", description="Compare two teams' scouting averages")
    @app_commands.describe(team_a="First team number", team_b="Second team number")
    async def scout_compare(
        self, interaction: discord.Interaction, team_a: int, team_b: int
    ):
        reports_a = await self.bot.db.get_scout_reports(interaction.guild_id, team_a)
        reports_b = await self.bot.db.get_scout_reports(interaction.guild_id, team_b)

        def avg_stats(reports):
            if not reports:
                return None
            n = len(reports)
            return {
                "auto":    sum(r["auto_score"]    for r in reports) / n,
                "teleop":  sum(r["teleop_score"]  for r in reports) / n,
                "endgame": sum(r["endgame_score"] for r in reports) / n,
                "total":   sum(r["auto_score"] + r["teleop_score"] + r["endgame_score"] for r in reports) / n,
                "count":   n,
            }

        a = avg_stats(reports_a)
        b = avg_stats(reports_b)

        embed = discord.Embed(
            title=f"Team Comparison: {team_a} vs {team_b}",
            color=0x1565C0,
        )

        def stat_row(label: str, key: str):
            va = f"{a[key]:.1f}" if a else "no data"
            vb = f"{b[key]:.1f}" if b else "no data"
            winner = ""
            if a and b:
                winner = f"  <- {team_a}" if a[key] > b[key] else (f"  <- {team_b}" if b[key] > a[key] else "  tie")
            embed.add_field(name=label, value=f"{team_a}: **{va}**\n{team_b}: **{vb}**{winner}")

        stat_row("Total Score Avg",   "total")
        stat_row("Auto Avg",          "auto")
        stat_row("TeleOp Avg",        "teleop")
        stat_row("Endgame Avg",       "endgame")

        reports_label = (
            f"Based on {a['count'] if a else 0} / {b['count'] if b else 0} reports"
        )
        embed.set_footer(text=reports_label)
        await interaction.response.send_message(embed=embed)

    # ── Pit Scouting ──────────────────────────────────────────────────────────

    pit_group = app_commands.Group(name="pit", description="Pit scouting tools")

    @pit_group.command(name="add", description="Submit a pit scouting report")
    @app_commands.describe(
        team_number="Team number",
        event="Event code (e.g. USPALVC)",
        drivetrain="Drivetrain type (mecanum, tank, swerve, etc.)",
        max_height="Maximum scoring height capability",
        auto_capable="Autonomous capabilities description",
        cycle_time="Approximate cycle time",
        strengths="Team strengths",
        weaknesses="Team weaknesses",
        notes="Additional notes",
    )
    @app_commands.choices(drivetrain=[
        app_commands.Choice(name="Mecanum", value="mecanum"),
        app_commands.Choice(name="Tank/Differential", value="tank"),
        app_commands.Choice(name="Swerve", value="swerve"),
        app_commands.Choice(name="Omni", value="omni"),
        app_commands.Choice(name="Other", value="other"),
    ])
    async def pit_add(
        self,
        interaction: discord.Interaction,
        team_number: int,
        event: str,
        drivetrain: str = None,
        max_height: str = None,
        auto_capable: str = None,
        cycle_time: str = None,
        strengths: str = None,
        weaknesses: str = None,
        notes: str = "",
    ):
        pit_id = await self.bot.db.add_pit_scout(
            interaction.guild_id, team_number, event, interaction.user.id,
            drivetrain, max_height, auto_capable, cycle_time,
            strengths, weaknesses, notes,
        )

        embed = discord.Embed(
            title=f"Pit Scout Report - Team {team_number}",
            description=f"Event: **{event.upper()}**",
            color=0x8E24AA,
        )
        if drivetrain:
            embed.add_field(name="Drivetrain", value=drivetrain.capitalize())
        if max_height:
            embed.add_field(name="Max Height", value=max_height)
        if auto_capable:
            embed.add_field(name="Auto Capabilities", value=auto_capable, inline=False)
        if cycle_time:
            embed.add_field(name="Cycle Time", value=cycle_time)
        if strengths:
            embed.add_field(name="Strengths", value=strengths, inline=False)
        if weaknesses:
            embed.add_field(name="Weaknesses", value=weaknesses, inline=False)
        if notes:
            embed.add_field(name="Notes", value=notes, inline=False)
        embed.set_footer(text=f"Scouted by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    @pit_group.command(name="view", description="View pit scouting data for a team")
    @app_commands.describe(
        team_number="Team number to look up",
        event="Event code (optional)",
    )
    async def pit_view(
        self, interaction: discord.Interaction, team_number: int, event: str = None
    ):
        data = await self.bot.db.get_pit_scout(
            interaction.guild_id, team_number, event
        )

        if not data:
            await interaction.response.send_message(
                f"No pit scouting data for team **{team_number}**"
                + (f" at **{event.upper()}**" if event else ""),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"Pit Scout Data - Team {team_number}",
            description=f"Event: **{data.get('event_code', 'N/A')}**",
            color=0x8E24AA,
        )
        if data.get("drivetrain"):
            embed.add_field(name="Drivetrain", value=data["drivetrain"].capitalize())
        if data.get("max_height"):
            embed.add_field(name="Max Height", value=data["max_height"])
        if data.get("auto_capable"):
            embed.add_field(name="Auto Capabilities", value=data["auto_capable"], inline=False)
        if data.get("cycle_time"):
            embed.add_field(name="Cycle Time", value=data["cycle_time"])
        if data.get("strengths"):
            embed.add_field(name="Strengths", value=data["strengths"], inline=False)
        if data.get("weaknesses"):
            embed.add_field(name="Weaknesses", value=data["weaknesses"], inline=False)
        if data.get("notes"):
            embed.add_field(name="Notes", value=data["notes"], inline=False)
        embed.set_footer(text=f"Scouted by user {data.get('scout_id', 'unknown')}")

        await interaction.response.send_message(embed=embed)

    @pit_group.command(name="list", description="List all pit scouted teams at an event")
    @app_commands.describe(event="Event code")
    async def pit_list(self, interaction: discord.Interaction, event: str):
        data = await self.bot.db.get_all_pit_scouts(interaction.guild_id, event)

        if not data:
            await interaction.response.send_message(
                f"No pit scouting data for **{event.upper()}**.", ephemeral=True
            )
            return

        lines = []
        for d in data:
            drivetrain = d.get("drivetrain", "?")
            lines.append(f"**{d['team_number']}** - {drivetrain}")

        embed = discord.Embed(
            title=f"Pit Scouted Teams at {event.upper()}",
            description="\n".join(lines[:25]),
            color=0x8E24AA,
        )
        if len(lines) > 25:
            embed.set_footer(text=f"Showing 25 of {len(lines)} teams")
        else:
            embed.set_footer(text=f"{len(lines)} team(s) scouted")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ScoutingCog(bot))
