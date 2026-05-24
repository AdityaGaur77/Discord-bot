import re
import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_mod

# Built-in profanity list — always active regardless of custom filter settings.
# Uses word-boundary matching to avoid false positives (e.g. "class" won't match "ass").
BUILTIN_PROFANITY: frozenset[str] = frozenset({
    "fuck", "fucker", "fuckers", "fucking", "fucked", "fucks", "motherfucker", "motherfucking",
    "shit", "shitting", "shitty", "shits", "bullshit",
    "bitch", "bitches", "bitchy", "bitching",
    "ass", "asshole", "assholes", "jackass",
    "cunt", "cunts",
    "dick", "dicks",
    "cock", "cocks",
    "piss", "pissed",
    "bastard", "bastards",
    "slut", "sluts",
    "whore", "whores",
    "nigger", "niggers", "nigga", "niggas",
    "faggot", "faggots",
    "retard", "retarded",
    "damn", "damnit",
})

_PATTERN_CACHE: dict[str, re.Pattern] = {}


def _build_pattern(word: str) -> re.Pattern:
    if word not in _PATTERN_CACHE:
        _PATTERN_CACHE[word] = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    return _PATTERN_CACHE[word]


def _find_violation(text: str, words: list[str]) -> str | None:
    """Return the first matched word (built-in or custom), or None."""
    lower = text.lower()
    for word in BUILTIN_PROFANITY:
        if _build_pattern(word).search(lower):
            return word
    for word in words:
        if _build_pattern(word).search(lower):
            return word
    return None


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._filter_cache: dict[int, list[str]] = {}

    async def _get_filter(self, guild_id: int) -> list[str]:
        if guild_id not in self._filter_cache:
            self._filter_cache[guild_id] = await self.bot.db.get_word_filter(guild_id)
        return self._filter_cache[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        # Admins and leadership are exempt
        member_roles = {r.name for r in message.author.roles}
        if member_roles & {"Coach", "Mentor", "Captain"} or message.author.guild_permissions.administrator:
            return

        custom_words = await self._get_filter(message.guild.id)
        matched = _find_violation(message.content, custom_words)
        if not matched:
            return

        # Delete the message silently
        try:
            await message.delete()
        except discord.Forbidden:
            return  # No permission to delete — skip everything

        # Warn the sender via DM only (private, not visible to the whole channel)
        try:
            dm_embed = discord.Embed(
                title="⚠️ Message Removed",
                description=(
                    f"Your message in **{message.guild.name}** was removed because it contained "
                    "language that isn't allowed in this server.\n\n"
                    "Please keep the conversation respectful."
                ),
                color=0xFB8C00,
            )
            await message.author.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # DMs disabled — message is still deleted, just no notification

        # Log to mod channel if configured (mod-only, not public)
        cfg = await self.bot.db.get_config(message.guild.id)
        if cfg and cfg.get("modlog_channel"):
            ch = message.guild.get_channel(cfg["modlog_channel"])
            if ch:
                log_embed = discord.Embed(title="🚨 Word Filter Triggered", color=0xE53935)
                log_embed.add_field(name="User",    value=f"{message.author} ({message.author.id})")
                log_embed.add_field(name="Channel", value=message.channel.mention)
                log_embed.add_field(name="Word",    value=f"||{matched}||")
                await ch.send(embed=log_embed)

    # ── /mod ──────────────────────────────────────────────────────────────────

    mod_group = app_commands.Group(name="mod", description="Moderation tools")

    @mod_group.command(name="warn", description="[Mod] Issue a warning to a member")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    @is_mod()
    async def mod_warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        warn_id = await self.bot.db.add_warning(
            interaction.guild_id, member.id, reason, interaction.user.id
        )

        embed = discord.Embed(
            title=f"⚠️ Warning Issued — #{warn_id}",
            description=f"{member.mention} has received a warning.",
            color=0xFB8C00,
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Issued by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

        try:
            dm_embed = discord.Embed(
                title="⚠️ You received a warning",
                description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason}",
                color=0xFB8C00,
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        cfg = await self.bot.db.get_config(interaction.guild_id)
        if cfg and cfg.get("modlog_channel"):
            ch = interaction.guild.get_channel(cfg["modlog_channel"])
            if ch and ch.id != interaction.channel_id:
                await ch.send(embed=embed)

    @mod_group.command(name="warnings", description="[Mod] View warnings for a member")
    @app_commands.describe(member="Member to look up")
    @is_mod()
    async def mod_warnings(self, interaction: discord.Interaction, member: discord.Member):
        warnings = await self.bot.db.get_warnings(interaction.guild_id, member.id)

        if not warnings:
            await interaction.response.send_message(
                f"✅ {member.mention} has no warnings.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.display_name} ({len(warnings)} total)",
            color=0xFB8C00,
        )
        for w in warnings[-10:]:
            embed.add_field(
                name=f"#{w['id']} — {w['created_at'][:10]}",
                value=f"**Reason:** {w['reason'] or 'None'}\n**By:** <@{w['moderator_id']}>",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod_group.command(name="word_add", description="[Mod] Add a custom word to the filter")
    @app_commands.describe(word="Word to block")
    @is_mod()
    async def mod_word_add(self, interaction: discord.Interaction, word: str):
        await self.bot.db.add_filter_word(interaction.guild_id, word.lower())
        self._filter_cache.pop(interaction.guild_id, None)
        await interaction.response.send_message(
            f"✅ Added `{word.lower()}` to the word filter.", ephemeral=True
        )

    @mod_group.command(name="word_remove", description="[Mod] Remove a custom word from the filter")
    @app_commands.describe(word="Word to unblock")
    @is_mod()
    async def mod_word_remove(self, interaction: discord.Interaction, word: str):
        await self.bot.db.remove_filter_word(interaction.guild_id, word.lower())
        self._filter_cache.pop(interaction.guild_id, None)
        await interaction.response.send_message(
            f"✅ Removed `{word.lower()}` from the word filter.", ephemeral=True
        )

    @mod_group.command(name="word_list", description="[Mod] View custom filtered words")
    @is_mod()
    async def mod_word_list(self, interaction: discord.Interaction, show_builtin: bool = False):
        custom = await self._get_filter(interaction.guild_id)

        lines = []
        if show_builtin:
            lines.append(f"**Built-in ({len(BUILTIN_PROFANITY)} words):** always active")
        if custom:
            lines.append(f"**Custom:** ||{', '.join(custom)}||")
        else:
            lines.append("No custom words added yet.")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
