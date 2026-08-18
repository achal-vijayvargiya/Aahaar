# Agent task 01 — DietPlanView: map seven_day_plan

## Objective

Make `aahaar-wellness-hub` DietPlanView show the real 7-day recipe plan from platform API data instead of empty meals.

## Context

- Plan payload: `PlatformPlanResponse.meal_plan` may contain `seven_day_plan` with `days.day_1…day_7`, each with `meals` keyed by meal name.
- Each meal typically has: `recipe` (`dish_name`, `ingredients`, `cooking_steps`, `approx_cooking_time_minutes`, `serving_instructions`), `allocated_foods`, `total_nutrition`, `validation`.
- Current code has a TODO mapper that always returns `[]` — replace it.
- Rule: `.cursor/rules/client-delivery.mdc`
- Source of truth is live engine output, NOT `sample_7day_output.json`.

## Requirements

1. Create a pure mapper (e.g. `src/lib/mapSevenDayPlan.ts`) from `meal_plan.seven_day_plan` → UI day/meal model.
2. Handle missing `seven_day_plan` gracefully (empty state message, not crash).
3. Handle `recipe: null` (show allocated foods + “Recipe pending/failed” badge).
4. Wire DietPlanView day tabs to render dish name, ingredients, steps, cook time, per-meal nutrition.
5. Keep existing plan metadata (client, dates, macros summary) working.
6. Do not implement PDF export in this task.

## Tests / verification

- Add a small unit test for the mapper if the hub has a test setup; otherwise add a `*.test.ts` next to the mapper with vitest/jest if already configured, or document a fixture-based manual checklist.
- Manual: open a plan that has `seven_day_plan` in DB/API → all 7 day tabs show meals.
- `npm run build` (or project equivalent) in `aahaar-wellness-hub` must pass.

## Out of scope

Backend changes, PDF, NCPProcessFlow JSON replacement (task 02), mobile.

## Done when

DietPlanView is usable by a nutritionist to read the week’s recipes without opening raw JSON.
