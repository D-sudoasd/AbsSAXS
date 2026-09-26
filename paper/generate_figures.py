#!/usr/bin/env python3
"""Generate the code-derived figures used by the JOSS submission.

The workflow figure is a schematic derived from the package modules and public
interfaces.  The K-factor panel uses deterministic synthetic data solely to
illustrate the robust estimator; it is not an experimental performance claim.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# Run directly from a source checkout without requiring an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saxsabs import estimate_k_factor_robust
from saxsabs.constants import NIST_SRM3600_DATA


MM_PER_INCH = 25.4
JOSS_TEXT_WIDTH_MM = 140.0
JOSS_TEXT_WIDTH_IN = JOSS_TEXT_WIDTH_MM / MM_PER_INCH

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 8.0,
        "axes.titlesize": 8.5,
        "axes.labelsize": 8.5,
        "legend.fontsize": 7.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.7,
        "figure.facecolor": "white",
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)

COLORS = {
    "ink": "#23343D",
    "muted": "#60737D",
    "input": "#EAF2F8",
    "interface": "#FFF1D6",
    "core": "#E5F1EB",
    "output": "#F0EAF4",
    "gate": "#EEF1F3",
    "accent": "#0072B2",
    "warning": "#D55E00",
    "input_edge": "#24618A",
    "interface_edge": "#9A541E",
    "core_edge": "#247451",
    "output_edge": "#725078",
}


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    """Save editable vectors and a 600 dpi raster at the declared final size."""

    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / f"{stem}.svg"
    fig.savefig(svg_path)
    # Matplotlib terminates many SVG path lines with a space. Normalize the
    # generated text so the version-controlled source passes Git whitespace checks.
    svg_lines = svg_path.read_text(encoding="utf-8").splitlines()
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_lines) + "\n",
        encoding="utf-8",
    )
    fig.savefig(output_dir / f"{stem}.pdf")
    fig.savefig(output_dir / f"{stem}.png", dpi=600)


def _box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    facecolor: str,
    *,
    edgecolor: str | None = None,
    fontsize: float = 8.0,
    weight: str = "normal",
) -> None:
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.035,rounding_size=0.10",
        facecolor=facecolor,
        edgecolor=edgecolor or COLORS["ink"],
        linewidth=0.8,
    )
    ax.add_patch(patch)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=COLORS["ink"],
        linespacing=1.2,
    )


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str | None = None,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=8,
            color=color or COLORS["muted"],
            linewidth=0.9,
            shrinkA=3,
            shrinkB=3,
        )
    )


def make_workflow_figure(output_dir: Path) -> None:
    """Render a compact architecture figure at the JOSS text-column width."""

    fig, ax = plt.subplots(figsize=(JOSS_TEXT_WIDTH_IN, 3.55))
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.035, top=0.98)
    ax.set_xlim(0, 14.6)
    ax.set_ylim(1.25, 10)
    ax.axis("off")

    _box(
        ax,
        7.3,
        9.30,
        13.8,
        0.72,
        "Entry points: Python API · CLI · Workbench · strict BL19B2 batch workflow",
        COLORS["gate"],
        edgecolor=COLORS["muted"],
        fontsize=8.1,
    )

    headings = [
        (1.95, "Inputs", "input", 1.75),
        (7.30, "Shared processing", "core", 2.35),
        (12.65, "Outputs", "output", 1.75),
    ]
    for x, label, color_key, half_width in headings:
        ax.text(x, 8.45, label, ha="center", va="center", fontsize=9.2, fontweight="bold")
        ax.plot(
            [x - half_width, x + half_width],
            [8.12, 8.12],
            color=COLORS[color_key],
            linewidth=3.2,
            solid_capstyle="round",
        )

    inputs = [
        (6.80, "2D detector frames\nand instrument headers"),
        (4.80, "External 1D profiles\nand correction metadata"),
        (2.80, "NIST SRM 3600,\nwater, or supplied\nreference curve"),
    ]
    for y, label in inputs:
        _box(
            ax,
            1.95,
            y,
            3.55,
            1.05,
            label,
            COLORS["input"],
            edgecolor=COLORS["input_edge"],
            fontsize=8.0,
        )

    core = [
        (6.90, "Parse, normalize, and\nvalidate inputs", 0.92),
        (5.50, "Reduce detector data and\nintegrate with pyFAI", 0.92),
        (4.10, "Estimate K and propagate\nsupported uncertainty", 0.92),
        (
            2.50,
            "Check intensity state\nand correction history\nbefore calibrated output",
            1.25,
        ),
    ]
    for y, label, height in core:
        _box(
            ax,
            7.30,
            y,
            5.25,
            height,
            label,
            COLORS["core"],
            edgecolor=COLORS["core_edge"],
            fontsize=8.0,
        )

    outputs = [
        (6.70, "Absolute 1D profiles\nand calibrated 2D data"),
        (4.80, "canSAS XML and\nNXcanSAS HDF5"),
        (2.90, "Calibration records,\nsource hashes, QC,\nand run reports"),
    ]
    for y, label in outputs:
        _box(
            ax,
            12.65,
            y,
            3.55,
            1.28,
            label,
            COLORS["output"],
            edgecolor=COLORS["output_edge"],
            fontsize=8.0,
        )

    # These arrows connect the three stages without crossing any labels.
    _arrow(ax, (3.79, 4.80), (4.66, 4.80), color=COLORS["accent"])
    _arrow(ax, (9.94, 4.80), (10.86, 4.80), color=COLORS["accent"])
    save_figure(fig, output_dir, "fig_workflow")
    plt.close(fig)


def make_kfactor_figure(output_dir: Path) -> None:
    """Illustrate the robust K estimator with deterministic synthetic data."""

    rng = np.random.default_rng(42)
    q_ref = NIST_SRM3600_DATA[:, 0]
    i_ref = NIST_SRM3600_DATA[:, 1]
    k_true = 0.035

    q_dense = np.sort(
        np.unique(np.concatenate([np.linspace(float(q_ref.min()), float(q_ref.max()), 240), q_ref]))
    )
    i_ref_dense = np.interp(q_dense, q_ref, i_ref)
    i_meas_dense = i_ref_dense / k_true * (1 + rng.normal(0, 0.025, q_dense.size))
    outlier_reference_indices = np.array([1, 13])
    outlier_dense_indices = np.searchsorted(q_dense, q_ref[outlier_reference_indices])
    outlier_ratios = np.array([k_true * 3.5, k_true * 0.3])
    i_meas_dense[outlier_dense_indices] = i_ref[outlier_reference_indices] / outlier_ratios
    if np.any(i_ref_dense <= 0.0) or np.any(i_meas_dense <= 0.0):
        raise ValueError("log-scale demonstration requires strictly positive intensities")
    i_meas_at_ref = np.interp(q_ref, q_dense, i_meas_dense)
    ratios = i_ref / i_meas_at_ref
    estimate = estimate_k_factor_robust(
        q_dense,
        i_meas_dense,
        q_ref,
        i_ref,
        q_window=(float(q_ref.min()), float(q_ref.max())),
    )
    inliers = np.array(
        [
            np.any(np.isclose(ratio, estimate.ratios_used, rtol=1e-12, atol=1e-15))
            for ratio in ratios
        ]
    )

    fig, axes = plt.subplots(1, 2, figsize=(JOSS_TEXT_WIDTH_IN, 2.82))
    fig.subplots_adjust(left=0.12, right=0.99, bottom=0.24, top=0.85, wspace=0.34)

    left, right = axes
    left.semilogy(
        q_dense,
        i_meas_dense * k_true,
        linestyle="none",
        marker=".",
        markersize=1.5,
        color=COLORS["accent"],
        alpha=0.85,
        zorder=2,
        label="Rescaled synthetic profile",
    )
    left.semilogy(
        q_ref,
        i_ref,
        linestyle="--",
        dashes=(4, 2),
        color=COLORS["warning"],
        linewidth=1.15,
        zorder=1,
        label="NIST SRM 3600 curve (supplied)",
    )
    left.set(xlabel=r"$q$ ($\mathrm{\AA}^{-1}$)", ylabel=r"$I(q)$ ($\mathrm{cm}^{-1}$)")
    left.set_title("Reference and scaled profile", loc="left", fontweight="bold")
    left.text(-0.13, 1.04, "a", transform=left.transAxes, fontsize=9.5, fontweight="bold")
    left.legend(
        frameon=False,
        loc="upper right",
        handlelength=1.7,
        borderaxespad=0.5,
    )

    right.scatter(q_ref[inliers], ratios[inliers], s=16, color=COLORS["accent"], label="Inlier")
    right.scatter(
        q_ref[~inliers],
        ratios[~inliers],
        s=30,
        marker="x",
        linewidth=1.4,
        color=COLORS["warning"],
        label="Rejected",
    )
    right.axhline(
        estimate.k_factor,
        color=COLORS["ink"],
        linewidth=1.0,
        label=f"K = {estimate.k_factor:.4f}",
    )
    right.set(xlabel=r"$q$ ($\mathrm{\AA}^{-1}$)", ylabel=r"$I_{ref}/I_{meas}$")
    right.set_title("Robust K estimate", loc="left", fontweight="bold")
    right.text(-0.13, 1.04, "b", transform=right.transAxes, fontsize=9.5, fontweight="bold")
    right.legend(
        frameon=False,
        ncol=2,
        loc="upper right",
        handlelength=1.8,
        columnspacing=1.0,
        borderaxespad=0.5,
    )

    save_figure(fig, output_dir, "fig_kfactor_demo")
    plt.close(fig)


def sync_readme_assets(output_dir: Path, readme_assets_dir: Path, *, include_demo: bool) -> None:
    """Keep the README workflow and demo images aligned with their source figures."""

    readme_assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output_dir / "fig_workflow.svg", readme_assets_dir / "workflow.svg")
    if include_demo:
        shutil.copyfile(output_dir / "fig_kfactor_demo.png", readme_assets_dir / "kfactor-demo.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="also render the explicitly synthetic K-factor demonstration",
    )
    parser.add_argument(
        "--readme-assets-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets" / "readme",
        help="directory for the matching README SVG and optional demo PNG",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    readme_assets_dir = args.readme_assets_dir.resolve()
    make_workflow_figure(output_dir)
    if args.demo:
        make_kfactor_figure(output_dir)
    sync_readme_assets(output_dir, readme_assets_dir, include_demo=args.demo)
    print(f"Wrote JOSS figures to {output_dir}")


if __name__ == "__main__":
    main()
