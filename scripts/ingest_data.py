"""Download and prepare public datasets."""


def ingest_samsum():
    """Download SAMSum dataset via HuggingFace datasets library."""
    raise NotImplementedError("Phase A: implement SAMSum ingestion.")


def ingest_support_tickets():
    """Download support ticket dataset from HuggingFace."""
    raise NotImplementedError("Phase A: implement ticket ingestion.")


def ingest_enron_sample():
    """Download and sample Enron emails."""
    raise NotImplementedError("Phase A: implement Enron sampling.")


if __name__ == "__main__":
    print("Data ingestion scripts — run individual functions as needed.")
