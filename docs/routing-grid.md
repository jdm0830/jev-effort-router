# Routing grid — models, profiles, and effort mapping

Companion of SPEC.md. Every consumer reads this to know what Jev may choose, what each option means, and
how a chosen level lands on each model family's wire.

## Models offered to Jev

The Choice options are exactly these two, in this order. The option string is
`"<model-id>: <one-line profile>"`; the model id is everything before the first `:`.

Every model id here belongs to the **OpenRouter** provider — this plugin routes nothing else. The
profile text is sent to Jev verbatim, **in English**, and is part of the measured payload, so treat it
as data rather than documentation: it is not a display string, and rewriting or re-translating it
changes what Jev is choosing between. The criteria were moved from French to English in an earlier
pass; the before/after measurement is recorded in the changelog.

| # | Model id (option prefix) | Profile line sent to Jev |
|---|---|---|
| 1 | `openrouter/auto` | the usual choice for general work: everyday writing, explanation, summarising, ordinary coding and tool use; routed for you by OpenRouter; cheap for its size |
| 2 | `typesafe/jev-router` | deep and hard work: rigorous reasoning, mathematics, logic, science, quantitative and financial analysis, complex code and long agentic tasks where a wrong answer is costly; slow and the most expensive |

These two profiles are the fork's benchmarked grid. Neither carries a numeric benchmark in this file:
the fork ships no benchmark numbers it did not measure, and pinning prices or scores here would be a
claim this repository cannot back. Both entries are OpenRouter-routed, so `openrouter/auto` is handled
by OpenRouter's own router and `typesafe/jev-router` by TypeSafe's; read their current pricing and
capabilities from the provider catalog rather than a snapshot in this file.

