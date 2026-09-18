# Mismar AI Office Architecture

## Product shape

Mobile-first PWA now; public SaaS later.

## Layers

1. Web shell: installable PWA.
2. API: one thin orchestration endpoint.
3. Council engine: role routing, parallel opinions, compressed debate.
4. Model gateway: LiteLLM provider abstraction.
5. Builder adapter: OpenHands/Grok Build/Aider/SWE-agent-compatible workers.
6. GitHub: branch -> PR -> CI -> human merge.
7. Persistent state: later add Postgres for projects, sessions, usage and audit logs.

## Debate design

Round 1: independent positions in parallel.
Round 2: each active role sees a compact digest, not full histories.
Round 3: optional only in deep mode.
Synthesis: one Chief-of-Staff call.

This gives the experience of a full staff while preventing quadratic context growth.

## Token strategy

N agents do NOT receive N copies of the entire conversation.

Every round compresses:
raw messages -> role summaries -> disagreement digest -> decision.

The system also caches identical calls and skips model work when deterministic checks can answer the question.

## Coding workers

Do not hard-wire one coding agent. The builder interface should accept:
- OpenHands
- Grok Build
- Aider
- SWE-agent / mini-SWE-agent
- future workers

The council decides which worker is appropriate for the task.

## Safety

No agent merges directly to main.
Builder changes happen on a branch.
CI is deterministic first.
Human approval is required before merge.

## Product modes

Fast: 3 roles / 1 round.
Balanced: up to 6 roles / 2 rounds.
Full: 13 roles / 2 rounds.
Deep: 13 roles / 3 rounds.

Full and Deep are deliberate high-compute modes.
