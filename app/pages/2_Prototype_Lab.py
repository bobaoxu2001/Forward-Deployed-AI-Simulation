"""Prototype Lab — Run structuring on case bundles, inspect outputs."""
import streamlit as st

st.set_page_config(page_title="Prototype Lab", layout="wide")
st.title("Prototype Lab")

st.info("Upload or select a case bundle to run the structuring pipeline.")

st.markdown("""
### Pipeline Flow
```
Raw Text → Normalization → LLM Structuring (JSON Schema) → Validation → Output
```

### What you'll see
- **Input:** Raw ticket/email/chat text
- **Output:** Structured JSON (root cause, sentiment, risk, recommendation, evidence)
- **Metadata:** Model version, prompt version, latency
""")

# Placeholder for pipeline integration
st.warning("Pipeline not yet connected. Complete Phase B to enable.")
