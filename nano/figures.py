"""Figures. Every one of them is drawn from a run, never from an illustration.

matplotlib and pillow are optional dependencies (``pip install -e '.[figures]'``);
importing this module without them raises with that instruction rather than
failing obscurely deep inside a plot call.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import animation
except ImportError as exc:  # pragma: no cover - depends on the environment
    raise ImportError(
        "Figures need matplotlib and pillow. Install them with: pip install -e '.[figures]'"
    ) from exc

from nano.agent import EpisodeResult
from nano.data import WaferRecord

PREDICTION_CMAP = "magma"
UNCERTAINTY_CMAP = "viridis"
STRATEGY_STYLE = {
    "nano": {"color": "#2f6df6", "linestyle": "-", "label": "NANO"},
    "random": {"color": "#8a8f98", "linestyle": "--", "label": "Random"},
    "grid": {"color": "#e08b2a", "linestyle": "-.", "label": "Grid"},
}


def save(fig, path: Path | str, *, dpi: int = 140) -> Path:
    """Write a figure, converting to WebP through pillow when asked for one."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".webp":
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)
        from PIL import Image

        Image.open(buffer).convert("RGB").save(out, format="WEBP", quality=88, method=5)
    else:
        fig.savefig(out, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
    return out


def _panel(ax, record: WaferRecord, values: np.ndarray, title: str, *, cmap: str, vmin=0.0, vmax=1.0):
    grid = record.to_grid(values)
    image = ax.imshow(grid, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    return image


def _mark_measured(ax, record: WaferRecord, observed_mask: np.ndarray, color="#ffffff"):
    coords = record.coords[np.asarray(observed_mask, dtype=bool)]
    if coords.size:
        ax.scatter(
            coords[:, 1], coords[:, 0], s=6, facecolors="none", edgecolors=color, linewidths=0.6
        )


# --------------------------------------------------------------------------- #
# Benchmark figures
# --------------------------------------------------------------------------- #


def plot_error_curve(summary: dict, path: Path | str) -> Path:
    """Measurements versus reconstruction error, one line per strategy."""
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    metric = summary.get("metric", {})
    for name, strategy in summary.get("strategies", {}).items():
        curve = strategy.get("curve") or []
        if not curve:
            continue
        style = STRATEGY_STYLE.get(name, {"color": None, "linestyle": "-", "label": name})
        xs = [point["measurements"] for point in curve]
        means = np.array([point["mean"] for point in curve])
        stds = np.array([point.get("std", 0.0) or 0.0 for point in curve])
        ax.plot(xs, means, color=style["color"], linestyle=style["linestyle"], label=style["label"])
        ax.fill_between(xs, means - stds, means + stds, color=style["color"], alpha=0.12, linewidth=0)

    prior = summary.get("prior", {}).get("initial_error", {}).get("mean")
    if prior is not None:
        ax.axhline(prior, color="#c0392b", linewidth=1.0, linestyle=":", label="Prior, uncorrected")

    ax.set_xlabel("measurements taken (initial + budget spent)")
    ax.set_ylabel(f"{metric.get('name', 'error')} ↓ ({metric.get('unit', '')})".strip())
    ax.set_title("Reconstruction error against measurement count", fontsize=11)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=9)
    _footer(fig, summary)
    return save(fig, path)


def plot_paired_improvement(summary: dict, path: Path | str) -> Path:
    """Per-episode difference between NANO and each baseline, wins and losses both visible."""
    episodes = summary.get("episodes") or []
    if not episodes:
        raise ValueError("summary has no per-episode records to pair")

    baselines = [name for name in ("random", "grid") if name in summary.get("strategies", {})]
    fig, axes = plt.subplots(1, len(baselines), figsize=(5.2 * len(baselines), 4.4), squeeze=False)

    for ax, name in zip(axes[0], baselines):
        deltas = np.array(
            [ep["final"][name] - ep["final"]["nano"] for ep in episodes if "nano" in ep["final"]]
        )
        order = np.argsort(deltas)
        colours = ["#2f6df6" if d > 0 else "#c0392b" for d in deltas[order]]
        ax.bar(np.arange(deltas.size), deltas[order], color=colours, width=0.85)
        ax.axhline(0, color="#333", linewidth=0.8)
        wins = int((deltas > 0).sum())
        ax.set_title(
            f"NANO − {STRATEGY_STYLE[name]['label']}: {wins}/{deltas.size} episodes better",
            fontsize=10,
        )
        ax.set_xlabel("episode (wafer × seed), sorted")
        ax.set_ylabel("baseline error − NANO error")
        ax.grid(alpha=0.2, axis="y")

    fig.suptitle("Paired per-episode improvement (positive = NANO better)", fontsize=11)
    _footer(fig, summary)
    return save(fig, path)


def plot_wafer_comparison(
    record: WaferRecord, prior: np.ndarray, episode: EpisodeResult, path: Path | str
) -> Path:
    """Biased prior, NANO reconstruction and hidden ground truth on a common scale."""
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.9))
    _panel(axes[0], record, prior, "Biased prior (simulation)", cmap=PREDICTION_CMAP)
    image = _panel(axes[1], record, episode.prediction, "NANO reconstruction", cmap=PREDICTION_CMAP)
    _mark_measured(axes[1], record, episode.observed_mask)
    _panel(axes[2], record, record.reality, "Ground truth (hidden from agent)", cmap=PREDICTION_CMAP)
    fig.colorbar(image, ax=axes, fraction=0.025, pad=0.02, label="failure probability")
    fig.suptitle(
        f"{record.wafer_id} · {record.pattern} · "
        f"{episode.n_initial} initial + {episode.budget} measured",
        fontsize=10,
    )
    return save(fig, path)


