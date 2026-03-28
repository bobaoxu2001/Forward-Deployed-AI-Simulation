"""Build case bundles from ingested datasets."""


def build_case_bundles(output_dir: str = "data/cases", num_cases: int = 40):
    """
    Assemble case bundles from raw datasets.
    Each bundle = one customer/incident/problem chain.

    Placeholder — will be implemented in Phase A.
    """
    raise NotImplementedError("Phase A: implement case bundle construction.")


if __name__ == "__main__":
    build_case_bundles()
