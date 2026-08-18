# Agent task 04 — Gate share on recipe quality

## Objective

Prevent silent sharing of incomplete plans: surface failed/null recipes in UI and block or warn on PDF export.

## Context

- Meals may have `recipe: null` and/or `validation.is_valid === false` / `validation.warnings`.
- Export from task 03 should not pretend a failed meal is a finished dish.
- Rule: `.cursor/rules/client-delivery.mdc`

## Requirements

1. Backend export: if any meal lacks a usable recipe, either:
   - default: return 409 with a clear JSON body listing day/meal failures, OR
   - support `?allow_partial=true` to export with “Recipe unavailable” placeholders.
   Pick one default (prefer 409 without query param; allow_partial opt-in).
2. Hub DietPlanView + NCP step: banner summarizing failed meal count; disable Export PDF or confirm before `allow_partial`.
3. Tests for 409 vs allow_partial behavior.

## Tests / verification

- Extend `test_plan_export.py` with a fixture plan that has one `recipe: null` meal.
- Hub build passes.
- Manual: incomplete plan shows warning; export blocked or confirmed.

## Out of scope

Fixing LLM quality itself, parallelization (task 05).

## Done when

A doctor cannot accidentally export a “complete” PDF that hides missing recipes.
