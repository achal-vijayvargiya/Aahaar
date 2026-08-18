# Agent task 03 — Platform PDF export (reporting module)

## Objective

Add a platform API that exports a client-shareable PDF from `seven_day_plan`, and wire the DietPlanView “Export PDF” button to it.

## Context

- Platform plans API: `backend/app/platform/api/plans/` (extend existing router).
- Do NOT use legacy `backend/app/routers/diet_plans.py` as the live path (may copy reportlab patterns only).
- Data: load `PlatformDietPlan` by id; read `meal_plan["seven_day_plan"]`; join client name from client repo if needed.
- Hub: `platform-api.ts` + DietPlanView currently toasts “PDF export is not yet available”.
- Rule: `.cursor/rules/client-delivery.mdc`

## Requirements

1. `GET /api/v1/platform/plans/{plan_id}/export?format=pdf` returning `application/pdf`.
2. PDF contents (minimum): cover (client name, plan date/version), then for each day → each meal: dish name, ingredients, cooking steps, serving notes, approximate cook time; optional per-meal calories/protein if present.
3. 404 if plan missing; 422/400 if no `seven_day_plan` to export.
4. Hub: `platformPlanApi.exportPdf(planId)` downloads the file; Export PDF button uses it.
5. Auth: follow whatever auth pattern sibling platform plan routes use (if none, document; prefer requiring auth if other sensitive routes do).

## Tests / verification

- Backend pytest: new test file e.g. `backend/tests/platform/api/test_plan_export.py`
  - Create/fixture a plan with minimal `seven_day_plan` → export returns 200 and `application/pdf` with non-empty body.
  - Missing plan → 404.
  - Plan without seven_day_plan → 4xx.
- Hub: Export PDF no longer shows the “not available” toast when API succeeds.
- Run: `pytest backend/tests/platform/api/test_plan_export.py -q` (from backend venv as project usual).

## Out of scope

Word export, shopping list, email send, recipe LLM changes, failed-recipe gating (task 04).

## Done when

Doctor can download a PDF from DietPlanView and share it with a client.
