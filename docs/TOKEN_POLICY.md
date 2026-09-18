# Token Economy Policy

Tokens are a hard compute budget.

1. Never call all 13 roles by default.
2. Deterministic routing comes before an LLM router.
3. One call performs one useful reasoning job.
4. Structured compact output only.
5. Never send the whole repository to an LLM.
6. Never resend unchanged context.
7. Send diffs, manifests, errors and short summaries instead.
8. Cache successful responses by normalized task hash.
9. Deterministic CI runs before AI review.
10. AI review is manual or conditional, never automatic by default.
11. Repair loops are capped at 2.
12. Failed repairs become a human task.
13. Builder agents inspect the filesystem themselves.
14. Cheap models handle routing, extraction, formatting and review.
15. Strong models are reserved for architecture ambiguity and hard coding.

Normal call budget:
Planner 1
Specialists 0-2
Synthesis 0-1
Builder 1 OpenHands conversation
CI 0 LLM calls
AI review 0 by default
Repairs up to 2 OpenHands continuations

Context budget:
Planner gets the idea, tiny repository manifest and constraints.
Builder gets plan.md and feedback.md while OpenHands can inspect files itself.
Checker gets CI status, failing test names, short logs and relevant diff.

The 13 roles are a capability registry, not 13 always-on agents.
