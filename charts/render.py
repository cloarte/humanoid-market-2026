"""Rendering helpers shared by the matplotlib charts: figure setup, PNG export, animated GIF."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # file output only; no window
import matplotlib.pyplot as plt
from PIL import Image

from src import style

FIG_HEIGHT_IN = 7.5
GIF_FPS = 10


def new_figure(height_in: float = FIG_HEIGHT_IN):
    style.apply()
    return plt.figure(figsize=(style.FIG_WIDTH_IN, height_in))


def ramp(t: float, start: float, end: float) -> float:
    """0 before `start`, 1 after `end`, linear in between (for fade-ins)."""
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    return (t - start) / (end - start)


def save_gif(draw: Callable[[plt.Figure, float], None], name: str, seconds: float) -> Path:
    """Render `draw(fig, t)` for t in [0, seconds], hold the final frame, write outputs/<name>.gif.

    The GIF is GIF_WIDTH_PX wide, lasts between style.GIF_SECONDS, and must stay under GIF_MAX_BYTES.
    """
    dpi = style.GIF_WIDTH_PX / style.FIG_WIDTH_IN
    n = round(seconds * GIF_FPS)
    frames = []
    for i in range(n + 1):
        fig = new_figure()
        draw(fig, i / GIF_FPS)
        fig.set_dpi(dpi)
        fig.canvas.draw()
        rgba = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba(), "raw", "RGBA", 0, 1)
        frames.append(
            rgba.convert("RGB").quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        )
        plt.close(fig)
    durations = [round(1000 / GIF_FPS)] * len(frames)
    durations[-1] = round(style.GIF_HOLD_FINAL_S * 1000)
    total = sum(durations) / 1000
    lo, hi = style.GIF_SECONDS
    if not lo <= total <= hi:
        raise ValueError(f"{name}.gif lasts {total:.1f}s; allowed {lo}-{hi}s")
    path = style.OUTPUTS / f"{name}.gif"
    style.OUTPUTS.mkdir(exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    if path.stat().st_size > style.GIF_MAX_BYTES:
        raise ValueError(
            f"{name}.gif is {path.stat().st_size / 1e6:.1f} MB; limit is {style.GIF_MAX_BYTES / 1e6:.0f} MB"
        )
    return path
