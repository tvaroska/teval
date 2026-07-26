#!/usr/bin/env python3
"""
Analyze Customer Support Evaluation Results

Generates comprehensive analysis including:
- Overall pass rates
- Per-metric statistics
- Problem patterns
- Production readiness assessment
- Exportable reports

Usage:
    python analyze.py                           # Analyze default directory
    python analyze.py -d ./my_results           # Analyze specific directory
    python analyze.py --export excel            # Export to Excel
    python analyze.py --export csv              # Export to CSV
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rubric import rubric


def load_evaluations(storage_dir: str = "./evaluation_results") -> list[dict]:
    """
    Load all evaluations from storage directory.

    Returns list of evaluation data dicts.
    """
    storage_path = Path(storage_dir)
    sessions_path = storage_path / "sessions"

    if not sessions_path.exists():
        print(f"No evaluations found in {storage_dir}")
        return []

    evaluations = []

    # Load from session directories
    for session_dir in sessions_path.iterdir():
        if session_dir.is_dir():
            latest_file = session_dir / "latest.json"
            if latest_file.exists():
                with open(latest_file) as f:
                    data = json.load(f)
                    evaluations.append(data)

    # Also check for item-level evaluations
    items_path = storage_path / "items"
    if items_path.exists():
        for item_file in items_path.glob("*.json"):
            with open(item_file) as f:
                data = json.load(f)
                if isinstance(data, list):
                    evaluations.extend(data)
                else:
                    evaluations.append(data)

    return evaluations


def analyze_results(evaluations: list[dict]) -> dict:
    """
    Comprehensive analysis of evaluation results.

    Returns analysis dict with statistics and insights.
    """
    if not evaluations:
        return {"error": "No evaluations to analyze"}

    analysis = {
        "summary": {
            "total_evaluations": len(evaluations),
            "analyzed_at": datetime.now().isoformat()
        },
        "overall": {
            "passed": 0,
            "failed_mandatory": 0,
            "failed_quality": 0
        },
        "metrics": {},
        "by_category": {},
        "evaluators": {},
        "problem_items": []
    }

    # Analyze each evaluation
    for eval_data in evaluations:
        result = eval_data.get("evaluation", eval_data.get("results", {}))
        metadata = eval_data.get("metadata", {})
        item_id = eval_data.get("item_id", metadata.get("item_id", "unknown"))

        # Check mandatory metrics
        mandatory_pass = all(
            result.get(m.id, False)
            for m in rubric.mandatory_metrics
        )

        # Check quality threshold
        quality_score = sum(
            1 for m in rubric.cumulative_metrics
            if result.get(m.id, False)
        )
        quality_pass = quality_score >= rubric.passing_score_threshold

        # Overall pass
        passes = mandatory_pass and quality_pass

        # Update counts
        if passes:
            analysis["overall"]["passed"] += 1
        elif not mandatory_pass:
            analysis["overall"]["failed_mandatory"] += 1
            # Track problem items
            failed_metrics = [
                m.id for m in rubric.mandatory_metrics
                if not result.get(m.id, False)
            ]
            analysis["problem_items"].append({
                "item_id": item_id,
                "type": "mandatory_failure",
                "failed_metrics": failed_metrics
            })
        else:
            analysis["overall"]["failed_quality"] += 1

        # Per-metric stats
        for metric in rubric.metrics:
            if metric.id not in analysis["metrics"]:
                analysis["metrics"][metric.id] = {
                    "passed": 0,
                    "failed": 0,
                    "mandatory": metric.mandatory
                }

            if result.get(metric.id, False):
                analysis["metrics"][metric.id]["passed"] += 1
            else:
                analysis["metrics"][metric.id]["failed"] += 1

        # By category
        category = metadata.get("category", "unknown")
        if category not in analysis["by_category"]:
            analysis["by_category"][category] = {
                "total": 0,
                "passed": 0
            }
        analysis["by_category"][category]["total"] += 1
        if passes:
            analysis["by_category"][category]["passed"] += 1

        # By evaluator
        evaluator = metadata.get("evaluator", "anonymous")
        if evaluator not in analysis["evaluators"]:
            analysis["evaluators"][evaluator] = {
                "total": 0,
                "completed": 0,
                "last_active": None
            }
        analysis["evaluators"][evaluator]["total"] += 1
        analysis["evaluators"][evaluator]["completed"] += 1
        analysis["evaluators"][evaluator]["last_active"] = eval_data.get(
            "timestamp",
            metadata.get("timestamp")
        )

    # Calculate pass rates
    total = analysis["summary"]["total_evaluations"]
    analysis["overall"]["pass_rate"] = analysis["overall"]["passed"] / total
    analysis["overall"]["mandatory_fail_rate"] = (
        analysis["overall"]["failed_mandatory"] / total
    )
    analysis["overall"]["quality_fail_rate"] = (
        analysis["overall"]["failed_quality"] / total
    )

    # Metric pass rates
    for metric_id, stats in analysis["metrics"].items():
        total_metric = stats["passed"] + stats["failed"]
        stats["pass_rate"] = stats["passed"] / total_metric if total_metric > 0 else 0

    # Category pass rates
    for category, stats in analysis["by_category"].items():
        stats["pass_rate"] = stats["passed"] / stats["total"] if stats["total"] > 0 else 0

    return analysis


def generate_report(analysis: dict) -> str:
    """Generate human-readable report from analysis."""
    if "error" in analysis:
        return f"Error: {analysis['error']}"

    total = analysis["summary"]["total_evaluations"]
    overall = analysis["overall"]

    report = f"""
{'=' * 60}
CUSTOMER SUPPORT EVALUATION REPORT
{'=' * 60}

