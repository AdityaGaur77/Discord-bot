"""
Permission helpers for FTC bot role-gating.
Coaches, Mentors, and Captains get admin-level access to most management commands.
"""

import discord
from discord import app_commands
from typing import Callable

# Roles that can run management/admin commands
LEADERSHIP_ROLES = {"Coach", "Mentor", "Captain", "Programming Lead", "Build Lead", "CAD Lead"}

# Roles that can run moderation commands
MOD_ROLES = {"Coach", "Mentor", "Captain"}


def is_leadership() -> Callable:
    """Slash command check: user must have a leadership role or server admin perms."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        member_roles = {r.name for r in interaction.user.roles}
        if member_roles & LEADERSHIP_ROLES:
            return True
        raise app_commands.CheckFailure(
            "🚫 This command requires a Coach, Mentor, Captain, or Lead role."
        )
    return app_commands.check(predicate)


def is_mod() -> Callable:
    """Slash command check: user must have a moderation role or server admin perms."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        member_roles = {r.name for r in interaction.user.roles}
        if member_roles & MOD_ROLES:
            return True
        raise app_commands.CheckFailure(
            "🚫 This command requires a Coach, Mentor, or Captain role."
        )
    return app_commands.check(predicate)


def is_admin() -> Callable:
    """Slash command check: must have Discord administrator permission."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        raise app_commands.CheckFailure(
            "🚫 This command requires server Administrator permission."
        )
    return app_commands.check(predicate)
