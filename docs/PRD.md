# PRD: Forward-Deployed AI Simulation

> Full PRD is in the project root PDF. This is the reference summary.

See: `Forward-Deployed AI Simulation PRD：从脏数据到系统抽象的 Distyl 风格交付.pdf`

## Key Decisions

- **System > Model**: Evaluation, guardrails, audit trails, and feedback loops are first-class, not afterthoughts.
- **AI boundaries explicit**: AI suitability matrix defines what AI does, what it doesn't, and where human review is mandatory.
- **No auto-reply**: AI never sends customer-facing messages or commits SLA promises.
- **Evidence required**: Every structured output must cite source text. Unsupported claims are flagged.
- **Case bundles as delivery unit**: 20-40 bundles simulating real customer/incident chains.
- **Abstraction after usage**: Reusable modules are extracted from what was actually built and measured.
