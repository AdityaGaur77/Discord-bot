import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_leadership

# Roles members can self-assign (no leadership required)
SELF_ASSIGN_ROLES = {
    "Programming Lead", "Build Lead", "CAD Lead",
    "Drive Team", "Driver", "Human Player",
    "Scouting Lead", "Scout", "Notebooker",
    "Outreach Lead", "Safety Lead", "New Member",
}

# Roles that require a leader to assign
RESTRICTED_ROLES = {"Coach", "Mentor", "Captain"}


class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    role_group = app_commands.Group(name="role", description="Manage FTC team roles")

    @role_group.command(name="join", description="Self-assign an FTC team role")
    @app_commands.describe(role_name="The role you want (e.g. Scout, Driver, Notebooker)")
    async def role_join(self, interaction: discord.Interaction, role_name: str):
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(
                f"❌ Role **{role_name}** not found. Run `/setup roles` first.",
                ephemeral=True,
            )
            return

        if role_name in RESTRICTED_ROLES:
            await interaction.response.send_message(
                f"🔒 **{role_name}** can only be assigned by a Coach or Mentor.",
                ephemeral=True,
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"You already have the **{role_name}** role.", ephemeral=True
            )
            return

        await interaction.user.add_roles(role, reason="Self-assigned via /role join")
        embed = discord.Embed(
            title="✅ Role Assigned",
            description=f"{interaction.user.mention} is now **{role_name}**!",
            color=role.color,
        )
        await interaction.response.send_message(embed=embed)

    @role_group.command(name="assign", description="[Leadership] Assign a role to another member")
    @app_commands.describe(member="The member to assign", role_name="The role to give them")
    @is_leadership()
    async def role_assign(self, interaction: discord.Interaction,
                          member: discord.Member, role_name: str):
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(
                f"❌ Role **{role_name}** not found.", ephemeral=True
            )
            return

        await member.add_roles(role, reason=f"Assigned by {interaction.user} via /role assign")
        embed = discord.Embed(
            title="✅ Role Assigned",
            description=f"{member.mention} is now **{role_name}**",
            color=role.color,
        )
        await interaction.response.send_message(embed=embed)

    @role_group.command(name="remove", description="[Leadership] Remove a role from a member")
    @app_commands.describe(member="The member", role_name="The role to remove")
    @is_leadership()
    async def role_remove(self, interaction: discord.Interaction,
                          member: discord.Member, role_name: str):
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role or role not in member.roles:
            await interaction.response.send_message(
                f"❌ **{member.display_name}** doesn't have the **{role_name}** role.",
                ephemeral=True,
            )
            return

        await member.remove_roles(role, reason=f"Removed by {interaction.user} via /role remove")
        await interaction.response.send_message(
            f"✅ Removed **{role_name}** from {member.mention}"
        )

    @role_group.command(name="list", description="List all FTC roles in this server")
    async def role_list(self, interaction: discord.Interaction):
        all_ftc = list(SELF_ASSIGN_ROLES | RESTRICTED_ROLES)
        available = [
            r.name for r in interaction.guild.roles if r.name in all_ftc
        ]
        if not available:
            await interaction.response.send_message(
                "No FTC roles found. Run `/setup roles` to create them.", ephemeral=True
            )
            return

        embed = discord.Embed(title="🎭 FTC Team Roles", color=0x1565C0)
        self_assign = [r for r in available if r in SELF_ASSIGN_ROLES]
        restricted  = [r for r in available if r in RESTRICTED_ROLES]

        if self_assign:
            embed.add_field(
                name="✅ Self-Assignable (use /role join)",
                value="\n".join(f"• {r}" for r in sorted(self_assign)),
                inline=False,
            )
        if restricted:
            embed.add_field(
                name="🔒 Leadership Only",
                value="\n".join(f"• {r}" for r in sorted(restricted)),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RolesCog(bot))
