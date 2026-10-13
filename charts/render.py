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


def highlight(t: float, phases: list[tuple[float, float]], fade: tuple[float, float, float, float]) -> list[float]:
    """Opacity helpers for a "never empty" GIF. `fade` = (dim from, dim to, back from, back to): everything dims,
    then each phase (start, end) brings its marks back; at the end everything returns to full colour.
    Returns [dim, phase_1, phase_2, ...], each in 0..1."""
    dim = ramp(t, fade[0], fade[1]) * (1 - ramp(t, fade[2], fade[3]))
    return [dim, *(ramp(t, a, b) for a, b in phases)]


def opacity(dim: float, lit: float, floor: float = 0.22) -> float:
    """Opacity of a mark: 1 when nothing is dimmed or the mark is lit, `floor` when dimmed and not lit."""
    return 1 - (1 - floor) * dim * (1 - lit)


def _frame(draw: Callable[[plt.Figure, float], None], t: float) -> Image.Image:
    fig = new_figure()
    draw(fig, t)
    fig.set_dpi(style.GIF_WIDTH_PX / style.FIG_WIDTH_IN)
    fig.canvas.draw()
    rgba = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba(), "raw", "RGBA", 0, 1)
    plt.close(fig)
    return rgba.convert("RGB")


def save_gif(draw: Callable[[plt.Figure, float], None], name: str, seconds: float) -> Path:
    """Render `draw(fig, t)` for t in [0, seconds] and write outputs/<name>.gif.

    The first frame is the cover that phones, social previews and some e-mail clients show on their own, so
    it must be the complete chart: the GIF is refused unless draw(fig, 0) equals the static chart draw(fig).
    The first frame is held GIF_HOLD_FIRST_S, the last GIF_HOLD_FINAL_S. The GIF is GIF_WIDTH_PX wide, lasts
    between style.GIF_SECONDS and must stay under GIF_MAX_BYTES.
    """
    full = _frame(draw, 99.0)
    raw = [_frame(draw, i / GIF_FPS) for i in range(round(seconds * GIF_FPS) + 1)]
    for which, frame in (("first", raw[0]), ("last", raw[-1])):
        if frame.tobytes() != full.tobytes():
            raise ValueError(f"{name}.gif: the {which} frame is not the complete chart (a GIF must never start empty)")
    frames = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in raw]
    durations = [round(1000 / GIF_FPS)] * len(frames)
    durations[0] = round(style.GIF_HOLD_FIRST_S * 1000)
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
