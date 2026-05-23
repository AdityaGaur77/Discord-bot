import discord
from discord import app_commands
from discord.ext import commands
import services.ftc_client as ftc


def _season(cfg):
    return cfg.get("season", ftc.CURRENT_SEASON) if cfg else ftc.CURRENT_SEASON


class FTCApiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ftc_group = app_commands.Group(name="ftc", description="Live FTC event and team data")

    # /ftc myteam ---------------------------------------------------------

    @ftc_group.command(name="myteam", description="Quick lookup of your configured team")
    async def ftc_myteam(self, interaction: discord.Interaction):
        """Lookup the server's configured team number."""
        cfg = await self.bot.db.get_config(interaction.guild_id)
        if not cfg or not cfg.get("team_number"):
            await interaction.response.send_message(
                "No team configured. Use `/setup team <number>` first.",
                ephemeral=True,
            )
            return
        # Reuse the team lookup logic
        await self.ftc_team.callback(self, interaction, cfg["team_number"])

    # /ftc team -----------------------------------------------------------

    @ftc_group.command(name="team", description="Look up any FTC team by number")
    @app_commands.describe(team_number="FTC team number (e.g. 12345)")
    async def ftc_team(self, interaction: discord.Interaction, team_number: int):
        await interaction.response.defer(thinking=True)
        cfg = await self.bot.db.get_config(interaction.guild_id)
        season = _season(cfg)

        # Basic info always available
        team = await ftc.get_team(team_number)
        if not team:
            await interaction.followup.send(f"❌ Team **{team_number}** not found.")
            return

        embed = discord.Embed(
            title=f"🤖 Team {team.get('number')} — {team.get('name', '?')}",
            color=0x1565C0,
        )
        location_parts = [
            team.get("city"), team.get("stateProv"), team.get("country")
        ]
        embed.add_field(name="Location",    value=", ".join(p for p in location_parts if p) or "?")
        embed.add_field(name="Rookie Year", value=str(team.get("rookieYear", "?")))
        if team.get("schoolName"):
            embed.add_field(name="School", value=team["schoolName"])
        if team.get("website"):
            embed.add_field(name="Website", value=team["website"], inline=False)

        # Season stats (may 404 if team hasn't competed yet)
        stats = await ftc.get_team_quick_stats(team_number, season)
        if stats:
            # Note: quick-stats endpoint returns global season stats (tot, auto, dc, eg, opr)
            # but NOT wins/losses - those are per-event only
            for key, label in [("tot", "Avg Total"), ("auto", "Avg Auto"),
                                ("dc", "Avg TeleOp"), ("eg", "Avg Endgame")]:
                s = stats.get(key)
                if s and s.get("value") is not None:
                    rank_str = f" (rank #{s['rank']})" if s.get("rank") else ""
                    embed.add_field(name=label, value=f"{s['value']:.1f}{rank_str}")

        embed.set_footer(text="Data via ftcscout.org/rest/v1")
        await interaction.followup.send(embed=embed)

    # /ftc event ----------------------------------------------------------

    @ftc_group.command(name="event", description="Look up an FTC event by code")
    @app_commands.describe(event_code="Event code (e.g. USCANC1)")
    async def ftc_event(self, interaction: discord.Interaction, event_code: str):
        await interaction.response.defer(thinking=True)
        cfg = await self.bot.db.get_config(interaction.guild_id)

        event = await ftc.get_event(event_code, _season(cfg))
        if not event:
            await interaction.followup.send(f"❌ Event **{event_code.upper()}** not found.")
            return

        embed = discord.Embed(
            title=f"📍 {event.get('name', event_code.upper())}",
            description=f"`{event.get('code','?')}` • {event.get('typeName', event.get('type',''))}",
            color=0xFB8C00,
        )
        loc = ", ".join(
            p for p in [event.get("city"), event.get("stateProv"), event.get("country")] if p
        )
        embed.add_field(name="Location", value=loc or "?")
        embed.add_field(name="Dates",    value=f"{event.get('start','?')} → {event.get('end','?')}")
        if event.get("website"):
            embed.add_field(name="Website", value=event["website"], inline=False)
        embed.set_footer(text="Data via ftcscout.org/rest/v1")
        await interaction.followup.send(embed=embed)

    # /ftc rankings -------------------------------------------------------

    @ftc_group.command(name="rankings", description="Show current standings at an event")
    @app_commands.describe(event_code="Event code (e.g. USCANC1)")
    async def ftc_rankings(self, interaction: discord.Interaction, event_code: str):
        await interaction.response.defer(thinking=True)
        cfg = await self.bot.db.get_config(interaction.guild_id)

        rankings = await ftc.get_rankings(event_code, _season(cfg))
        if not rankings:
            await interaction.followup.send(f"❌ No rankings found for **{event_code.upper()}**.")
            return

        lines = []
        for entry in rankings[:15]:
            team  = entry.get("team") or {}
            stats = entry.get("stats") or {}
            opr   = stats.get("opr") or {}
            w, l  = stats.get("wins", 0), stats.get("losses", 0)
            opr_str = f" OPR {opr['value']:.1f}" if opr.get("value") is not None else ""
            lines.append(
                f"**#{stats.get('rank','?')}** {team.get('number','?')} {team.get('name','?')}"
                f" — {w}W/{l}L{opr_str}"
            )

        embed = discord.Embed(
            title=f"🏆 Rankings — {event_code.upper()}",
            description="\n".join(lines),
            color=0xFB8C00,
        )
        embed.set_footer(
            text=f"Top 15 of {len(rankings)} teams • ftcscout.org/rest/v1"
            if len(rankings) > 15 else "ftcscout.org/rest/v1"
        )
        await interaction.followup.send(embed=embed)

    # /ftc scores ---------------------------------------------------------

    @ftc_group.command(name="scores", description="Show recent match results at an event")
    @app_commands.describe(event_code="Event code (e.g. USCANC1)")
    async def ftc_scores(self, interaction: discord.Interaction, event_code: str):
        await interaction.response.defer(thinking=True)
        cfg = await self.bot.db.get_config(interaction.guild_id)

        matches = await ftc.get_scores(event_code, _season(cfg))
        if not matches:
            await interaction.followup.send(f"❌ No results found for **{event_code.upper()}**.")
            return

        lines = []
        for m in reversed(matches[-10:]):
            red_teams  = "/".join(str(t.get("team", {}).get("number", "?")) for t in m.get("redTeams",  []))
            blue_teams = "/".join(str(t.get("team", {}).get("number", "?")) for t in m.get("blueTeams", []))
            red_pts    = (m.get("redScore")  or {}).get("totalPoints", "?")
            blue_pts   = (m.get("blueScore") or {}).get("totalPoints", "?")
            desc = m.get("description") or f"Match {m.get('matchNum','?')}"
            lines.append(f"**{desc}** 🔴 {red_teams} **{red_pts}** — **{blue_pts}** 🔵 {blue_teams}")

        embed = discord.Embed(
            title=f"📊 Recent Results — {event_code.upper()}",
            description="\n".join(lines),
            color=0x43A047,
        )
        embed.set_footer(text=f"Last {len(lines)} of {len(matches)} played • ftcscout.org/rest/v1")
        await interaction.followup.send(embed=embed)

    # /ftc schedule -------------------------------------------------------

    @ftc_group.command(name="schedule", description="Show upcoming matches at an event")
    @app_commands.describe(event_code="Event code (e.g. USCANC1)")
    async def ftc_schedule(self, interaction: discord.Interaction, event_code: str):
        await interaction.response.defer(thinking=True)
        cfg = await self.bot.db.get_config(interaction.guild_id)

        matches = await ftc.get_schedule(event_code, _season(cfg))
        if not matches:
            await interaction.followup.send(
                f"❌ No upcoming matches for **{event_code.upper()}** — "
                "event may not have started yet, or all matches are complete."
            )
            return

        lines = []
        for m in matches[:10]:
            red_teams  = "/".join(str(t.get("team", {}).get("number", "?")) for t in m.get("redTeams",  []))
            blue_teams = "/".join(str(t.get("team", {}).get("number", "?")) for t in m.get("blueTeams", []))
            desc = m.get("description") or f"Match {m.get('matchNum','?')}"
            lines.append(f"**{desc}** 🔴 {red_teams} vs 🔵 {blue_teams}")

        embed = discord.Embed(
            title=f"📅 Upcoming Matches — {event_code.upper()}",
            description="\n".join(lines),
            color=0x1565C0,
        )
        embed.set_footer(text=f"Next {len(lines)} matches • ftcscout.org/rest/v1")
        await interaction.followup.send(embed=embed)

    # /ftc awards ---------------------------------------------------------

    @ftc_group.command(name="awards", description="Show awards given at an event")
    @app_commands.describe(event_code="Event code (e.g. USCANC1)")
    async def ftc_awards(self, interaction: discord.Interaction, event_code: str):
        await interaction.response.defer(thinking=True)
        cfg = await self.bot.db.get_config(interaction.guild_id)

        awards = await ftc.get_event_awards(event_code, _season(cfg))
        if awards is None:
            await interaction.followup.send(f"❌ Event **{event_code.upper()}** not found.")
            return
        if not awards:
            await interaction.followup.send(f"No awards posted yet for **{event_code.upper()}**.")
            return

        lines = []
        for a in awards:
            name   = a.get("name") or a.get("award", {}).get("name", "Unknown Award")
            team   = a.get("team") or {}
            person = a.get("person", "")
            recipient = f"Team **{team.get('number')}** {team.get('name','')}" if team.get("number") else ""
            if person:
                recipient += f" ({person})"
            lines.append(f"🏅 **{name}** — {recipient or '?'}")

        embed = discord.Embed(
            title=f"🏅 Awards — {event_code.upper()}",
            description="\n".join(lines),
            color=0xFB8C00,
        )
        embed.set_footer(text="Data via ftcscout.org/rest/v1")
        await interaction.followup.send(embed=embed)

    # /ftc teams ----------------------------------------------------------

    @ftc_group.command(name="teams", description="List all teams at an event")
    @app_commands.describe(event_code="Event code (e.g. USCANC1)")
    async def ftc_teams(self, interaction: discord.Interaction, event_code: str):
        await interaction.response.defer(thinking=True)
        cfg = await self.bot.db.get_config(interaction.guild_id)

        entries = await ftc.get_event_teams(event_code, _season(cfg))
        if not entries:
            await interaction.followup.send(f"❌ No team data for **{event_code.upper()}**.")
            return

        lines = []
        for e in entries:
            t = e.get("team") or {}
            city = t.get("city", "")
            lines.append(f"**{t.get('number','?')}** — {t.get('name','?')}{f' *({city})*' if city else ''}")

        embed = discord.Embed(
            title=f"👥 Teams at {event_code.upper()} ({len(entries)} total)",
            description="\n".join(lines[:25]),
            color=0x1565C0,
        )
        if len(lines) > 25:
            embed.set_footer(text=f"Showing 25 of {len(lines)} teams")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(FTCApiCog(bot))
