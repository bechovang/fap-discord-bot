"""
Discord progress helpers for long-running interaction flows.
"""
from __future__ import annotations

import discord


def render_progress_bar(current: int, total: int, width: int = 10) -> str:
    """Render a compact text progress bar for Discord messages."""
    total = max(total, 1)
    current = max(0, min(current, total))
    filled = round((current / total) * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {current}/{total}"


class InteractionProgress:
    """Track and update a single progress message tied to an interaction."""

    def __init__(self, interaction: discord.Interaction, title: str, ephemeral: bool = True):
        self.interaction = interaction
        self.title = title
        self.ephemeral = ephemeral
        self.message: discord.WebhookMessage | None = None

    def _build_embed(
        self,
        status: str,
        current: int,
        total: int,
        detail: str,
        color: discord.Color,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Progress", value=render_progress_bar(current, total), inline=False)
        embed.add_field(name="Current Step", value=detail, inline=False)
        return embed

    async def start(self, total: int, detail: str):
        embed = self._build_embed(
            status="Starting",
            current=0,
            total=total,
            detail=detail,
            color=discord.Color.blurple(),
        )
        self.message = await self.interaction.followup.send(
            embed=embed,
            ephemeral=self.ephemeral,
            wait=True,
        )

    async def update(self, current: int, total: int, detail: str):
        if not self.message:
            await self.start(total=total, detail=detail)
            return

        embed = self._build_embed(
            status="Working",
            current=current,
            total=total,
            detail=detail,
            color=discord.Color.gold(),
        )
        await self.message.edit(embed=embed)

    async def complete(self, total: int, detail: str = "Completed"):
        if not self.message:
            await self.start(total=total, detail=detail)

        embed = self._build_embed(
            status="Done",
            current=total,
            total=total,
            detail=detail,
            color=discord.Color.green(),
        )
        await self.message.edit(embed=embed)

    async def fail(self, current: int, total: int, detail: str):
        if not self.message:
            await self.start(total=total, detail=detail)

        embed = self._build_embed(
            status="Failed",
            current=current,
            total=total,
            detail=detail,
            color=discord.Color.red(),
        )
        await self.message.edit(embed=embed)
