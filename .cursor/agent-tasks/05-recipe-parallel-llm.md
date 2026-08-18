# Agent task 05 — Recipe engine: parallel LLM calls

## Objective

Reduce recipe generation wall-clock time by running meal LLM calls concurrently (bounded), without changing output schema.

## Context

- `backend/app/platform/engines/recipe_engine/recipe_generation_engine.py` currently generates recipes sequentially (~meals × 7 days).
- Output shape of `seven_day_plan` must remain compatible with UI/PDF.
- Existing tests mock LLM — update as needed.
- Rule: `.cursor/rules/client-delivery.mdc`

## Requirements

1. Parallelize per-meal LLM generation with a concurrency limit (e.g. 3–5).
2. Preserve per-meal validation + retry behavior.
3. Preserve `summary` counts (`successful_recipes`, `failed_recipes`, etc.).
4. No schema change to `seven_day_plan`.
5. Document env/settings knob if you add one (max workers).

## Tests / verification

- `pytest backend/tests/platform/engines/test_recipe_generation_engine.py -q`
- Add/adjust a test that mocked LLM is invoked for multiple meals and results land in correct day/meal keys under concurrency.
- Manual optional: one real generate with `skip_recipe_llm=false` only if keys available — not required in CI.

## Out of scope

UI, PDF, batching into a single LLM prompt (unless clearly better and schema-safe — prefer concurrency first).

## Done when

Same output schema; tests green; generation is meaningfully faster for multi-meal plans under mock/timed unit expectations or documented concurrency.
