import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_leadership

STATUS_COLORS = {"open": 0x1565C0, "done": 0x43A047}
PRIORITY_ICONS = {"high": "!!!", "medium": "!!", "low": "!"}
PRIORITY_COLORS = {"high": 0xE53935, "medium": 0xFB8C00, "low": 0x43A047}


class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    task_group = app_commands.Group(name="task", description="Team task management")

    @task_group.command(name="add", description="Add a new team task")
    @app_commands.describe(
        title="Task description",
        owner="Who owns this task",
        subteam="Which subteam (programming, build, cad, etc.)",
        due="Due date, e.g. 'Friday' or '2026-01-15'",
        priority="Task priority: high, medium, or low",
    )
    @app_commands.choices(priority=[
        app_commands.Choice(name="High", value="high"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Low", value="low"),
    ])
    async def task_add(
        self,
        interaction: discord.Interaction,
        title: str,
        owner: discord.Member = None,
        subteam: str = None,
        due: str = None,
        priority: str = "medium",
    ):
        owner_id = owner.id if owner else interaction.user.id
        task_id = await self.bot.db.add_task(
            interaction.guild_id, title, owner_id, subteam, due, priority
        )

        color = PRIORITY_COLORS.get(priority, 0x1565C0)
        embed = discord.Embed(
            title="Task Added",
            description=f"**#{task_id}** {title}",
            color=color,
        )
        embed.add_field(name="Priority", value=priority.capitalize())
        if owner:
            embed.add_field(name="Owner",   value=owner.mention)
        if subteam:
            embed.add_field(name="Subteam", value=subteam.capitalize())
        if due:
            embed.add_field(name="Due",     value=due)

        await interaction.response.send_message(embed=embed)

        # Post to tasks channel if configured
        cfg = await self.bot.db.get_config(interaction.guild_id)
        if cfg and cfg.get("tasks_channel") and cfg["tasks_channel"] != interaction.channel_id:
            ch = interaction.guild.get_channel(cfg["tasks_channel"])
            if ch:
                await ch.send(embed=embed)

    @task_group.command(name="list", description="List open tasks")
    @app_commands.describe(
        status="Filter by status: open or done",
        subteam="Filter by subteam",
    )
    async def task_list(
        self,
        interaction: discord.Interaction,
        status: str = "open",
        subteam: str = None,
    ):
        tasks = await self.bot.db.get_tasks(interaction.guild_id, status, subteam)

        if not tasks:
            filter_str = f" for **{subteam}**" if subteam else ""
            await interaction.response.send_message(
                f"No **{status}** tasks{filter_str}.", ephemeral=True
            )
            return

        lines = []
        for t in tasks:
            owner_str   = f"<@{t['owner_id']}>" if t.get("owner_id") else "unassigned"
            subteam_str = f" `[{t['subteam']}]`" if t.get("subteam") else ""
            due_str     = f" | due {t['due_date']}" if t.get("due_date") else ""
            priority    = t.get("priority", "medium")
            priority_icon = PRIORITY_ICONS.get(priority, "!!")
            status_icon = "[x]" if t["status"] == "done" else "[ ]"
            lines.append(
                f"{status_icon} `{priority_icon}` **#{t['id']}** {t['title']}{subteam_str} — {owner_str}{due_str}"
            )

        embed = discord.Embed(
            title=f"{status.capitalize()} Tasks" + (f" - {subteam}" if subteam else ""),
            description="\n".join(lines),
            color=STATUS_COLORS.get(status, 0x1565C0),
        )
        embed.set_footer(text=f"{len(tasks)} task(s) | Priority: !!! high, !! medium, ! low")
        await interaction.response.send_message(embed=embed)

    @task_group.command(name="done", description="Mark a task as completed")
    @app_commands.describe(task_id="Task ID number from /task list")
    async def task_done(self, interaction: discord.Interaction, task_id: int):
        closed = await self.bot.db.close_task(interaction.guild_id, task_id)
        if closed:
            await interaction.response.send_message(
                f"✅ Task **#{task_id}** marked as done!"
            )
        else:
            await interaction.response.send_message(
                f"❌ Task **#{task_id}** not found or already done.", ephemeral=True
            )

    @task_group.command(name="assign", description="[Leadership] Reassign a task to someone")
    @app_commands.describe(task_id="Task ID", member="New owner")
    @is_leadership()
    async def task_assign(
        self, interaction: discord.Interaction, task_id: int, member: discord.Member
    ):
        success = await self.bot.db.assign_task(interaction.guild_id, task_id, member.id)
        if not success:
            await interaction.response.send_message(
                f"Task **#{task_id}** not found or already completed.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Task **#{task_id}** reassigned to {member.mention}"
        )


async def setup(bot):
    await bot.add_cog(TasksCog(bot))
