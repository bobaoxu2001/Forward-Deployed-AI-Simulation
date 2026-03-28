"""Run evaluation harness on batch results."""


def run_evaluation(cases_dir: str, results_dir: str):
    """
    Run full evaluation: schema pass rate, evidence coverage,
    review routing, failure modes.

    Placeholder — will be implemented in Phase C.
    """
    raise NotImplementedError("Evaluation harness not yet implemented. Phase C.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python -m eval.run_eval <cases_dir> <results_dir>")
        sys.exit(1)
    run_evaluation(sys.argv[1], sys.argv[2])
