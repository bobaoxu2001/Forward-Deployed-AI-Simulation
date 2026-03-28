"""Evaluation harness: batch run across all cases, compute metrics, generate report.

Usage:
    python -m eval.run_eval                          # from SQLite DB
    python -m eval.run_eval --cases data/cases       # from case files + mock pipeline
    python -m eval.run_eval --report data/eval/report.md  # save markdown report
"""
import json
import sys
import time
from pathlib import Path

from pipeline.schemas import CaseBundle, ExtractionOutput
from pipeline.loaders import load_all_cases
from pipeline.normalize import normalize_case
from pipeline.extract import extract_case, MockProvider
from pipeline.validate import validate_extraction, check_evidence_present
from pipeline.gate import compute_gate_decision
from eval.metrics import compute_all_metrics
from eval.failure_modes import tag_failure_modes, summarize_failure_modes, FailureTag


def run_eval_from_files(
    cases_dir: str = "data/cases",
    use_mock: bool = True,
) -> dict:
    """Run full evaluation from case bundle files.

    Loads cases, runs extraction (mock by default), validates,
    gates, detects failure modes, and computes all metrics.

    Returns the full eval results dict.
    """
    cases = load_all_cases(cases_dir)
    if not cases:
        print(f"No cases found in {cases_dir}")
        return {}

    print(f"Running evaluation on {len(cases)} cases...")

    provider = MockProvider() if use_mock else None
    case_dicts = []
    extraction_dicts = []
    all_failure_tags: list[FailureTag] = []
    validation_results = []
    gate_decisions = []

    for i, case in enumerate(cases):
        case = normalize_case(case)
        case_dict = case.to_dict()
        case_dicts.append(case_dict)

        # Extract
        extraction, metadata = extract_case(case, provider=provider)
        ext_dict = extraction.to_dict()
        ext_dict["case_id"] = case.case_id  # attach for tracking
        extraction_dicts.append(ext_dict)

        # Validate
        valid, errors = validate_extraction(ext_dict)
        validation_results.append((valid, errors))

        # Gate
        gate = compute_gate_decision(ext_dict)
        gate_decisions.append(gate)

        # Failure modes
        tags = tag_failure_modes(ext_dict, case_dict)
        all_failure_tags.extend(tags)

    # Compute metrics
    metrics = compute_all_metrics(extraction_dicts, case_dicts)

    # Failure mode summary
    failure_summary = summarize_failure_modes(all_failure_tags)

    # Gate distribution
    auto_count = sum(1 for g in gate_decisions if g["route"] == "auto")
    review_count = sum(1 for g in gate_decisions if g["route"] == "review")

    # Reason code distribution
    from collections import Counter
    reason_code_counts = Counter()
    for g in gate_decisions:
        for code in g.get("review_reason_codes", []):
            reason_code_counts[code] += 1

    results = {
        "timestamp": time.time(),
        "total_cases": len(cases),
        "metrics": metrics,
        "failure_modes": failure_summary,
        "gate_distribution": {
            "auto": auto_count,
            "review": review_count,
        },
        "review_reason_codes": dict(reason_code_counts),
        "validation_pass_count": sum(1 for v, _ in validation_results if v),
        "validation_fail_count": sum(1 for v, _ in validation_results if not v),
    }

    return results


