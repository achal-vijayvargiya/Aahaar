# Client delivery — agent runbook

Goal: nutritionists can **see** a 7-day recipe plan and **export a shareable PDF** for clients.

NCP engines through food allocation + recipe LLM already work. The gap is UI mapping + platform export + light recipe polish.

## How to run in Cursor

1. Open this repo (local or Cloud Agent).
2. Run **one task at a time**, in order (`01` → `05`). Do not parallelize 01–03.
3. New Agent chat (or Cloud Agent) → paste the **entire** contents of that task’s `.md` file as the prompt.
4. When the agent finishes: review diff, run its listed tests, merge/commit.
5. Only then start the next task.

Optional: `@docs/delivery/README.md` and `@.cursor/rules/client-delivery.mdc` in the prompt for extra context.

## Task order

| # | Task | Repo area | Depends on |
|---|------|-----------|------------|
| 01 | Map `seven_day_plan` → DietPlanView | wellness-hub | — |
| 02 | Same mapper in NCP recipe step (replace JSON dump) | wellness-hub | 01 |
| 03 | Platform PDF export API + wire Export PDF button | backend + hub | 01 |
| 04 | Gate export / UI on failed recipes | backend + hub | 03 |
| 05 | Recipe latency: parallel LLM calls | backend | 03 (can follow 04) |

## Definition of “deliverable ready”

- [ ] DietPlanView shows 7 days of dishes, ingredients, steps, nutrition
- [ ] NCP recipe step shows the same readable UI (not raw JSON)
- [ ] Doctor can download a PDF from the plan page
- [ ] Plans with null/failed recipes are flagged before share
- [ ] Listed automated tests pass

## Out of scope (do not assign yet)

Admin API stubs, mobile NCP, shopping list v2, Word export, MealPlanNarrator, legacy diet_plans router.
