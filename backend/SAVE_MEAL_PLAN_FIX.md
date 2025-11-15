# Meal Plan Save Issue - Fixed

## Problem

When using the conversational AI agent to generate and save diet plans, users encountered an issue where the agent would respond with:

> "It seems that I'm unable to save the meal plan due to formatting issues. As the meal plan is quite extensive, I'll need to reformat it to fit the exact format required for saving."

### Root Cause

The `SaveDietPlanTool` expected the agent to explicitly pass the complete meal plan text in the `plan_text` parameter when calling the tool. However, in conversational mode:

1. The agent generates the meal plan as part of its conversational output
2. When the user asks to "save the plan", the agent calls the save tool
3. The agent was NOT extracting and passing the meal plan text from its previous responses
4. The parser received empty or incorrectly formatted text, resulting in 0 meals parsed

**Log Evidence:**
```
2025-11-10 19:12:44 - INFO - Parsing AI-generated diet plan response
2025-11-10 19:12:44 - INFO - Parsed 0 meals from AI response  # ← Problem!
```

## Solution

Implemented a multi-layered fix:

### 1. Made `plan_text` Optional in SaveDietPlanTool

**File:** `backend/app/utils/diet_plan_tools.py`

```python
class SaveDietPlanInput(BaseModel):
    """Input schema for saving diet plan to database"""
    client_id: int = Field(description="Database ID of the client")
    plan_name: str = Field(description="Name of the diet plan")
    plan_text: Optional[str] = Field(
        default=None, 
        description="Complete meal plan text. If not provided, will extract from conversation history."
    )
    duration_days: int = Field(default=7, description="Duration of the plan in days")
```

### 2. Added Conversation History Extraction

Added a new method `_extract_meal_plan_from_history()` to the `SaveDietPlanTool` that:

- Searches through conversation history backwards
- Looks for AI messages containing meal plans (messages with "Day 1", "Day 2", etc.)
- Extracts the most recent message containing 3+ days (likely the full meal plan)
- Returns the extracted text for parsing

```python
def _extract_meal_plan_from_history(self) -> Optional[str]:
    """Extract meal plan text from conversation history"""
    if not self.agent_memory:
        return None
    
    try:
        messages = self.agent_memory.chat_memory.messages
        
        for msg in reversed(messages):
            content = msg.content if hasattr(msg, 'content') else str(msg)
            
            # Check if this message contains a meal plan
            if re.search(r'Day\s+\d+\s*:', content, re.IGNORECASE):
                day_count = len(re.findall(r'Day\s+\d+\s*:', content, re.IGNORECASE))
                
                if day_count >= 3:  # Likely the full meal plan
                    logger.info(f"Extracted meal plan with {day_count} days from conversation history")
                    return content
        
        logger.warning("Could not find meal plan in conversation history")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting meal plan from history: {e}")
        return None
```

### 3. Updated Tool Initialization

**File:** `backend/app/utils/diet_plan_agent.py`

The `DietPlanAgent` now sets a reference to its memory in the `SaveDietPlanTool` after initialization:

```python
# Set memory reference for SaveDietPlanTool so it can extract meal plans
for tool in self.tools:
    if hasattr(tool, 'name') and tool.name == 'save_diet_plan':
        tool.agent_memory = self.memory
        self._save_tool = tool
        logger.debug("Set memory reference for SaveDietPlanTool")
        break
```

### 4. Enhanced System Prompt

Updated the agent's system prompt to be more explicit about saving:

```python
IMPORTANT FOR SAVING:
When user asks to save the plan, you MUST call save_diet_plan with:
- client_id: The client's ID
- plan_name: A descriptive name (e.g., "7-Day Weight Loss Plan")
- plan_text: THE COMPLETE FORMATTED MEAL PLAN TEXT you generated
- duration_days: Number of days (usually 7)

The plan_text should contain the entire meal plan in the structured format with all days.
```

## How It Works Now

### User Flow

1. **User:** "Generate 7 days meal plan"
   - Agent generates complete meal plan in structured format
   - Stores it in conversation history

2. **User:** "Save this plan"
   - Agent calls `save_diet_plan` tool
   - **Option A:** Agent provides `plan_text` parameter (ideal)
   - **Option B:** Tool extracts meal plan from conversation history (fallback)
   - Parser processes the text and creates database records

### Fallback Logic

```
User asks to save
    ↓
Agent calls save_diet_plan
    ↓
plan_text provided? ──YES──→ Use provided text
    ↓ NO
    ↓
Extract from conversation history
    ↓
Found meal plan? ──YES──→ Use extracted text
    ↓ NO
    ↓
Return error with instructions
```

## Benefits

1. **More Robust:** Works even if agent doesn't provide `plan_text` explicitly
2. **Better UX:** Agent can save plans without needing to regenerate them
3. **Backward Compatible:** Still works if agent provides `plan_text` directly
4. **Clear Errors:** If extraction fails, provides clear instructions

## Testing

### Manual Test

```bash
cd backend
python scripts/test_ai_diet_plan_flow.py
```

### API Test

```bash
# 1. Start a chat session
curl -X POST http://localhost:8000/diet-plans/ai-chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "message": "Generate a 7-day meal plan for this client"
  }'

# 2. Save the plan
curl -X POST http://localhost:8000/diet-plans/ai-chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "session_id": "SESSION_ID_FROM_STEP_1",
    "message": "Save this meal plan"
  }'
```

### Expected Behavior

Before the fix:
```
❌ "It seems that I'm unable to save the meal plan due to formatting issues..."
```

After the fix:
```
✅ Diet plan saved successfully!

Plan Details:
- Plan ID: 42
- Name: 7-Day Weight Loss Plan
- Duration: 7 days
- Total Meals: 49
- Status: active

The plan is now visible in the client's diet plans list.
```

## Files Changed

1. `backend/app/utils/diet_plan_tools.py`
   - Made `plan_text` optional
   - Added `agent_memory` field
   - Added `_extract_meal_plan_from_history()` method
   - Updated `_run()` to use extraction fallback
   - Added `re` import

2. `backend/app/utils/diet_plan_agent.py`
   - Updated system prompt with clearer save instructions
   - Added logic to set memory reference in SaveDietPlanTool
   - Added `_save_tool` tracking field

## Edge Cases Handled

1. **No meal plan in history:** Returns clear error message with format instructions
2. **Multiple meal plans in history:** Uses the most recent one (searches backwards)
3. **Partial meal plans:** Only extracts if 3+ days found (validates completeness)
4. **Memory not available:** Gracefully handles missing memory reference
5. **Parsing failures:** Provides detailed error messages

## Future Enhancements

1. **Session-based Extraction:** Store generated meal plan in session metadata
2. **Incremental Saving:** Allow saving after each day is generated
3. **Draft Mode:** Save incomplete plans as drafts for later completion
4. **Plan Comparison:** Compare conversation history plan with provided text for consistency

## Support

If issues persist:

1. Check logs: `backend/logs/app.log`
2. Verify meal plan format matches expected structure
3. Ensure conversation history is being persisted
4. Test with explicit `plan_text` parameter first

## Related Documentation

- [AI Diet Plan Format Guide](AI_DIET_PLAN_FORMAT_GUIDE.md)
- [AI Agent Implementation](CONVERSATIONAL_AI_AGENT_IMPLEMENTATION.md)
- [Quick Start Guide](QUICK_START_AI_DIET_PLANS.md)

