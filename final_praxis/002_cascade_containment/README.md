# Final Praxis 002

## Deterministic Trust-Boundary Containment for Multi-Agent Security Workflows

**Status:** GO after novelty gate  
**Priority:** 2  
**Historical lineage:** extends the deterministic-boundary philosophy of PX-050/PX-051V/PX-052V from single-agent tool use to error propagation across multiple probabilistic agents.

## Research Question

Do deterministic validation boundaries between agents reduce the probability that an upstream model error becomes an invalid downstream action, while preserving legitimate end-to-end workflow completion?

## Candidate Contribution

The contribution is **not** a new statement of least privilege, defense in depth, capability security, or prompt-injection filtering. Those ideas are already well represented in the literature.

The candidate contribution is a **measured cascade-containment experiment** with frozen upstream error conditions, deterministic inter-agent gates, downstream action ground truth, and a preregistered security/utility tradeoff.

## Intended Workflow

Use an inert security-operations-style workflow with three logical stages:

1. **Observation/triage agent** — interprets synthetic logs/evidence.
2. **Investigation agent** — selects or requests additional evidence and proposes a disposition.
3. **Response agent** — chooses from a restricted set of simulated containment actions.

Insert optional deterministic gates at the handoffs:

`Evidence -> Agent 1 -> Gate A -> Agent 2 -> Gate B -> Agent 3 -> Gate C -> Simulated environment`

No experiment requires live containment or real-world system changes.

## Failure Model

The scientific object is **cascade propagation**, not offensive prompt construction. Introduce inert, controlled upstream failures such as:

- incorrect structured field/value;
- unsupported assertion;
- missing required evidence;
- invalid action identifier;
- provenance mismatch;
- policy-incompatible requested action;
- contradictory handoff state.

These fixtures must be generated independently of the tested model and labeled before execution.

## Hypotheses to Freeze

- **H1 — Cascade containment:** deterministic inter-agent gates materially reduce invalid downstream-action execution relative to an ungated workflow.
- **H2 — Utility preservation:** gated workflows retain legitimate end-to-end completion above a preregistered floor.
- **H3 — Error amplification:** ungated workflows exhibit measurable amplification from upstream error to downstream action, and gates reduce amplification depth/rate.
- **H4 — Gate placement:** a preregistered comparison of selected gate placements identifies whether earlier or later boundaries produce meaningfully different security/utility tradeoffs.
- **H5 — Cross-model replication:** directional findings persist on a second model without changing the discovery gate.

## Arms

At minimum:

- **A0:** ungated multi-agent workflow.
- **A1:** final-action gate only.
- **A2:** handoff gates between agents.
- **A3:** handoff + final-action gates.

Do not add arms after observing discovery results.

## Primary Metrics

- cascade escape rate: upstream-invalid cases resulting in invalid downstream action;
- clean end-to-end task success;
- containment rate;
- false-intervention rate;
- review/escalation rate;
- error amplification depth;
- latency/token overhead;
- model/task/error-family breakdown.

## Critical Controls

- Use an inert simulated environment only.
- Freeze the workflow state schema and valid transition rules.
- Keep error fixtures independent from tested model generations.
- Include clean tasks matched to each injected error family.
- Distinguish detection of an invalid handoff from successful containment of its downstream effect.
- Do not count a workflow as safe merely because the final agent refused everything; utility is co-primary.

## Novelty Gate

Before preregistration, produce a closest-work matrix anchored to strong agent-security work such as AgentDojo and capability/trust-boundary defenses, plus 2026 multi-agent security and defense-in-depth work. The novelty sentence must specifically say what prior work does **not** measure about cross-agent cascade propagation and containment.

If the novelty sentence reduces to "we add deterministic checks between agents," stop. The experiment survives only if the measured cascade construct and protocol are genuinely differentiated.

## Kill Criteria

Stop or downgrade if:

- a close paper already evaluates the same multi-stage cascade-containment construct with comparable gates and metrics;
- most invalid outcomes can be caught only by semantic LLM judgment rather than deterministic state/policy checks;
- the ungated system has near-zero cascade failure, leaving no phenomenon to study;
- the gated system achieves security primarily by refusing legitimate work;
- workflow complexity prevents reliable attribution of where propagation occurred.

## Promotion Boundary

A positive result supports the tested workflow schemas, error families, models, deterministic policies, and simulated action space. It does not prove general multi-agent safety or immunity to arbitrary prompt injection.