def plot_uncertainty_before_after(
    record: WaferRecord, episode: EpisodeResult, path: Path | str
) -> Path:
    """Where the agent knew it was blind, before and after spending the budget."""
    first, last = episode.steps[0], episode.steps[-1]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9))
    _panel(axes[0], record, first.uncertainty, f"Uncertainty at {first.measurements} measurements",
           cmap=UNCERTAINTY_CMAP)
    image = _panel(axes[1], record, last.uncertainty,
                   f"Uncertainty at {last.measurements} measurements", cmap=UNCERTAINTY_CMAP)
    _mark_measured(axes[1], record, episode.observed_mask, color="#ff5c5c")
    fig.colorbar(image, ax=axes, fraction=0.03, pad=0.02, label="uncertainty (relative)")
    fig.suptitle(f"{record.wafer_id} · uncertainty collapse over one budget", fontsize=10)
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Demo figures
# --------------------------------------------------------------------------- #


def plot_demo_step(record: WaferRecord, episode: EpisodeResult, step_index: int, path: Path | str) -> Path:
    """Prediction and uncertainty at one iteration, with measured dies marked."""
    step = episode.steps[step_index]
    observed = episode.mask_at_step(step_index)
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9))
    _panel(axes[0], record, step.prediction, f"Prediction · {step.measurements} measurements",
           cmap=PREDICTION_CMAP)
    _mark_measured(axes[0], record, observed)
    _panel(axes[1], record, step.uncertainty, "Uncertainty", cmap=UNCERTAINTY_CMAP)
    _mark_measured(axes[1], record, observed, color="#ff5c5c")
    fig.suptitle(f"{record.wafer_id} · {record.pattern}", fontsize=10)
    return save(fig, path)


def plot_selection(
    record: WaferRecord,
    episode: EpisodeResult,
    terms: dict[str, np.ndarray],
    step_index: int,
    path: Path | str,
) -> Path:
    """The acquisition surface at the moment of choice, decomposed into its terms."""
    step = episode.steps[step_index]
    acquisition = np.where(np.isfinite(terms["acquisition"]), terms["acquisition"], np.nan)
    fig, axes = plt.subplots(1, 4, figsize=(13.5, 3.8))
    for ax, (title, values, cmap) in zip(
        axes,
        [
            ("uncertainty", terms["uncertainty"], UNCERTAINTY_CMAP),
            ("simulation disagreement", terms["disagreement"], "cividis"),
            ("spatial novelty", terms["novelty"], "bone"),
            ("acquisition = product", acquisition, "inferno"),
        ],
    ):
        finite = values[np.isfinite(values)]
        _panel(ax, record, values, title, cmap=cmap,
               vmin=float(np.nanmin(finite)), vmax=float(np.nanmax(finite)))
    if step.selected_index is not None:
        row, col = record.coords[step.selected_index]
        for ax in axes:
            ax.scatter([col], [row], s=90, facecolors="none", edgecolors="#00ff9d", linewidths=1.6)
    score = "" if step.score is None else f" · score {step.score:.4f}"
    fig.suptitle(
        f"Selection at {step.measurements} measurements · die {step.selected_index}{score}",
        fontsize=10,
    )
    return save(fig, path)


def plot_final_comparison(
    record: WaferRecord, prior: np.ndarray, episode: EpisodeResult, path: Path | str
) -> Path:
    return plot_wafer_comparison(record, prior, episode, path)


def animate_episode(
    record: WaferRecord, episode: EpisodeResult, path: Path | str, *, fps: int = 6, stride: int = 1
) -> Path:
    """The whole episode as a GIF: prediction, uncertainty, and the point just taken."""
    indices = list(range(0, len(episode.steps), stride))
    if indices[-1] != len(episode.steps) - 1:
        indices.append(len(episode.steps) - 1)

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9))
    first = episode.steps[0]
    prediction_img = _panel(axes[0], record, first.prediction, "Prediction", cmap=PREDICTION_CMAP)
    uncertainty_img = _panel(axes[1], record, first.uncertainty, "Uncertainty", cmap=UNCERTAINTY_CMAP)
    title = fig.suptitle("", fontsize=10)
    marker = axes[0].scatter([], [], s=80, facecolors="none", edgecolors="#00ff9d", linewidths=1.5)

    def draw(step_index: int):
        step = episode.steps[step_index]
        prediction_img.set_data(record.to_grid(step.prediction))
        uncertainty_img.set_data(record.to_grid(step.uncertainty))
        if step.selected_index is not None:
            row, col = record.coords[step.selected_index]
            marker.set_offsets(np.array([[col, row]]))
        else:
            marker.set_offsets(np.empty((0, 2)))
        title.set_text(
            f"{record.wafer_id} · {record.pattern} · {step.measurements} measurements"
        )
        return prediction_img, uncertainty_img, marker, title

    anim = animation.FuncAnimation(fig, draw, frames=indices, blit=False)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    anim.save(out, writer=animation.PillowWriter(fps=fps))
    plt.close(fig)
    return out


def _footer(fig, summary: dict) -> None:
    experiment = summary.get("experiment", {})
    dataset = summary.get("dataset", {})
    seeds = experiment.get("seeds", [])
    fig.text(
        0.5,
        -0.02,
        f"{dataset.get('name', 'unknown source')} · {dataset.get('n_wafers', '?')} wafers × "
        f"{len(seeds)} seeds · {experiment.get('initial_measurements', '?')} initial + "
        f"{experiment.get('measurement_budget', '?')} budget · "
        f"generated {summary.get('generated_at', '')}",
        ha="center",
        fontsize=7,
        color="#666",
    )


def strategy_series(summary: dict, name: str) -> Sequence[dict]:
    return summary.get("strategies", {}).get(name, {}).get("curve", [])
