#!/usr/bin/env python3
"""
CodeBench - turns Harbor results into a table and a chart.

Usage:
    python analyze.py jobs            # 'jobs' = the folder Harbor wrote its results into

It looks for every reward.txt (or reward.json) under that folder, works out which
task each one belongs to from the folder name, and prints:
    - pass rate per task, per type and per difficulty
It also writes:
    results/summary.csv, results/pass_rate.png, results/failure_notes.md

If your Harbor results use a different layout, open one trial folder, find where the
reward is stored, and adjust find_rewards() below (it is short).
"""
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def _as_finite_number(value):
    """Return float(value) if value is a finite int/float (excluding bool), else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    num = float(value)
    return num if math.isfinite(num) else None


def read_reward(path):
    """Parse a reward.txt or reward.json file into a finite float, raising ValueError on bad input."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("empty reward file")
    if path.suffix == ".json":
        data = json.loads(text)
        if not isinstance(data, dict) or not data:
            raise ValueError("reward JSON must be a non-empty object")
        if "reward" in data:
            num = _as_finite_number(data["reward"])
            if num is None:
                raise ValueError("invalid 'reward' value")
            return num
        values = [_as_finite_number(v) for v in data.values()]
        numeric = [v for v in values if v is not None]
        if not numeric:
            raise ValueError("no numeric reward values in JSON")
        return sum(numeric)
    num = float(text)
    if not math.isfinite(num):
        raise ValueError("non-finite reward value")
    return num


def _match_task_id(rel_path, task_ids):
    """Return the longest matching task_id in a relative POSIX path, or None."""
    label = rel_path.as_posix()
    matches = [tid for tid in task_ids if tid in label]
    return max(matches, key=len) if matches else None


def collect_rewards(root, task_ids):
    """Scan root for reward files, returning ({task_id: [reward, ...]}, [warning, ...])."""
    rewards = defaultdict(list)
    warnings = []
    by_dir = defaultdict(list)
    for name in ("reward.txt", "reward.json"):
        for file in sorted(root.rglob(name)):
            by_dir[file.parent].append(file)

    for folder in sorted(by_dir):
        candidates = by_dir[folder]
        task_id = _match_task_id(folder.relative_to(root), task_ids)
        if not task_id:
            continue
        parsed = False
        last_err = None
        for candidate in candidates:
            try:
                rewards[task_id].append(read_reward(candidate))
                parsed = True
                break
            except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
                last_err = (candidate, exc)
        if not parsed and last_err is not None:
            warnings.append("could not read %s (%s)" % (last_err[0], last_err[1]))
    return rewards, warnings


def find_rewards(root, task_ids):
    """Returns {task_id: [reward, reward, ...]} (one number per run)."""
    rewards, _ = collect_rewards(root, task_ids)
    return rewards


def passed_count(values):
    return sum(1 for v in values if v >= 1)


def percent(values):
    return 100.0 * passed_count(values) / len(values) if values else 0.0


def group(meta, rewards, key):
    groups = defaultdict(list)
    for item in meta:
        groups[item[key]].extend(rewards.get(item["id"], []))
    return groups


def _resolve_metadata():
    cwd_meta = Path("tasks_metadata.json")
    if cwd_meta.exists():
        return cwd_meta
    return SCRIPT_DIR / "tasks_metadata.json"


def _save_chart(by_type, by_level, out_path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(Install matplotlib to get the chart:  pip install matplotlib)")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    panels = [
        (axes[0], by_type, "Pass rate by task type"),
        (axes[1], by_level, "Pass rate by difficulty"),
    ]
    for ax, series, title in panels:
        labels = list(series)
        values = list(series.values())
        bars = ax.bar(labels, values)
        ax.set_title(title)
        ax.set_ylim(0, 110)
        ax.set_ylabel("% passed")
        ax.tick_params(axis="x", rotation=15)
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + 2,
                "%.0f%%" % val,
                ha="center",
                va="bottom",
                fontsize=9,
            )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print("\nChart saved: %s" % out_path)


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("jobs")
    meta_path = _resolve_metadata()
    if not meta_path.exists():
        sys.exit("Metadata file not found: %s" % meta_path)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit("Could not read %s: %s" % (meta_path, exc))

    if not root.exists() or not root.is_dir():
        sys.exit("Results folder not found: %s" % root)

    rewards, warnings = collect_rewards(root, [m["id"] for m in meta])
    for warning in warnings:
        print("Warning:", warning)
    if not rewards:
        sys.exit("No valid reward files found under %s. Check the folder name and layout." % root)

    Path("results").mkdir(exist_ok=True)
    rows = []
    all_values = []
    print("%-28s %-14s %-8s %s" % ("task", "type", "level", "pass rate"))
    for item in meta:
        values = rewards.get(item["id"], [])
        all_values.extend(values)
        passed = passed_count(values)
        rate = percent(values)
        rows.append([item["id"], item["type"], item["difficulty"], len(values), passed, round(rate, 1)])
        shown = "%.0f%% (%d/%d)" % (rate, passed, len(values)) if values else "not run"
        print("%-28s %-14s %-8s %s" % (item["id"], item["type"], item["difficulty"], shown))

    with open("results/summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["task", "type", "difficulty", "runs", "passed", "pass_rate_percent"])
        writer.writerows(rows)

    by_type = {k: percent(v) for k, v in group(meta, rewards, "type").items() if v}
    order = ["easy", "medium", "hard"]
    raw_level = group(meta, rewards, "difficulty")
    by_level = {k: percent(raw_level[k]) for k in order if raw_level.get(k)}

    print("\nOverall pass rate:       %.1f%% (%d/%d runs)" % (
        percent(all_values), passed_count(all_values), len(all_values)
    ))
    print("Pass rate by type:       ", {k: "%.0f%%" % v for k, v in by_type.items()})
    print("Pass rate by difficulty: ", {k: "%.0f%%" % v for k, v in by_level.items()})

    failed = [r[0] for r in rows if r[3] and r[5] < 100]
    notes = [
        "# Failure notes",
        "",
        "For each task below, open the AI's attempt and write WHY it failed",
        "(missed an edge case / misread the instruction / wrong logic / my test was unfair).",
        "",
    ]
    if failed:
        notes += ["## %s\n- Why it failed: \n- Was the task fair? \n" % t for t in failed]
    else:
        notes.append("_No failed tasks in this run._\n")
    Path("results/failure_notes.md").write_text("\n".join(notes), encoding="utf-8")

    _save_chart(by_type, by_level, Path("results/pass_rate.png"))
    print("Saved: results/summary.csv and results/failure_notes.md")


if __name__ == "__main__":
    main()