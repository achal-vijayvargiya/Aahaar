# Agent task 02 — NCP recipe step: readable UI

## Objective

Replace the raw JSON dump on the NCP recipe-generation step with the same readable meal UI used in DietPlanView.

## Context

- Depends on task 01 mapper (`mapSevenDayPlan` or equivalent).
- File: `aahaar-wellness-hub/src/components/NCPProcessFlow.tsx` (and related).
- After recipe generation, UI currently dumps `seven_day_plan` in a `<pre>`.
- Rule: `.cursor/rules/client-delivery.mdc`

## Requirements

1. Import and reuse the task-01 mapper — do not duplicate mapping logic.
2. After successful recipe generation (and when loading existing recipe data), render day/meal cards.
3. Keep approve/generate actions working.
4. Show validation warnings / null recipes clearly.
5. Link or button to open full DietPlanView for the plan id when available.

## Tests / verification

- Hub build passes.
- Manual: run NCP through recipe step → human-readable recipes, not JSON.
- If mapper tests exist, they still pass.

## Out of scope

PDF export, backend recipe engine changes.

## Done when

Nutritionist can review recipes inside the NCP flow without reading JSON.
