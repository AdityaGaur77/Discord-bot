import discord
from discord import app_commands
from discord.ext import commands


class ScoutingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    scout_group = app_commands.Group(name="scout", description="Match scouting tools")

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
                winner = (
                    f"  ← {team_a}" if a[key] > b[key]
                    else (f"  ← {team_b}" if b[key] > a[key] else "  tie")
                )
            embed.add_field(name=label, value=f"{team_a}: **{va}**\n{team_b}: **{vb}**{winner}")

        stat_row("Total Score Avg", "total")
        stat_row("Auto Avg",        "auto")
        stat_row("TeleOp Avg",      "teleop")
        stat_row("Endgame Avg",     "endgame")

        embed.set_footer(
            text=f"Based on {a['count'] if a else 0} / {b['count'] if b else 0} reports"
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ScoutingCog(bot))
