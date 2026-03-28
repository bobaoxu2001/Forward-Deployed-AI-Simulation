"""Run the full structuring pipeline on case bundles.

Pipeline: load → normalize → extract → validate → gate → store
"""
import sys
from pathlib import Path

from pipeline.schemas import CaseBundle
from pipeline.loaders import load_all_cases
from pipeline.normalize import normalize_case
from pipeline.extract import extract_case, MockProvider, ClaudeProvider
from pipeline.validate import validate_extraction, check_evidence_present
from pipeline.gate import compute_gate_decision
from pipeline.storage import (
    init_db,
    store_case,
    store_extraction,
    store_trace_log,
    write_trace_jsonl,
)


def run_pipeline(
    cases_dir: str = "data/cases",
    use_mock: bool = False,
    db_path: Path | None = None,
) -> dict:
    """
    Run full pipeline on all case bundles in cases_dir.

    Args:
        cases_dir: Directory containing case bundle JSON files
        use_mock: If True, use MockProvider instead of Claude API
        db_path: Optional custom DB path (for testing)

    Returns:
        Summary dict with counts and results
    """
    # Initialize storage
    init_db(db_path)

    # Load cases
    cases = load_all_cases(cases_dir)
    if not cases:
        print(f"No cases found in {cases_dir}. Run scripts/build_cases.py first.")
        return {"total": 0, "processed": 0, "errors": 0}

    print(f"Loaded {len(cases)} cases from {cases_dir}")

    # Choose provider
    provider = MockProvider() if use_mock else ClaudeProvider()
    print(f"Using provider: {type(provider).__name__}")

    results = {
        "total": len(cases),
        "processed": 0,
        "errors": 0,
        "auto_routed": 0,
        "review_routed": 0,
        "schema_pass": 0,
        "schema_fail": 0,
    }

    for i, case in enumerate(cases):
        print(f"\n[{i+1}/{len(cases)}] Processing {case.case_id}...")

        try:
            # Step 1: Normalize
            case = normalize_case(case)

            # Step 2: Extract
            extraction, metadata = extract_case(case, provider=provider)

            # Step 3: Validate
            ext_dict = extraction.to_dict()
            valid, errors = validate_extraction(ext_dict)
            has_evidence, evidence_msg = check_evidence_present(ext_dict)

            if valid:
                results["schema_pass"] += 1
            else:
                results["schema_fail"] += 1
                print(f"  Schema validation failed: {errors}")

            # Step 4: Gate
            gate_decision = compute_gate_decision(ext_dict)

            # If validation failed or evidence missing, force review
            if not valid or not has_evidence:
                gate_decision["route"] = "review"
                if not valid:
                    gate_decision["reasons"].append("Schema validation failed")
                    gate_decision["review_reason_codes"].append("schema_failure")
                if not has_evidence:
                    gate_decision["reasons"].append(evidence_msg)
                    gate_decision["review_reason_codes"].append("missing_evidence")

            if gate_decision["route"] == "auto":
                results["auto_routed"] += 1
            else:
                results["review_routed"] += 1

            print(f"  Route: {gate_decision['route']}")
            if gate_decision["reasons"]:
                print(f"  Reasons: {gate_decision['reasons']}")

            # Step 5: Store
            store_case(case, db_path)
            store_extraction(case.case_id, extraction, gate_decision, db_path)
            store_trace_log(
                case_id=case.case_id,
                model_name=metadata.get("model_name", "unknown"),
                prompt_version=metadata.get("prompt_version", "unknown"),
                validation_pass=valid,
                validation_errors=errors,
                review_required=gate_decision["route"] == "review",
                review_reason_codes=gate_decision.get("review_reason_codes", []),
                gate_route=gate_decision["route"],
                latency_ms=metadata.get("latency_ms", 0),
                raw_response=metadata.get("raw_response", ""),
                db_path=db_path,
            )
            write_trace_jsonl(
                case_id=case.case_id,
                extraction=extraction,
                gate_decision=gate_decision,
                metadata=metadata,
                validation_result=(valid, errors),
            )

            results["processed"] += 1

        except Exception as e:
            results["errors"] += 1
            print(f"  ERROR: {e}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Pipeline complete:")
    print(f"  Total cases: {results['total']}")
    print(f"  Processed: {results['processed']}")
    print(f"  Errors: {results['errors']}")
    print(f"  Schema pass: {results['schema_pass']}")
    print(f"  Schema fail: {results['schema_fail']}")
    print(f"  Auto-routed: {results['auto_routed']}")
    print(f"  Review-routed: {results['review_routed']}")

    return results


if __name__ == "__main__":
    use_mock = "--mock" in sys.argv
    run_pipeline(use_mock=use_mock)
