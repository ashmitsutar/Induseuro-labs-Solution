# ShopAssist: cost optimization

## Run

```sh
python -m pip install -r requirements.txt
python question1/run.py
python question2/run.py
python cost_report.py
python -m pytest -q tests/test_optimized.py \
  tests/test_question1.py::test_baseline_resolves_public_tickets \
  tests/test_question1.py::test_holdout_subscription \
  tests/test_question2.py::test_pipeline_resolves_public_tickets
```

The original tests are preserved. Their two `test_baseline_cost_is_high` assertions deliberately expect the expensive starting implementation; they will fail for a successful optimization. They are not correctness or target-budget checks. The additional tests check each public ticket against its own budget and check single-call behavior, the subscription holdout, retrieval, and invalid audit responses.

## Question 1

The agent keeps the full small policy corpus, ticket thread, and order snapshot in one call. It removes the per-request UUID, examples, verbose reasoning request, and pretty-printed snapshot, and requests compact JSON. The result uses the existing parser. No ticket IDs or expected answers are hard-coded in the agent. No cache savings are claimed.

Measured with the repository's `CostSession`, cl100k_base tokenizer and local simulator. For T-1001 the single `handle_ticket` call has 384 input tokens, 0 cached input tokens, and 46 output tokens: **384 × 3 + 46 × 15 = 1,842 points**, below 3,000. Output: `REFUND`, `returns-within-30-days`.

## Question 2

The four logical nodes are preserved, with one model call instead of four:

1. **Triage (local):** select potentially relevant policy domains from order attributes, including a general returns fallback. It does not decide the action.
2. **Retrieve (local):** load the selected articles from `data/kb`; do not build or transmit the enormous expanded corpus.
3. **Compose (LLM):** send the ticket, snapshot and retrieved policy text once, asking for concise JSON.
4. **Audit (local):** reject malformed responses, unknown actions, citations outside the retrieved set, and automatic refund/replacement decisions that violate key eligibility conditions. Missing or malformed facts fail closed. Errors must be routed to a human by the caller.

| Path | Call | Input | Cached input | Output | Points |
|---|---|---:|---:|---:|---:|
| T-1004, replacement | compose | 256 | 0 | 36 | 256 × 3 + 36 × 15 = **1,308** |
| T-1002, digital denial | compose | 266 | 0 | 39 | 266 × 3 + 39 × 15 = **1,383** |

All four public tickets are below 2,500 points. Q2 also matches the subscription holdout. Billing totals exclude local computation and no cache discount is assumed.

## Limits

The provided `LlmClient` is a simulator that obtains its answer from the evaluator based on the order snapshot, not from interpreting the prompt or retrieved articles. These results therefore verify the assignment harness, not real-model policy reasoning or prompt quality. The audit checks selected eligibility conditions for automatic refunds and replacements, but is not a complete independent policy engine: for example it does not verify all denials or escalation decisions. The retrieval mapping is hand-maintained for the supplied policy domains; add indexing, coverage for new policies and a stronger policy audit before production. Neither agent executes refunds or shipments. The simulator's customer reply can claim actions already happened, so a real deployment must ground customer messaging in actual fulfillment state.