def run_eval_from_db(db_path: str = "data/processed/results.db") -> dict:
    """Run evaluation from SQLite database results.

    Reads stored extractions and cases, computes metrics and failure modes.
    """
    from pipeline.storage import get_all_extractions, _get_connection

    db = Path(db_path)
    if not db.exists():
        print(f"Database not found: {db_path}")
        return {}

    conn = _get_connection(db)
    try:
        # Load cases
        case_rows = conn.execute("SELECT * FROM cases").fetchall()
        case_dicts = [dict(row) for row in case_rows]

        # Load extractions
        ext_rows = conn.execute("SELECT * FROM extractions").fetchall()
        extraction_dicts = []
        for row in ext_rows:
            d = dict(row)
            # Parse JSON fields back
            for field in ("next_best_actions", "evidence_quotes", "gate_reasons", "review_reason_codes"):
                if d.get(field) and isinstance(d[field], str):
                    try:
                        d[field] = json.loads(d[field])
                    except json.JSONDecodeError:
                        pass
            extraction_dicts.append(d)
    finally:
        conn.close()

    if not extraction_dicts:
        print("No extractions found in database")
        return {}

    print(f"Running evaluation on {len(extraction_dicts)} extractions from DB...")

    # Compute metrics
    metrics = compute_all_metrics(extraction_dicts, case_dicts)

    # Failure modes
    all_tags = []
    case_map = {c.get("case_id"): c for c in case_dicts}
    for ext in extraction_dicts:
        case = case_map.get(ext.get("case_id"), {})
        tags = tag_failure_modes(ext, case)
        all_tags.extend(tags)

    failure_summary = summarize_failure_modes(all_tags)

    # Gate distribution from stored data
    auto_count = sum(1 for e in extraction_dicts if e.get("gate_route") == "auto")
    review_count = sum(1 for e in extraction_dicts if e.get("gate_route") == "review")

    from collections import Counter
    reason_code_counts = Counter()
    for e in extraction_dicts:
        codes = e.get("review_reason_codes", [])
        if isinstance(codes, str):
            try:
                codes = json.loads(codes)
            except json.JSONDecodeError:
                codes = []
        for code in codes:
            reason_code_counts[code] += 1

    return {
        "timestamp": time.time(),
        "total_cases": len(extraction_dicts),
        "metrics": metrics,
        "failure_modes": failure_summary,
        "gate_distribution": {"auto": auto_count, "review": review_count},
        "review_reason_codes": dict(reason_code_counts),
    }


# --- Markdown report ---

def generate_report(results: dict) -> str:
    """Generate a markdown evaluation report."""
    if not results:
        return "# Evaluation Report\n\nNo results to report.\n"

    lines = []
    lines.append("# Evaluation Report")
    lines.append("")
    lines.append(f"**Total cases evaluated:** {results.get('total_cases', 0)}")
    lines.append("")

    # Metrics table
    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value | Target | Pass |")
    lines.append("|--------|-------|--------|------|")

    metrics = results.get("metrics", {})
    for name, info in metrics.items():
        if name == "total_cases":
            continue
        if isinstance(info, dict):
            value = info.get("value", 0)
            target = info.get("target")
            passed = info.get("pass")

            value_str = f"{value:.2%}" if isinstance(value, float) else str(value)
            target_str = f"{target:.2%}" if target is not None else "—"
            pass_str = "PASS" if passed is True else ("FAIL" if passed is False else "—")

            lines.append(f"| {name} | {value_str} | {target_str} | {pass_str} |")

    lines.append("")

    # Gate distribution
    gate = results.get("gate_distribution", {})
    lines.append("## Gate Distribution")
    lines.append("")
    lines.append(f"- Auto-routed: {gate.get('auto', 0)}")
    lines.append(f"- Review-routed: {gate.get('review', 0)}")
    lines.append("")

    # Review reason codes
    reason_codes = results.get("review_reason_codes", {})
    if reason_codes:
        lines.append("## Review Reason Codes")
        lines.append("")
        lines.append("| Reason Code | Count |")
        lines.append("|-------------|-------|")
        for code, count in sorted(reason_codes.items(), key=lambda x: -x[1]):
            lines.append(f"| {code} | {count} |")
        lines.append("")

    # Failure modes
    fm = results.get("failure_modes", {})
    lines.append("## Failure Modes")
    lines.append("")
    lines.append(f"**Total failures detected:** {fm.get('total_failures', 0)}")
    lines.append(f"**Cases affected:** {fm.get('affected_cases', 0)}")
    lines.append("")

    by_mode = fm.get("by_mode", {})
    lines.append("| Mode | Count | Examples |")
    lines.append("|------|-------|----------|")
    for mode, data in by_mode.items():
        count = data.get("count", 0)
        examples = data.get("examples", [])
        if examples:
            ex_str = "; ".join(
                f"`{e['case_id']}`: {e['detail'][:60]}" for e in examples[:2]
            )
        else:
            ex_str = "—"
        lines.append(f"| {mode} | {count} | {ex_str} |")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by eval/run_eval.py*")

    return "\n".join(lines)


# --- CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run evaluation harness")
    parser.add_argument("--cases", default=None, help="Cases directory (file-based eval)")
    parser.add_argument("--db", default="data/processed/results.db", help="SQLite DB path")
    parser.add_argument("--mock", action="store_true", help="Use mock provider")
    parser.add_argument("--report", default=None, help="Save markdown report to file")
    args = parser.parse_args()

    if args.cases:
        results = run_eval_from_files(args.cases, use_mock=args.mock)
    else:
        results = run_eval_from_db(args.db)

    report = generate_report(results)
    print(report)

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w") as f:
            f.write(report)
        print(f"\nReport saved to {args.report}")