**A profile line must name a task family, never praise the model in the abstract.** The two rules a
rewrite has to keep: no superlative with no task attached ("excellent value for money", "excellent in
real use for everyday tasks") and no cost adjective standing in for a task ("fast and economical"). A
line like that is a safe pick on *every* prompt, so the model carrying one swallows decisions that
belong to the others — the mechanism that kept narrow profiles off the route until the grid was
rewritten to name task families. `tests/test_grid.py::test_no_profile_is_a_task_free_superlative`
enforces it. Cost and speed may appear as a secondary clause, always beside the task the model is for;
pricing is not part of the criterion text.

**The id here is the wire id, verbatim — tag included.** An id this table names must match what the
provider's catalog serves, or a perfectly confident decision becomes `HTTP 404: model "..." not found`
and kills the turn outright. Verify every grid entry against the provider's model list — the host
caches OpenRouter's as a flat `model_id -> {name, context_length, pricing, ...}` mapping at
`<HERMES_HOME>/cache/openrouter_model_metadata.json` (every id *and* its short alias are keys) — rather
than against memory or pricing pages, because a provider-side rename is the one drift a passing offline
suite cannot see.

The rest of the provider's catalog is deliberately excluded: not benchmarked in this pass, and a longer
Choice list dilutes decision quality. Adding an option is a reviewed change to this file plus a README
note, not a config-only act.

## Effort options

Second Choice question, three options, in this order: `low`, `medium`, `high`. Default when confidence is
below threshold: `medium`.

## Effort-to-wire mapping

Every route lands on the `openrouter` provider profile. OpenRouter's transport emits a nested
`reasoning: {effort: ...}` inside `extra_body`, so the plugin writes the chosen level to
`extra_body["reasoning"]["effort"]` and drops any stale top-level `reasoning_effort` — writing both
makes OpenRouter reject the call with `HTTP 400: "reasoning_effort" and "reasoning.effort" are both
provided with conflicting values`, and a top-level `reasoning` argument raises
`Completions.create() got an unexpected keyword argument 'reasoning'`. The plugin's per-family table
exists to (a) state the family's real vocabulary where a generic clamp would be wrong, and (b) omit the
field instead of risking a 400. Unknown model ids — including both grid entries — fall back to the
OpenRouter family, accepted `low | medium | high`.

| Model family | Wire parameter | Accepted levels | Mapping of `low` / `medium` / `high` | Source |
|---|---|---|---|---|
| DeepSeek (V4 / V4.1) | `extra_body.reasoning.effort` | low, medium, high, max | passthrough | `effort.py` `FAMILIES` |
| Kimi K3 | `extra_body.reasoning.effort` | low, high, max (medium → **high** is the declared override; server default is high) | `low` → low, `medium` → high, `high` → high | `effort.py` `FAMILIES` |
| GLM-5.3 / GLM-5.3 Flash | `extra_body.reasoning.effort` | low, medium, high, max (graded, live-verified, monotonic) | passthrough | `effort.py` `FAMILIES` |
| GLM-5.2 | `extra_body.reasoning.effort` | high, max | `low` / `medium` → high | `effort.py` `FAMILIES` |
| MiniMax | `extra_body.reasoning.effort` | low, medium, high, max (`none` disables) | passthrough | `effort.py` `FAMILIES` |
| Nemotron | `extra_body.reasoning.effort` | low, medium, high, max (`none` disables) | passthrough | `effort.py` `FAMILIES` |
| Qwen | `extra_body.reasoning.effort` | low, medium, high, max | passthrough | `effort.py` `FAMILIES` |
| Claude / Gemini / GPT | `extra_body.reasoning.effort` | low, medium, high | passthrough | `effort.py` `FAMILIES` |
| **Unknown ids** (incl. `openrouter/auto`, `typesafe/jev-router`) | `extra_body.reasoning.effort` | low, medium, high | passthrough; `xhigh`/`max` → high, `minimal` → low | `effort.py` `OPENROUTER` |

Rules that follow from the table:

1. **Never escalate.** When the requested level is not accepted, clamp to the nearest *weaker* accepted
   level; only send the weakest accepted level when nothing weaker exists. Hermes' `clamp_effort` already
   implements exactly this and is the reference implementation for the plugin's own table.
2. **Never invent a level.** A level outside `low | medium | high` (and the family's override targets) is
   dropped, and the request goes out with no reasoning-effort key at all rather than a 400.
3. **`none` is a disable, not a rung.** The plugin never routes to a reasoning-off state.
4. **`max` is not reachable by Jev's three-level question.** It is a valid target only as an override
   destination (`medium → high` for Kimi K3 is; `xhigh → max` is not reachable at all).

This table is the record of what has been verified. A family added later gets its row filled in from a
live probe before it joins the grid; until then the generic clamp applies and the audit record marks the
effort as `clamped`.

## Levers left, in the order they are worth trying

Measured findings and the order of expected return, so the next pass does not re-derive them.

1. **The confidence threshold is the second-order cause of an unused model.** A model can win the
   decision and still never serve a turn: below the 0.5 threshold the answer is discarded and the
   configured fallback model is applied instead. On the pre-rewrite grid, 3 of the 8 task families sat
   at mean confidence 0.40-0.42 and were degraded 5/5 — the grid was deciding and the threshold was
   throwing it away. A per-task threshold, or a threshold that only applies when the leading
   probability is not a clear margin over the runner-up, recovers those turns without loosening
   anything on the tasks that are already confident. Use `grid_coverage.below_threshold` in `status`
   to see how often it fires before changing the number.
2. **Effort can depend on the chosen model, but the endpoint cannot do it.** The two questions are
   evaluated independently and in parallel, so a `high` effort answer reaches a model chosen for
   throughput. Coupling them in code — asking for the effort *after* the model is known, or mapping
   `(model, effort)` through the per-family table instead of only clamping the level — is a behaviour
   change that needs its own measurement. There is no evidence yet that it pays.
3. **`route_per_turn: false` (once per session) is the wrong default for a mixed session.** A session
   that opens with a greeting and then asks for a refactor is served by one model the whole way. Routing
   per turn is the default because of this; the cost is one decision call per user turn, at p50 0.27 s.
4. **Do not add models, and do not reorder the grid, without a measurement.** Every extra option
   measurably dilutes a Choice decision, and the first-listed option has an advantage that is visible
   in the numbers (the generalist holds its position partly through wording, not only through fit).
   Both were measured here; changing either without re-running the 8-task × 5-call protocol makes the
   effect unattributable.
5. **Re-measure after any provider-side change.** Two independent sources of drift: the model ids
   themselves (`nemotron-3-nano` → `nemotron-3-nano:30b`) and the decision model's own calibration
   (`jev_model` pinned to `typesafe/jev-1.13` for exactly this reason). The measurement script pattern
   is: import the plugin package through `importlib`, swap the criterion text, POST to the live
   endpoint with the profile's key, 5 calls per task family, then compare chosen model, mean
   confidence and calls above the threshold.
