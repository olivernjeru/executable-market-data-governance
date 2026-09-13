# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
  This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.
"""

import json
import os
import sys
from typing import Dict, List, Any


def load_history(history_path: str) -> List[Dict[str, Any]]:
    with open(history_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def extract_metrics(history: List[Dict[str, Any]]):
    epochs: List[int] = []
    mean_sharpes: List[float] = []
    min_sharpes: List[float] = []
    max_sharpes: List[float] = []
    epoch_times: List[float] = []

    # Collect dynamic agent series
    agent_sharpe_series: Dict[str, List[float]] = {}
    agent_total_reward_series: Dict[str, List[float]] = {}
    agent_max_drawdown_series: Dict[str, List[float]] = {}
    mean_ann_vols: List[float] = []
    mean_sortinos: List[float] = []
    mean_ann_returns: List[float] = []
    agent_ann_vol_series: Dict[str, List[float]] = {}
    agent_sortino_series: Dict[str, List[float]] = {}
    agent_ann_return_series: Dict[str, List[float]] = {}
    agent_turnover_series: Dict[str, List[float]] = {}

    # Training losses/entropy (averaged across agents per epoch)
    avg_policy_losses: List[float] = []
    avg_value_losses: List[float] = []
    avg_entropies: List[float] = []

    for entry in history:
        epoch = entry.get("epoch")
        train = entry.get("train", {})
        val = entry.get("val", {})

        epochs.append(epoch)
        epoch_times.append(float(train.get("epoch_time", 0.0)))
        mean_sharpes.append(float(val.get("mean_sharpe", float("nan"))))
        min_sharpes.append(float(val.get("min_sharpe", float("nan"))))
        max_sharpes.append(float(val.get("max_sharpe", float("nan"))))
        mean_ann_vols.append(float(val.get("mean_ann_vol", float("nan"))))
        mean_sortinos.append(float(val.get("mean_sortino", float("nan"))))
        mean_ann_returns.append(float(val.get("mean_ann_return_pct", float("nan"))))

        # Extract per-agent sharpes and other metrics dynamically
        for k, v in val.items():
            if not k.endswith("_sharpe"):
                pass
            else:
                if k in ("mean_sharpe", "min_sharpe", "max_sharpe"):
                    pass
                else:
                    agent = k[: -len("_sharpe")]
                    agent_sharpe_series.setdefault(agent, []).append(float(v))
            if k.endswith("_total_reward"):
                agent = k[: -len("_total_reward")]
                agent_total_reward_series.setdefault(agent, []).append(float(v))
            if k.endswith("_max_drawdown"):
                agent = k[: -len("_max_drawdown")]
                agent_max_drawdown_series.setdefault(agent, []).append(float(v))
            if k.endswith("_ann_vol"):
                agent = k[: -len("_ann_vol")]
                agent_ann_vol_series.setdefault(agent, []).append(float(v))
            if k.endswith("_sortino"):
                agent = k[: -len("_sortino")]
                agent_sortino_series.setdefault(agent, []).append(float(v))
            if k.endswith("_ann_return_pct"):
                agent = k[: -len("_ann_return_pct")]
                agent_ann_return_series.setdefault(agent, []).append(float(v))
            if k.endswith("_total_turnover"):
                agent = k[: -len("_total_turnover")]
                agent_turnover_series.setdefault(agent, []).append(float(v))

        # Compute averages across agents for policy/value loss and entropy
        policy_losses = [
            float(x) for k, x in train.items() if k.endswith("_policy_loss")
        ]
        value_losses = [float(x) for k, x in train.items() if k.endswith("_value_loss")]
        entropies = [float(x) for k, x in train.items() if k.endswith("_entropy")]
        avg_policy_losses.append(
            sum(policy_losses) / len(policy_losses) if policy_losses else float("nan")
        )
        avg_value_losses.append(
            sum(value_losses) / len(value_losses) if value_losses else float("nan")
        )
        avg_entropies.append(
            sum(entropies) / len(entropies) if entropies else float("nan")
        )

    return {
        "epochs": epochs,
        "mean_sharpes": mean_sharpes,
        "min_sharpes": min_sharpes,
        "max_sharpes": max_sharpes,
        "epoch_times": epoch_times,
        "agent_sharpe_series": agent_sharpe_series,
        "agent_total_reward_series": agent_total_reward_series,
        "agent_max_drawdown_series": agent_max_drawdown_series,
        "mean_ann_vols": mean_ann_vols,
        "mean_sortinos": mean_sortinos,
        "mean_ann_returns": mean_ann_returns,
        "agent_ann_vol_series": agent_ann_vol_series,
        "agent_sortino_series": agent_sortino_series,
        "agent_ann_return_series": agent_ann_return_series,
        "agent_turnover_series": agent_turnover_series,
        "avg_policy_losses": avg_policy_losses,
        "avg_value_losses": avg_value_losses,
        "avg_entropies": avg_entropies,
    }


def get_best_epoch(metrics: Dict[str, Any]) -> int:
    epochs = metrics["epochs"]
    mean_sharpes = metrics["mean_sharpes"]
    if not epochs:
        return -1
    return max(
        range(len(epochs)),
        key=lambda i: (
            mean_sharpes[i] if mean_sharpes[i] == mean_sharpes[i] else -float("inf")
        ),
    )


def save_summary_markdown(output_dir: str, metrics: Dict[str, Any]) -> None:
    ensure_dir(output_dir)
    epochs = metrics["epochs"]
    mean_sharpes = metrics["mean_sharpes"]
    min_sharpes = metrics["min_sharpes"]
    max_sharpes = metrics["max_sharpes"]
    epoch_times = metrics["epoch_times"]

    if epochs:
        best_idx = get_best_epoch(metrics)
        best_epoch = epochs[best_idx]
        best_mean = mean_sharpes[best_idx]
        best_min = min_sharpes[best_idx]
        best_max = max_sharpes[best_idx]
        # Aggregated metrics at best epoch (if available)
        best_mean_ann_vol = metrics.get("mean_ann_vols", [])
        best_mean_sortino = metrics.get("mean_sortinos", [])
        best_mean_ann_return = metrics.get("mean_ann_returns", [])
        best_mean_ann_vol = (
            best_mean_ann_vol[best_idx]
            if len(best_mean_ann_vol) > best_idx
            else float("nan")
        )
        best_mean_sortino = (
            best_mean_sortino[best_idx]
            if len(best_mean_sortino) > best_idx
            else float("nan")
        )
        best_mean_ann_return = (
            best_mean_ann_return[best_idx]
            if len(best_mean_ann_return) > best_idx
            else float("nan")
        )
    else:
        best_idx = -1
        best_epoch = -1
        best_mean = best_min = best_max = float("nan")
        best_mean_ann_vol = best_mean_sortino = best_mean_ann_return = float("nan")

    total_time = sum(t for t in epoch_times if t == t)
    avg_time = (
        (total_time / len([t for t in epoch_times if t == t]))
        if epoch_times
        else float("nan")
    )

    md_path = os.path.join(output_dir, "results_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Training Results Summary\n\n")
        f.write(
            f"Epochs: {len(epochs)} (from {epochs[0] if epochs else 'N/A'} to {epochs[-1] if epochs else 'N/A'})\n\n"
        )
        f.write("## Best Epoch (by mean Sharpe)\n\n")
        f.write(f"- Epoch: {best_epoch}\n")
        f.write(f"- Mean Sharpe: {best_mean:.4f}\n")
        f.write(f"- Min Sharpe: {best_min:.4f}\n")
        f.write(f"- Max Sharpe: {best_max:.4f}\n\n")
        f.write("## Timing\n\n")
        f.write(f"- Total training time: {total_time/3600:.2f} hours\n")
        f.write(f"- Average epoch time: {avg_time/60:.2f} minutes\n\n")
        f.write("## Aggregate Metrics at Best Epoch\n\n")
        f.write(f"- Mean Annualized Volatility: {best_mean_ann_vol:.4f}\n")
        f.write(f"- Mean Sortino: {best_mean_sortino:.4f}\n")
        f.write(f"- Mean Annualized Return: {best_mean_ann_return:.2f}%\n\n")
        f.write("## Files\n\n")
        f.write("- Plots saved alongside this file in this folder.\n")


def save_metrics_csv(output_dir: str, metrics: Dict[str, Any]) -> None:
    import csv

    ensure_dir(output_dir)
    csv_path = os.path.join(output_dir, "metrics_summary.csv")
    epochs = metrics["epochs"]
    header = [
        "epoch",
        "mean_sharpe",
        "min_sharpe",
        "max_sharpe",
        "epoch_time_sec",
        "avg_policy_loss",
        "avg_value_loss",
        "avg_entropy",
    ]
    # Aggregate metrics
    header.extend(["mean_ann_vol", "mean_sortino", "mean_ann_return_pct"])
    # Per-agent sharpe columns (sorted for stable order)
    agent_cols = sorted(metrics["agent_sharpe_series"].keys())
    header.extend([f"{a}_sharpe" for a in agent_cols])
    reward_agents = sorted(metrics["agent_total_reward_series"].keys())
    drawdown_agents = sorted(metrics["agent_max_drawdown_series"].keys())
    ann_vol_agents = sorted(metrics["agent_ann_vol_series"].keys())
    sortino_agents = sorted(metrics["agent_sortino_series"].keys())
    ann_return_agents = sorted(metrics["agent_ann_return_series"].keys())
    turnover_agents = sorted(metrics["agent_turnover_series"].keys())
    header.extend([f"{a}_total_reward" for a in reward_agents])
    header.extend([f"{a}_max_drawdown" for a in drawdown_agents])
    header.extend([f"{a}_ann_vol" for a in ann_vol_agents])
    header.extend([f"{a}_sortino" for a in sortino_agents])
    header.extend([f"{a}_ann_return_pct" for a in ann_return_agents])
    header.extend([f"{a}_total_turnover" for a in turnover_agents])
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for i, e in enumerate(epochs):
            row = [
                e,
                metrics["mean_sharpes"][i],
                metrics["min_sharpes"][i],
                metrics["max_sharpes"][i],
                metrics["epoch_times"][i],
                metrics["avg_policy_losses"][i],
                metrics["avg_value_losses"][i],
                metrics["avg_entropies"][i],
            ]
            row.extend(
                [
                    (
                        metrics["mean_ann_vols"][i]
                        if i < len(metrics["mean_ann_vols"])
                        else ""
                    ),
                    (
                        metrics["mean_sortinos"][i]
                        if i < len(metrics["mean_sortinos"])
                        else ""
                    ),
                    (
                        metrics["mean_ann_returns"][i]
                        if i < len(metrics["mean_ann_returns"])
                        else ""
                    ),
                ]
            )
            # per-agent sharpes (pad if series is shorter)
            for a in agent_cols:
                series = metrics["agent_sharpe_series"][a]
                row.append(series[i] if i < len(series) else "")
            for a in reward_agents:
                series = metrics["agent_total_reward_series"][a]
                row.append(series[i] if i < len(series) else "")
            for a in drawdown_agents:
                series = metrics["agent_max_drawdown_series"][a]
                row.append(series[i] if i < len(series) else "")
            for a in ann_vol_agents:
                series = metrics["agent_ann_vol_series"][a]
                row.append(series[i] if i < len(series) else "")
            for a in sortino_agents:
                series = metrics["agent_sortino_series"][a]
                row.append(series[i] if i < len(series) else "")
            for a in ann_return_agents:
                series = metrics["agent_ann_return_series"][a]
                row.append(series[i] if i < len(series) else "")
            for a in turnover_agents:
                series = metrics["agent_turnover_series"][a]
                row.append(series[i] if i < len(series) else "")
            writer.writerow(row)


def save_training_report(
    output_dir: str, metrics: Dict[str, Any], repo_root: str, history_path: str
) -> None:
    """Create a comprehensive report covering prerequisites, process, triggers, and results."""
    ensure_dir(output_dir)
    import re

    epochs = metrics["epochs"]
    mean_sharpes = metrics["mean_sharpes"]
    min_sharpes = metrics["min_sharpes"]
    max_sharpes = metrics["max_sharpes"]
    epoch_times = metrics["epoch_times"]

    if epochs:
        best_idx = get_best_epoch(metrics)
        best_epoch = epochs[best_idx]
        best_mean = mean_sharpes[best_idx]
        best_min = min_sharpes[best_idx]
        best_max = max_sharpes[best_idx]
    else:
        best_idx = -1
        best_epoch = -1
        best_mean = best_min = best_max = float("nan")

    total_time = sum(t for t in epoch_times if t == t)
    avg_time = (
        (total_time / len([t for t in epoch_times if t == t]))
        if epoch_times
        else float("nan")
    )

    checkpoints_dir = os.path.join(
        repo_root, "results", "full_ecosystem", "checkpoints"
    )
    checkpoint_files = []
    checkpoint_epochs = []
    best_model_path = None
    if os.path.isdir(checkpoints_dir):
        for name in sorted(os.listdir(checkpoints_dir)):
            if name.endswith(".pt"):
                checkpoint_files.append(name)
                m = re.match(r"checkpoint_epoch_(\d+)\.pt$", name)
                if m:
                    checkpoint_epochs.append(int(m.group(1)))
                if name == "best_model.pt":
                    best_model_path = name

    report_path = os.path.join(output_dir, "DRL_training_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Phase 4 Multi-Agent DRL Training Report\n\n")

        f.write("## Prerequisites\n\n")
        f.write("- Python 3.11+ (observed: 3.13)\n")
        f.write("- Key packages: torch, numpy, pandas, matplotlib, seaborn\n")
        f.write("- OS: Windows (UTF-8 console recommended)\n")
        f.write(
            "- Data: Intraday and daily price datasets prepared and loadable by `run_full_ecosystem_training.py`\n\n"
        )

        f.write("## Pipeline Overview\n\n")
        f.write(
            "1. Data loading and feature engineering (intraday + daily features).\n"
        )
        f.write(
            "2. Environment initialization: Constraints (±10% limits), T+3 settlement, market impact, trading hours.\n"
        )
        f.write(
            "3. MultiAgentPPO setup: per-agent actors with a shared critic; PPO with clipping, value/entropy terms.\n"
        )
        f.write(
            "4. Training loop: rollouts (steps/epoch), GAE, PPO updates, validation evaluation per epoch.\n\n"
        )

        f.write("## Training Configuration (from artifacts)\n\n")
        f.write(
            "- Epochs observed: {} ({} → {})\n".format(
                len(epochs),
                epochs[0] if epochs else "N/A",
                epochs[-1] if epochs else "N/A",
            )
        )
        f.write(
            "- Average epoch time: {:.2f} minutes\n".format(
                avg_time / 60 if avg_time == avg_time else float("nan")
            )
        )
        f.write(
            "- Total observed time: {:.2f} hours\n\n".format(
                total_time / 3600 if total_time == total_time else float("nan")
            )
        )

        f.write("## Checkpoints & Triggers\n\n")
        f.write(
            "- Best model criterion: highest validation mean Sharpe; saved as `best_model.pt`.\n"
        )
        if best_model_path:
            f.write(
                "  - Best model present. Best epoch (by mean Sharpe in history): {}\n".format(
                    best_epoch
                )
            )
        else:
            f.write(
                "  - Best model file not found; see history for best epoch: {}\n".format(
                    best_epoch
                )
            )
        if checkpoint_files:
            f.write(
                "- Checkpoint files in `{}`:\n".format(
                    os.path.relpath(checkpoints_dir, repo_root)
                )
            )
            for name in checkpoint_files:
                f.write(f"  - {name}\n")
        if checkpoint_epochs:
            f.write(
                "- Epochs with checkpoints detected: {}\n\n".format(
                    sorted(checkpoint_epochs)
                )
            )

        f.write("## Results Summary\n\n")
        f.write("- Best Epoch: {}\n".format(best_epoch))
        f.write(
            "- Mean Sharpe (best): {:.4f}\n".format(
                best_mean if best_mean == best_mean else float("nan")
            )
        )
        f.write(
            "- Min–Max Sharpe (best epoch): {:.4f} – {:.4f}\n".format(
                best_min if best_min == best_min else float("nan"),
                best_max if best_max == best_max else float("nan"),
            )
        )
        f.write("- See `metrics_summary.csv` for per-epoch and per-agent values.\n\n")
        f.write("## Visuals\n\n")
        f.write(
            "- `sharpe_band.png`: Mean validation Sharpe with min–max band; markers for best epoch and checkpoints.\n"
        )
        f.write(
            "- `per_agent_sharpe.png`: Validation Sharpe per agent over epochs with markers.\n"
        )
        f.write("- `epoch_time.png`: Epoch time (sec) with markers.\n")
        f.write(
            "- `losses_entropy.png`: Average policy/value losses and entropy with markers.\n\n"
        )
        f.write("Additional metrics plots (if available):\n\n")
        f.write(
            "- `per_agent_ann_vol.png`: Annualized volatility per agent over epochs.\n"
        )
        f.write("- `per_agent_sortino.png`: Sortino ratio per agent over epochs.\n")
        f.write(
            "- `per_agent_ann_return.png`: Annualized return per agent over epochs.\n"
        )
        f.write(
            "- `per_agent_turnover.png`: Total turnover per agent (validation eval) over epochs.\n\n"
        )

        f.write("## Reproducing Visuals\n\n")
        f.write("Use PowerShell from the repo root:\n\n")
        f.write("```pwsh\n")
        f.write("python code/phase4/analysis/plot_training_results.py\n")
        f.write("```\n")


def _add_epoch_markers(
    ax, epochs: List[int], best_epoch_idx: int, checkpoint_epochs: List[int]
):
    if not epochs:
        return
    best_epoch = epochs[best_epoch_idx] if best_epoch_idx >= 0 else None
    # Best epoch marker
    if best_epoch is not None:
        ax.axvline(
            best_epoch,
            color="#2ca02c",
            linestyle="--",
            alpha=0.8,
            label=f"Best Epoch {best_epoch}",
        )
    # Specific checkpoint epochs
    for ce in checkpoint_epochs:
        if ce in epochs:
            ax.axvline(
                ce, color="#7f7f7f", linestyle=":", alpha=0.7, label=f"Checkpoint {ce}"
            )


def _annotate_best(ax, epochs: List[int], best_idx: int, mean_sharpes: List[float]):
    """Annotate the best epoch point with its mean Sharpe value."""
    if best_idx is None or best_idx < 0 or not epochs:
        return
    x = epochs[best_idx]
    y = mean_sharpes[best_idx]
    if y != y:  # NaN guard
        return
    # Compute a small offset for readability
    y_vals = [v for v in mean_sharpes if v == v]
    if y_vals:
        yr = max(y_vals) - min(y_vals)
    else:
        yr = 1.0
    dy = 0.03 * yr if yr > 0 else 0.05
    ax.plot([x], [y], marker="o", color="#2ca02c")
    ax.annotate(
        f"Best: {y:.4f}",
        xy=(x, y),
        xytext=(x, y + dy),
        textcoords="data",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#2ca02c",
        arrowprops=dict(arrowstyle="-", color="#2ca02c", lw=0.8),
    )


def try_plot(metrics: Dict[str, Any], output_dir: str) -> None:
    ensure_dir(output_dir)
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set(style="whitegrid")

        epochs = metrics["epochs"]
        best_idx = get_best_epoch(metrics)
        checkpoint_epochs = [10, 20]

        # 1) Mean/Min/Max Sharpe over epochs
        plt.figure(figsize=(9, 5))
        plt.plot(epochs, metrics["mean_sharpes"], label="Mean Sharpe", color="#1f77b4")
        plt.fill_between(
            epochs,
            metrics["min_sharpes"],
            metrics["max_sharpes"],
            color="#1f77b4",
            alpha=0.15,
            label="Min–Max Sharpe",
        )
        plt.xlabel("Epoch")
        plt.ylabel("Sharpe")
        plt.title("Validation Sharpe (Mean with Min–Max Band)")
        _add_epoch_markers(plt.gca(), epochs, best_idx, checkpoint_epochs)
        _annotate_best(plt.gca(), epochs, best_idx, metrics["mean_sharpes"])
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "sharpe_band.png"), dpi=150)
        plt.close()

        # 2) Per-agent Sharpe lines
        plt.figure(figsize=(11, 6))
        for agent, series in sorted(metrics["agent_sharpe_series"].items()):
            # Some runs might be shorter; pad with NaN to match epochs length
            y = series + [float("nan")] * (len(epochs) - len(series))
            plt.plot(epochs, y, label=agent, linewidth=1)
        plt.xlabel("Epoch")
        plt.ylabel("Sharpe")
        plt.title("Validation Sharpe per Agent")
        _add_epoch_markers(plt.gca(), epochs, best_idx, checkpoint_epochs)
        # Annotate mean Sharpe at best epoch for context without clutter
        _annotate_best(plt.gca(), epochs, best_idx, metrics["mean_sharpes"])
        plt.legend(ncol=2, fontsize=8)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "per_agent_sharpe.png"), dpi=150)
        plt.close()

        # 2b) Per-agent Annualized Volatility
        if metrics.get("agent_ann_vol_series"):
            plt.figure(figsize=(11, 6))
            for agent, series in sorted(metrics["agent_ann_vol_series"].items()):
                y = series + [float("nan")] * (len(epochs) - len(series))
                plt.plot(epochs, y, label=agent, linewidth=1)
            plt.xlabel("Epoch")
            plt.ylabel("Ann. Volatility")
            plt.title("Annualized Volatility per Agent")
            _add_epoch_markers(plt.gca(), epochs, best_idx, checkpoint_epochs)
            plt.legend(ncol=2, fontsize=8)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "per_agent_ann_vol.png"), dpi=150)
            plt.close()

        # 2c) Per-agent Sortino
        if metrics.get("agent_sortino_series"):
            plt.figure(figsize=(11, 6))
            for agent, series in sorted(metrics["agent_sortino_series"].items()):
                y = series + [float("nan")] * (len(epochs) - len(series))
                plt.plot(epochs, y, label=agent, linewidth=1)
            plt.xlabel("Epoch")
            plt.ylabel("Sortino")
            plt.title("Sortino per Agent")
            _add_epoch_markers(plt.gca(), epochs, best_idx, checkpoint_epochs)
            plt.legend(ncol=2, fontsize=8)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "per_agent_sortino.png"), dpi=150)
            plt.close()

        # 2d) Per-agent Annualized Return
        if metrics.get("agent_ann_return_series"):
            plt.figure(figsize=(11, 6))
            for agent, series in sorted(metrics["agent_ann_return_series"].items()):
                y = series + [float("nan")] * (len(epochs) - len(series))
                plt.plot(epochs, y, label=agent, linewidth=1)
            plt.xlabel("Epoch")
            plt.ylabel("Ann. Return (%)")
            plt.title("Annualized Return per Agent")
            _add_epoch_markers(plt.gca(), epochs, best_idx, checkpoint_epochs)
            plt.legend(ncol=2, fontsize=8)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "per_agent_ann_return.png"), dpi=150)
            plt.close()

        # 2e) Per-agent Total Turnover (validation eval)
        if metrics.get("agent_turnover_series"):
            plt.figure(figsize=(11, 6))
            for agent, series in sorted(metrics["agent_turnover_series"].items()):
                y = series + [float("nan")] * (len(epochs) - len(series))
                plt.plot(epochs, y, label=agent, linewidth=1)
            plt.xlabel("Epoch")
            plt.ylabel("Total Turnover")
            plt.title("Total Turnover per Agent (Validation Eval)")
            _add_epoch_markers(plt.gca(), epochs, best_idx, checkpoint_epochs)
            plt.legend(ncol=2, fontsize=8)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "per_agent_turnover.png"), dpi=150)
            plt.close()

        # 3) Epoch time
        plt.figure(figsize=(9, 4))
        plt.plot(epochs, metrics["epoch_times"], marker="o", color="#ff7f0e")
        plt.xlabel("Epoch")
        plt.ylabel("Seconds")
        plt.title("Epoch Time")
        _add_epoch_markers(plt.gca(), epochs, best_idx, checkpoint_epochs)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "epoch_time.png"), dpi=150)
        plt.close()

        # 4) Average losses and entropy
        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(
            epochs,
            metrics["avg_policy_losses"],
            color="#2ca02c",
            label="Avg Policy Loss",
        )
        ax1.plot(
            epochs, metrics["avg_value_losses"], color="#d62728", label="Avg Value Loss"
        )
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Loss")
        ax2 = ax1.twinx()
        ax2.plot(
            epochs,
            metrics["avg_entropies"],
            color="#9467bd",
            alpha=0.6,
            label="Avg Entropy",
        )
        ax2.set_ylabel("Entropy")
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        _add_epoch_markers(ax1, epochs, best_idx, checkpoint_epochs)
        ax1.legend(lines + lines2, labels + labels2, loc="upper right")
        plt.title("Training Losses and Entropy (Averages across Agents)")
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, "losses_entropy.png"), dpi=150)
        plt.close(fig)

    except Exception as e:
        # Fallback: write a CSV-like text if plotting libs are missing
        txt_path = os.path.join(output_dir, "plots_not_generated.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Plots could not be generated. Reason:\n")
            f.write(str(e) + "\n\n")
            f.write("Install matplotlib and seaborn to enable plotting.\n")


def main():
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    default_history = os.path.join(
        repo_root,
        "results",
        "full_ecosystem",
        "checkpoints",
        "training_history.json",
    )
    default_output = os.path.join(repo_root, "results", "full_ecosystem", "plots")

    # Allow overrides: plot_training_results.py <history_json> <output_dir>
    history_path = sys.argv[1] if len(sys.argv) > 1 else default_history
    output_dir = sys.argv[2] if len(sys.argv) > 2 else default_output

    if not os.path.isfile(history_path):
        print(f"History file not found: {history_path}")
        sys.exit(1)

    ensure_dir(output_dir)
    history = load_history(history_path)
    metrics = extract_metrics(history)
    save_summary_markdown(output_dir, metrics)
    save_metrics_csv(output_dir, metrics)
    try_plot(metrics, output_dir)
    # Extended narrative report
    save_training_report(output_dir, metrics, repo_root, history_path)
    print(f"Summary and plots saved to: {output_dir}")


if __name__ == "__main__":
    main()
