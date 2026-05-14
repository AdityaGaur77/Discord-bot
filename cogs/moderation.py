import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_mod


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._filter_cache: dict[int, list[str]] = {}  # guild_id → [words]

    async def _get_filter(self, guild_id: int) -> list[str]:
        if guild_id not in self._filter_cache:
            self._filter_cache[guild_id] = await self.bot.db.get_word_filter(guild_id)
        return self._filter_cache[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        # Skip leadership/admin roles
        member_roles = {r.name for r in message.author.roles}
        if member_roles & {"Coach", "Mentor", "Captain"} or message.author.guild_permissions.administrator:
            return

        bad_words = await self._get_filter(message.guild.id)
        if not bad_words:
            return

        content_lower = message.content.lower()
        for word in bad_words:
            if word in content_lower:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, that language isn't allowed here.",
                        delete_after=5,
                    )
                except discord.Forbidden:
                    pass

                # Log to mod channel if configured
                cfg = await self.bot.db.get_config(message.guild.id)
                if cfg and cfg.get("modlog_channel"):
                    ch = message.guild.get_channel(cfg["modlog_channel"])
                    if ch:
                        embed = discord.Embed(
                            title="🚨 Word Filter Triggered",
                            color=0xE53935,
                        )
                        embed.add_field(name="User",    value=message.author.mention)
                        embed.add_field(name="Channel", value=message.channel.mention)
                        embed.add_field(name="Word",    value=f"||{word}||")
                        await ch.send(embed=embed)
                break

    # ── /mod word ─────────────────────────────────────────────────────────────

    mod_group = app_commands.Group(name="mod", description="Moderation tools")

    @mod_group.command(name="word_add", description="[Mod] Add a word to the filter")
    @app_commands.describe(word="Word to block")
    @is_mod()
    async def mod_word_add(self, interaction: discord.Interaction, word: str):
        await self.bot.db.add_filter_word(interaction.guild_id, word.lower())
        self._filter_cache.pop(interaction.guild_id, None)  # Invalidate cache
        await interaction.response.send_message(
            f"✅ Added `{word.lower()}` to the word filter.", ephemeral=True
        )

    @mod_group.command(name="word_remove", description="[Mod] Remove a word from the filter")
    @app_commands.describe(word="Word to unblock")
    @is_mod()
    async def mod_word_remove(self, interaction: discord.Interaction, word: str):
        await self.bot.db.remove_filter_word(interaction.guild_id, word.lower())
        self._filter_cache.pop(interaction.guild_id, None)
        await interaction.response.send_message(
            f"✅ Removed `{word.lower()}` from the word filter.", ephemeral=True
        )

    @mod_group.command(name="word_list", description="[Mod] View all filtered words")
    @is_mod()
    async def mod_word_list(self, interaction: discord.Interaction):
        words = await self._get_filter(interaction.guild_id)
        if not words:
            await interaction.response.send_message(
                "No words in the filter yet.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"🚫 Filtered words: ||{', '.join(words)}||", ephemeral=True
        )

    # ── /warn ─────────────────────────────────────────────────────────────────

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

        # DM the member
        try:
            dm_embed = discord.Embed(
                title="⚠️ You received a warning",
                description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason}",
                color=0xFB8C00,
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # Log to mod channel
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
        for w in warnings[-10:]:  # Show last 10
            embed.add_field(
                name=f"#{w['id']} — {w['created_at'][:10]}",
                value=f"**Reason:** {w['reason'] or 'None'}\n**By:** <@{w['moderator_id']}>",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