Generated: {analysis['summary']['analyzed_at']}
Total Evaluations: {total}

OVERALL RESULTS
{'-' * 40}
{'PASS' if overall['pass_rate'] >= 0.8 else 'FAIL'}: {overall['pass_rate']:.1%} pass rate

  Passed:            {overall['passed']:4d} ({overall['pass_rate']:.1%})
  Failed (Mandatory): {overall['failed_mandatory']:4d} ({overall['mandatory_fail_rate']:.1%})
  Failed (Quality):   {overall['failed_quality']:4d} ({overall['quality_fail_rate']:.1%})

METRIC-LEVEL ANALYSIS
{'-' * 40}

Mandatory Metrics (ALL must pass):
"""

    for metric in rubric.mandatory_metrics:
        stats = analysis["metrics"].get(metric.id, {})
        pass_rate = stats.get("pass_rate", 0)
        status = "CRITICAL" if pass_rate < 1.0 else "OK"
        report += f"  [{status:>8}] {metric.id}: {pass_rate:.1%}\n"

    report += "\nQuality Metrics (need {}/{}):\n".format(
        rubric.passing_score_threshold,
        len(rubric.cumulative_metrics)
    )

    for metric in rubric.cumulative_metrics:
        stats = analysis["metrics"].get(metric.id, {})
        pass_rate = stats.get("pass_rate", 0)
        status = "LOW" if pass_rate < 0.7 else "OK"
        report += f"  [{status:>8}] {metric.id}: {pass_rate:.1%}\n"

    if analysis["by_category"]:
        report += f"\nBY CATEGORY\n{'-' * 40}\n"
        for category, stats in sorted(
            analysis["by_category"].items(),
            key=lambda x: x[1]["pass_rate"]
        ):
            report += f"  {category}: {stats['pass_rate']:.1%} ({stats['passed']}/{stats['total']})\n"

    if analysis["evaluators"]:
        report += f"\nEVALUATOR ACTIVITY\n{'-' * 40}\n"
        for evaluator, stats in analysis["evaluators"].items():
            report += f"  {evaluator}: {stats['completed']} evaluations\n"

    if analysis["problem_items"]:
        report += f"\nPROBLEM ITEMS (Top 5)\n{'-' * 40}\n"
        for item in analysis["problem_items"][:5]:
            report += f"  {item['item_id']}: {item['type']} - {', '.join(item['failed_metrics'])}\n"

    # Production readiness
    report += f"\nPRODUCTION READINESS\n{'-' * 40}\n"

    mandatory_ok = overall["mandatory_fail_rate"] == 0
    quality_ok = overall["pass_rate"] >= 0.8

    report += f"  [{'OK' if mandatory_ok else 'FAIL'}] Mandatory metrics: {'100% pass' if mandatory_ok else 'Failures detected'}\n"
    report += f"  [{'OK' if quality_ok else 'FAIL'}] Quality threshold: {overall['pass_rate']:.1%} >= 80%\n"

    if mandatory_ok and quality_ok:
        report += "\n  READY FOR PRODUCTION\n"
    else:
        report += "\n  NOT READY - Address failures first\n"
        if not mandatory_ok:
            report += "    - Fix mandatory metric failures (safety issues)\n"
        if not quality_ok:
            report += "    - Improve quality to meet 80% threshold\n"

    report += "\n" + "=" * 60

    return report


def export_to_excel(analysis: dict, output_file: str = "evaluation_report.xlsx"):
    """Export analysis to Excel workbook."""
    try:
        import pandas as pd
    except ImportError:
        print("pandas required for Excel export: pip install pandas openpyxl")
        return

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_df = pd.DataFrame([{
            "Metric": "Total Evaluations",
            "Value": analysis["summary"]["total_evaluations"]
        }, {
            "Metric": "Pass Rate",
            "Value": f"{analysis['overall']['pass_rate']:.1%}"
        }, {
            "Metric": "Mandatory Failures",
            "Value": analysis["overall"]["failed_mandatory"]
        }, {
            "Metric": "Quality Failures",
            "Value": analysis["overall"]["failed_quality"]
        }])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Metrics sheet
        metrics_data = []
        for metric_id, stats in analysis["metrics"].items():
            metrics_data.append({
                "Metric": metric_id,
                "Type": "Mandatory" if stats["mandatory"] else "Quality",
                "Passed": stats["passed"],
                "Failed": stats["failed"],
                "Pass Rate": f"{stats['pass_rate']:.1%}"
            })
        metrics_df = pd.DataFrame(metrics_data)
        metrics_df.to_excel(writer, sheet_name="Metrics", index=False)

        # Categories sheet
        if analysis["by_category"]:
            cat_data = [
                {"Category": cat, **stats}
                for cat, stats in analysis["by_category"].items()
            ]
            cat_df = pd.DataFrame(cat_data)
            cat_df.to_excel(writer, sheet_name="Categories", index=False)

        # Problem items sheet
        if analysis["problem_items"]:
            problems_df = pd.DataFrame(analysis["problem_items"])
            problems_df.to_excel(writer, sheet_name="Problems", index=False)

    print(f"Exported to: {output_file}")


def export_to_csv(analysis: dict, output_dir: str = "./"):
    """Export analysis to CSV files."""
    import csv
    output_path = Path(output_dir)

    # Metrics CSV
    metrics_file = output_path / "metrics_analysis.csv"
    with open(metrics_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "metric", "type", "passed", "failed", "pass_rate"
        ])
        writer.writeheader()
        for metric_id, stats in analysis["metrics"].items():
            writer.writerow({
                "metric": metric_id,
                "type": "mandatory" if stats["mandatory"] else "quality",
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": f"{stats['pass_rate']:.4f}"
            })

    print(f"Exported to: {metrics_file}")

    # Summary CSV
    summary_file = output_path / "summary.csv"
    with open(summary_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["total_evaluations", analysis["summary"]["total_evaluations"]])
        writer.writerow(["pass_rate", f"{analysis['overall']['pass_rate']:.4f}"])
        writer.writerow(["mandatory_failures", analysis["overall"]["failed_mandatory"]])
        writer.writerow(["quality_failures", analysis["overall"]["failed_quality"]])

    print(f"Exported to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze customer support evaluation results"
    )
    parser.add_argument(
        "-d", "--directory",
        default="./evaluation_results",
        help="Directory containing evaluation results"
    )
    parser.add_argument(
        "--export",
        choices=["excel", "csv", "json"],
        help="Export format (in addition to text report)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file/directory for export"
    )

    args = parser.parse_args()

    # Load evaluations
    print(f"Loading evaluations from: {args.directory}")
    evaluations = load_evaluations(args.directory)

    if not evaluations:
        print("No evaluations found. Run the evaluation app first.")
        return

    print(f"Loaded {len(evaluations)} evaluations")

    # Analyze
    analysis = analyze_results(evaluations)

    # Generate and print report
    report = generate_report(analysis)
    print(report)

    # Save report
    report_file = Path(args.directory) / f"report_{datetime.now():%Y%m%d_%H%M%S}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_file}")

    # Export if requested
    if args.export == "excel":
        output = args.output or "evaluation_report.xlsx"
        export_to_excel(analysis, output)
    elif args.export == "csv":
        output = args.output or "./"
        export_to_csv(analysis, output)
    elif args.export == "json":
        output = args.output or "analysis.json"
        with open(output, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"Exported to: {output}")


if __name__ == "__main__":
    main()
