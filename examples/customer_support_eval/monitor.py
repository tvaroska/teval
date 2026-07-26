#!/usr/bin/env python3
"""
Real-time Monitoring for Evaluation Campaign

Watches evaluation progress and alerts on issues:
- Evaluator activity and completion rates
- Suspicious patterns (too fast, all pass)
- Overall campaign progress

Usage:
    python monitor.py                   # Check once and exit
    python monitor.py --watch           # Continuous monitoring
    python monitor.py --watch --interval 60  # Check every 60 seconds
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from rubric import rubric


def load_session_data(storage_dir: str = "./evaluation_results") -> dict:
    """Load all session data from storage directory."""
    storage_path = Path(storage_dir)
    sessions_path = storage_path / "sessions"

    if not sessions_path.exists():
        return {"sessions": [], "items": {}}

    data = {
        "sessions": [],
        "items": {},
        "evaluators": {}
    }

    for session_dir in sessions_path.iterdir():
        if session_dir.is_dir():
            latest_file = session_dir / "latest.json"
            if latest_file.exists():
                with open(latest_file) as f:
                    session_data = json.load(f)
                    data["sessions"].append(session_data)

                    # Track by evaluator
                    evaluator = session_data.get("metadata", {}).get(
                        "evaluator", "anonymous"
                    )
                    if evaluator not in data["evaluators"]:
                        data["evaluators"][evaluator] = []
                    data["evaluators"][evaluator].append(session_data)

                    # Track by item
                    item_id = session_data.get("item_id")
                    if item_id:
                        if item_id not in data["items"]:
                            data["items"][item_id] = []
                        data["items"][item_id].append(session_data)

    return data


def check_evaluator_quality(evaluator_data: list) -> list:
    """Check for quality issues with an evaluator's work."""
    issues = []

    if len(evaluator_data) < 5:
        return issues  # Not enough data to check

    # Check for suspiciously high pass rate
    all_pass = 0
    for eval_item in evaluator_data:
        result = eval_item.get("evaluation", {})
        if all(result.get(m.id, False) for m in rubric.metrics):
            all_pass += 1

    pass_rate = all_pass / len(evaluator_data)
    if pass_rate > 0.95:
        issues.append(f"Suspiciously high pass rate: {pass_rate:.1%}")

    # Check for fast completion times
    timestamps = []
    for eval_item in evaluator_data:
        ts = eval_item.get("timestamp")
        if ts:
            try:
                timestamps.append(datetime.fromisoformat(ts))
            except (ValueError, TypeError):
                pass

    if len(timestamps) >= 2:
        timestamps.sort()
        intervals = [
            (timestamps[i+1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
        ]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval < 15:  # Less than 15 seconds between items
            issues.append(f"Evaluating too quickly: {avg_interval:.0f}s average per item")

    return issues


def display_progress(data: dict, total_items: int = 500):
    """Display evaluation progress dashboard."""
    n_sessions = len(data["sessions"])
    n_items = len(data["items"])
    n_evaluators = len(data["evaluators"])

    progress = n_items / total_items if total_items > 0 else 0
    bar_width = 50
    filled = int(bar_width * progress)

    print()
    print("=" * 60)
    print(f"Evaluation Progress - {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)
    print()
    print(f"Items Evaluated: {n_items}/{total_items} ({progress:.1%})")
    print(f"[{'█' * filled}{'░' * (bar_width - filled)}]")
    print()
    print(f"Total Evaluations: {n_sessions}")
    print(f"Active Evaluators: {n_evaluators}")
    print()

    # Per-evaluator breakdown
    if data["evaluators"]:
        print("Evaluator Status:")
        print("-" * 40)

        for evaluator, evals in sorted(
            data["evaluators"].items(),
            key=lambda x: -len(x[1])
        ):
            count = len(evals)
            last_active = None
            for e in evals:
                ts = e.get("timestamp")
                if ts:
                    try:
                        last_active = datetime.fromisoformat(ts)
                    except (ValueError, TypeError):
                        pass

            active_str = ""
            if last_active:
                delta = datetime.now() - last_active
                if delta.total_seconds() < 300:  # Active in last 5 min
                    active_str = " [ACTIVE]"
                elif delta.total_seconds() < 3600:  # Last hour
                    active_str = f" [{int(delta.total_seconds()/60)}m ago]"

            # Check for quality issues
            issues = check_evaluator_quality(evals)
            issue_str = f" ⚠️ {issues[0]}" if issues else ""

            print(f"  {evaluator}: {count} items{active_str}{issue_str}")

    print()

    # Quality summary
    print("Quality Summary:")
    print("-" * 40)

    passed = 0
    failed_mandatory = 0
    failed_quality = 0

    for session in data["sessions"]:
        result = session.get("evaluation", {})

        mandatory_pass = all(
            result.get(m.id, False)
            for m in rubric.mandatory_metrics
        )

        quality_score = sum(
            1 for m in rubric.cumulative_metrics
            if result.get(m.id, False)
        )
        quality_pass = quality_score >= rubric.passing_score_threshold

        if mandatory_pass and quality_pass:
            passed += 1
        elif not mandatory_pass:
            failed_mandatory += 1
        else:
            failed_quality += 1

    total = len(data["sessions"])
    if total > 0:
        print(f"  Pass Rate: {passed/total:.1%}")
        print(f"    Passed: {passed}")
        print(f"    Failed (Mandatory): {failed_mandatory}")
        print(f"    Failed (Quality): {failed_quality}")

        if failed_mandatory > 0:
            print()
            print("  ⚠️ WARNING: Mandatory failures detected - safety review needed")

    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Monitor evaluation campaign progress"
    )
    parser.add_argument(
        "-d", "--directory",
        default="./evaluation_results",
        help="Storage directory to monitor"
    )
    parser.add_argument(
        "-n", "--total-items",
        type=int,
        default=500,
        help="Total expected items (for progress calculation)"
    )
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Continuous monitoring mode"
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=30,
        help="Check interval in seconds (with --watch)"
    )

    args = parser.parse_args()

    if args.watch:
        print(f"Watching {args.directory} every {args.interval} seconds...")
        print("Press Ctrl+C to stop")

        try:
            while True:
                # Clear screen (works on most terminals)
                print("\033[2J\033[H", end="")

                data = load_session_data(args.directory)
                display_progress(data, args.total_items)

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    else:
        data = load_session_data(args.directory)
        display_progress(data, args.total_items)


if __name__ == "__main__":
    main()
