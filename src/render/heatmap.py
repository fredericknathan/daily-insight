"""
Cross-country index heatmap.
Squarified treemap layout using fixed economic weights (to simulate volume/market cap),
coloured by % change according to standard financial market visual constraints.
"""

from __future__ import annotations
import matplotlib
matplotlib.use("Agg")  # headless — no display in CI
import matplotlib.pyplot as plt
import squarify
from src.fetch.resilience import ResolvedSnapshot

# Proxy for "volume" / market size to ensure USA is largest, ID is smaller, etc.
# Values roughly represent exchange market cap in USD Trillions.
MARKET_WEIGHTS = {
    "USA": 50.0,
    "Japan": 6.0,
    "Hong Kong": 4.0,
    "Korea": 2.0,
    "Indonesia": 0.8,
    "Singapore": 0.6,
    "Philippines": 0.3,
    "Vietnam": 0.2,
}

def get_color(change_pct: float | None) -> str:
    if change_pct is None:
        return "#e0e0e0" # N/A
    if change_pct >= 3.0:
        return "#089981" # Bright Lime/Green
    elif change_pct >= 1.0:
        return "#26a69a" # Medium Green
    elif change_pct > -1.0:
        return "#1e222d" # Neutral Muted Dark Gray
    elif change_pct > -3.0:
        return "#ef5350" # Medium Red
    else:
        return "#f23645" # Bright Crimson/Red

def render_heatmap(resolved: list[ResolvedSnapshot], countries_cfg: list, out_path: str) -> str:
    cfg_by_name = {c.name: c for c in countries_cfg}
    
    # Filter out unavailable
    valid = [r for r in resolved if r.change_pct is not None]
    if not valid:
        # Fallback to simple plot if nothing is valid
        fig, ax = plt.subplots(figsize=(9, 7))
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=20)
        ax.axis("off")
        plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return out_path

    # Sort by weight so larger boxes are clustered appropriately by squarify
    valid.sort(key=lambda r: MARKET_WEIGHTS.get(r.country, 1.0), reverse=True)

    sizes = [MARKET_WEIGHTS.get(r.country, 1.0) for r in valid]
    colors = [get_color(r.change_pct) for r in valid]
    
    labels = []
    for r in valid:
        bbg = cfg_by_name[r.country].bloomberg if r.country in cfg_by_name else r.country
        ticker = bbg.split()[0]  # Just take the ticker part, e.g., 'SPX' from 'SPX Index'
        
        stale_marker = " *" if r.stale else ""
        label = f"{ticker}\n{r.change_pct:+.2f}%{stale_marker}"
        labels.append(label)

    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    
    squarify.plot(
        sizes=sizes,
        label=labels,
        color=colors,
        alpha=1.0,
        ax=ax,
        text_kwargs={'fontsize': 14, 'color': 'white', 'fontweight': 'bold'},
        edgecolor="white",
        linewidth=2
    )

    ax.axis('off')
    
    plt.tight_layout(rect=[0, 0, 1, 1])
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white", pad_inches=0.0)
    plt.close(fig)
    return out_path
