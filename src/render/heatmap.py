"""
Cross-country index heatmap.
Squarified treemap layout using fixed economic weights (to simulate volume/market cap),
coloured by % change according to standard financial market visual constraints.
"""

from __future__ import annotations
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

def get_color(change_pct: float | None, max_abs_change: float) -> str:
    if change_pct is None or max_abs_change == 0:
        return "#e0e0e0" # N/A or neutral
    
    # Scale from 0.2 to 1.0 based on how close it is to the max move
    ratio = min(abs(change_pct) / max_abs_change, 1.0)
    # Ensure minimum saturation so it's clearly colored, scale up to 100%
    intensity = 0.3 + (0.7 * ratio)
    
    if change_pct > 0.0:
        # Interpolate between light green and bright green
        r = int(8 + (230 - 8) * (1 - intensity))
        g = int(153 + (230 - 153) * (1 - intensity))
        b = int(129 + (230 - 129) * (1 - intensity))
        return f"#{r:02x}{g:02x}{b:02x}"
    else:
        # Interpolate between light red and bright red
        r = int(242 + (242 - 242) * (1 - intensity))
        g = int(54 + (230 - 54) * (1 - intensity))
        b = int(69 + (230 - 69) * (1 - intensity))
        return f"#{r:02x}{g:02x}{b:02x}"

def generate_heatmap_data(resolved: list[ResolvedSnapshot], countries_cfg: list) -> list[dict]:
    cfg_by_name = {c.name: c for c in countries_cfg}
    
    valid = [r for r in resolved if r.change_pct is not None]
    if not valid:
        return []

    # Sort by weight so larger boxes appear first in the grid
    valid.sort(key=lambda r: MARKET_WEIGHTS.get(r.country, 1.0), reverse=True)
    
    max_abs = max((abs(r.change_pct) for r in valid), default=0.0)
    
    boxes = []
    for r in valid:
        bbg = cfg_by_name[r.country].bloomberg if r.country in cfg_by_name else r.country
        ticker = bbg.split()[0]
        
        boxes.append({
            "ticker": ticker,
            "change_pct": f"{r.change_pct:+.2f}%",
            "color": get_color(r.change_pct, max_abs)
        })
        
    return boxes
