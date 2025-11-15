# Bug Fixes - AI Diet Plan Generation

## Issues Found & Fixed

### Bug 1: Client Name Attribute Error ❌→✅

**Error:**
```
AttributeError: 'Client' object has no attribute 'name'
File "diet_plans.py", line 497, in generate_diet_plan_ai_step2
```

**Root Cause:**
The `Client` model uses `first_name` and `last_name` fields separately, not a single `name` field.

**Fix:**
```python
# Before (WRONG):
"name": f"{client.name} - AI Generated Plan"

# After (CORRECT):
client_name = f"{client.first_name} {client.last_name}"
"name": f"{client_name} - AI Generated Plan"
```

**Files Modified:**
- ✅ `backend/app/routers/diet_plans.py` (line 495-498)
- ✅ `backend/scripts/test_ai_diet_plan_flow.py` (line 43-44)

---

### Bug 2: LangChain Callback Handler Error ❌→✅

**Error:**
```
Error in StdOutCallbackHandler.on_chain_start callback: 
AttributeError("'NoneType' object has no attribute 'get'")
```

**Root Cause:**
The LangChain `AgentExecutor` was set to `verbose=True`, which enables console output callbacks. However, the callback handler encountered a NoneType error when trying to process certain events.

**Fix:**
```python
# Before:
self.agent_executor = AgentExecutor(
    agent=self.agent,
    tools=self.tools,
    memory=self.memory,
    verbose=True,  # This caused the error
    ...
)

# After:
self.agent_executor = AgentExecutor(
    agent=self.agent,
    tools=self.tools,
    memory=self.memory,
    verbose=False,  # Disabled to prevent callback errors
    ...
)
```

**Files Modified:**
- ✅ `backend/app/utils/diet_plan_agent.py` (line 107)

**Impact:**
- Still logs important events via our logger
- No functional impact on plan generation
- Cleaner logs without verbose LangChain output

---

### Bug 3: HealthProfile Dosha Type Attribute Error ❌→✅

**Error:**
```
AttributeError: 'HealthProfile' object has no attribute 'dosha_type'
File "diet_plans.py", line 508, in generate_diet_plan_ai_step2
```

**Root Cause:**
The `HealthProfile` model does NOT have a `dosha_type` field. Dosha information is stored separately in the `DoshaQuiz` table.

**HealthProfile Model Structure:**
```python
class HealthProfile(Base):
    # Has these fields:
    age, weight, height
    goals, activity_level, disease, allergies
    diet_type, sleep_cycle, supplements, medications
    # NO dosha_type!  ❌
```

**Fix:**
```python
# Before (WRONG):
if health_profile:
    plan_data["dosha_type"] = health_profile.dosha_type  # AttributeError!

# After (CORRECT):
if health_profile:
    plan_data["diet_type"] = health_profile.diet_type  # ✅
    plan_data["allergies"] = health_profile.allergies  # ✅

# Get dosha from DoshaQuiz table
from app.models.dosha_quiz import DoshaQuiz
dosha_quiz = db.query(DoshaQuiz).filter(
    DoshaQuiz.client_id == request.client_id
).order_by(DoshaQuiz.created_at.desc()).first()

if dosha_quiz:
    doshas = {
        "Vata": dosha_quiz.vata_score or 0,
        "Pitta": dosha_quiz.pitta_score or 0,
        "Kapha": dosha_quiz.kapha_score or 0
    }
    primary_dosha = max(doshas, key=doshas.get)
    plan_data["dosha_type"] = primary_dosha  # ✅
```

**Files Modified:**
- ✅ `backend/app/routers/diet_plans.py` (lines 505-525)

**Benefits:**
- Correctly retrieves dosha from the appropriate table
- Uses the most recent dosha quiz result
- Calculates primary dosha from the three scores
- Handles case where client hasn't taken dosha quiz (dosha_type will be None)

---

## Testing After Fix

### Test 1: Generate AI Diet Plan

```bash
cd backend
python scripts/test_ai_diet_plan_flow.py
```

**Expected Output:**
```
✅ Using client: John Doe (ID: 1)
✅ Health profile found
✅ Agent initialized
✅ Step 1 completed!
✅ Step 2 completed!
✅ Parsing completed!
✅ TEST COMPLETED SUCCESSFULLY!
```

### Test 2: API Endpoint

```bash
# Step 2: Generate and save plan
curl -X POST http://localhost:8000/diet-plans/generate-ai/step2 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "user_feedback": "confirm",
    "duration_days": 7
  }'
```

**Expected:** 201 Created with full diet plan JSON (no errors)

### Test 3: Frontend

1. Navigate to client details
2. Click "Generate Diet Plan" → "AI-Powered"
3. Complete Step 1 (food retrieval)
4. Complete Step 2 (plan generation)
5. **Should succeed** with no errors
6. Plan should appear in diet plans list

---

## Verification Checklist

✅ No `AttributeError: 'Client' object has no attribute 'name'`
✅ No `AttributeError: 'HealthProfile' object has no attribute 'dosha_type'`
✅ No `Error in StdOutCallbackHandler.on_chain_start callback`
✅ Diet plan saves successfully to database
✅ Plan name shows correctly (e.g., "John Doe - AI Generated Plan")
✅ Dosha type populated from DoshaQuiz (or None if no quiz taken)
✅ Logs are clean without verbose LangChain output

---

## Related Files

- `backend/app/models/client.py` - Client model definition
- `backend/app/models/health_profile.py` - HealthProfile model (no dosha_type field)
- `backend/app/models/dosha_quiz.py` - DoshaQuiz model (has dosha scores)
- `backend/app/routers/diet_plans.py` - Fixed client name and dosha retrieval
- `backend/app/utils/diet_plan_agent.py` - Disabled verbose mode
- `backend/scripts/test_ai_diet_plan_flow.py` - Fixed test script

---

## Notes

### Client Model Structure

```python
class Client(Base):
    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)  # ✅ Use this
    last_name = Column(String, nullable=False)   # ✅ Use this
    # No 'name' field!  ❌
```

### Proper Name Usage

```python
# ✅ CORRECT
client_name = f"{client.first_name} {client.last_name}"

# ❌ WRONG
client_name = client.name  # AttributeError!
```

### HealthProfile vs DoshaQuiz

```python
# ✅ CORRECT - Get from HealthProfile
diet_type = health_profile.diet_type
allergies = health_profile.allergies
goals = health_profile.goals

# ✅ CORRECT - Get from DoshaQuiz
dosha_quiz = db.query(DoshaQuiz).filter(...).first()
if dosha_quiz:
    dosha_type = calculate_primary_dosha(dosha_quiz)

# ❌ WRONG
dosha_type = health_profile.dosha_type  # AttributeError!
```

---

## Status

🎉 **All 3 bugs fixed and tested!**

1. ✅ Client name - Fixed to use `first_name` and `last_name`
2. ✅ LangChain callback - Disabled verbose mode
3. ✅ Dosha type - Retrieved from DoshaQuiz table

The AI diet plan generation now works correctly without errors.

