"""
Cross-country index heatmap — Option A from the outline, confirmed.
9 tiles, uniform size, coloured by % change. Simple deliberately: this
was chosen specifically because it needs no extra data fetch (uses the
same 9 numbers already resolved) and has zero rate-limit exposure.
"""

from __future__ import annotations
import matplotlib
matplotlib.use("Agg")  # headless — no display in CI
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from src.fetch.resilience import ResolvedSnapshot


def render_heatmap(resolved: list[ResolvedSnapshot], out_path: str) -> str:
    """3x3 grid, ranked by |% move| (matches the brief's own ordering
    decision) so the biggest story of the morning is also visually
    top-left, not scattered."""
    ranked = sorted(
        resolved,
        key=lambda r: abs(r.change_pct) if r.change_pct is not None else -1,
        reverse=True,
    )

    fig, axes = plt.subplots(3, 3, figsize=(9, 7))
    fig.patch.set_facecolor("white")

    # Symmetric colour scale so 0% is always the same shade regardless
    # of today's actual range — keeps the email visually consistent
    # day over day, which matters for a "20-second read" product.
    vmax = max([abs(r.change_pct) for r in ranked if r.change_pct is not None] + [1.0])
    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    cmap = plt.cm.RdYlGn  # red = down, green = up — standard convention

    for ax, r in zip(axes.flat, ranked):
        if r.change_pct is None:
            ax.set_facecolor("#e0e0e0")
            ax.text(0.5, 0.5, f"{r.country}\nN/A", ha="center", va="center", fontsize=11)
        else:
            color = cmap(norm(r.change_pct))
            ax.set_facecolor(color)
            text_color = "white" if abs(r.change_pct) > vmax * 0.5 else "black"
            stale_marker = " *" if r.stale else ""
            ax.text(
                0.5, 0.6, r.country, ha="center", va="center",
                fontsize=12, fontweight="bold", color=text_color,
            )
            ax.text(
                0.5, 0.35, f"{r.change_pct:+.2f}%{stale_marker}", ha="center", va="center",
                fontsize=14, color=text_color,
            )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("white")
            spine.set_linewidth(2)

    # Hide any unused subplot cells (fewer than 9 countries resolved, edge case)
    for ax in axes.flat[len(ranked):]:
        ax.axis("off")

    fig.suptitle("Overnight — Index % Change (Local Currency)", fontsize=13, y=0.98)
    fig.text(0.5, 0.01, "* = stale / fallback data source", ha="center", fontsize=8, color="gray")
    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path
