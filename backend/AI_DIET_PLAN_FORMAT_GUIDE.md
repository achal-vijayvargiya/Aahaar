# AI-Powered Diet Plan Generation - Format Guide

## Overview

The AI-powered diet plan generation system now automatically parses the AI's response and saves structured data to the database, matching the format used by manual diet plans.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│  (GenerateDietPlanAIDialog.tsx)                                │
│                                                                  │
│  Step 1: Configure → Step 2: Review Foods → Step 3: Complete   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND API                              │
│  /diet-plans/generate-ai/step1  →  /diet-plans/generate-ai/step2│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      AI AGENT (LangChain)                        │
│  - Uses OpenRouter (Claude/LLama models)                        │
│  - Generates structured meal plan text                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PARSER (DietPlanParser)                       │
│  - Extracts structured data from AI text                        │
│  - Validates completeness                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (PostgreSQL)                         │
│  - DietPlan table                                               │
│  - DietPlanMeal table                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Expected Format from AI Agent

The AI agent now generates diet plans in a strictly structured format:

```
Day 1:
- Morning Cleanse (6:30 AM): Warm Lemon Water with Ginger
  Portion: 1 glass (250ml)
  Healing Purpose: Detoxifies system, kickstarts digestion
  Dosha Notes: Balances all three doshas, especially good for Kapha
  Calories: 10, Protein: 0g, Carbs: 2g, Fat: 0g

- Breakfast (8:30 AM): Moong Dal Khichdi with Ghee
  Portion: 1 bowl (200g)
  Healing Purpose: Easy to digest, grounding for Vata
  Dosha Notes: Tridoshic, especially balancing for Vata
  Calories: 320, Protein: 12g, Carbs: 45g, Fat: 8g

- Mid Snack (11:00 AM): Fresh Seasonal Fruits
  Portion: 1 cup (150g)
  Healing Purpose: Provides natural energy, vitamins
  Dosha Notes: Cooling for Pitta, energizing for Kapha
  Calories: 80, Protein: 1g, Carbs: 20g, Fat: 0g

... (continues for all 7 meals per day)

Day 2:
... (repeats structure)
```

## Meal Structure

Each meal includes:

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `day_number` | Yes | Day of the week (1-7) | `1` |
| `meal_time` | Yes | Time of meal | `"6:30 AM"` |
| `meal_type` | Yes | Type of meal | `"Morning Cleanse"` |
| `food_dish` | Yes | Name of the dish | `"Warm Lemon Water with Ginger"` |
| `portion` | Recommended | Portion size | `"1 glass (250ml)"` |
| `healing_purpose` | Recommended | Ayurvedic benefit | `"Detoxifies system"` |
| `dosha_notes` | Recommended | Dosha impact | `"Balances all three doshas"` |
| `calories` | Recommended | Calorie content | `10` |
| `protein_g` | Recommended | Protein in grams | `0` |
| `carbs_g` | Recommended | Carbs in grams | `2` |
| `fat_g` | Recommended | Fat in grams | `0` |
| `notes` | Optional | Additional notes | `"Drink warm, not hot"` |
| `food_item_ids` | Optional | IDs from food database | `"123,456"` |

## Standard Meal Types

The system recognizes these meal types:

1. **Morning Cleanse** (6:30 AM) - Light detox drink
2. **Breakfast** (8:30 AM) - Hearty, grounding meal
3. **Mid Snack** (11:00 AM) - Light snack
4. **Lunch** (1:30 PM) - Largest meal of the day
5. **Evening Snack** (4:30 PM) - Light refreshment
6. **Dinner** (7:00 PM) - Light, digestible meal
7. **Sleep Tonic** (9:00 PM) - Calming bedtime drink

## Calorie Distribution

Default distribution (can be adjusted):

- Morning Cleanse: 10-20 kcal
- Breakfast: 25% of daily target
- Mid Snack: 10% of daily target
- Lunch: 35% of daily target
- Evening Snack: 10% of daily target
- Dinner: 15% of daily target
- Sleep Tonic: 10-20 kcal

**Example for 1800 kcal/day:**
- Morning Cleanse: 15 kcal
- Breakfast: 450 kcal
- Mid Snack: 180 kcal
- Lunch: 630 kcal
- Evening Snack: 180 kcal
- Dinner: 270 kcal
- Sleep Tonic: 15 kcal

## Parser Implementation

### DietPlanParser Class

Located in: `backend/app/utils/diet_plan_parser.py`

Key methods:

```python
class DietPlanParser:
    def parse_diet_plan(self, ai_response: str) -> Dict[str, Any]:
        """
        Main parsing method.
        Returns:
        {
            "meals": [...],
            "nutritional_summary": {...},
            "total_meals": int
        }
        """
    
    def validate_meals(self, meals: List[Dict]) -> Dict[str, Any]:
        """
        Validates parsed meals.
        Returns:
        {
            "valid": bool,
            "errors": [...],
            "warnings": [...],
            "total_meals": int,
            "days_covered": int
        }
        """
```

### Parsing Strategies

The parser uses multiple strategies to handle variations in AI output:

1. **Structured Format Parsing** - Primary method for well-formatted output
2. **Day Section Parsing** - Splits by day markers
3. **Meal Block Parsing** - Extracts individual meal blocks

### Validation Rules

The parser validates:

- ✅ All required fields present
- ✅ Day numbers are consecutive
- ✅ At least 80% of meals have nutritional data
- ⚠️ Missing optional fields (warnings only)
- ⚠️ Gaps in day coverage (warnings only)

## API Endpoint Changes

### POST /diet-plans/generate-ai/step2

**Previous Behavior:**
- Returned raw AI text response
- No database storage
- User had to manually parse

**New Behavior:**
- Generates AI response
- Parses response automatically
- Validates parsed data
- Saves to database
- Returns complete `DietPlanWithMeals` object

**Request:**
```json
{
  "client_id": 1,
  "user_feedback": "confirm",
  "modifications": {},
  "duration_days": 7,
  "name": "Weight Loss Plan - Week 1",
  "start_date": "2025-11-10T00:00:00Z"
}
```

**Response:**
```json
{
  "id": 42,
  "client_id": 1,
  "name": "Weight Loss Plan - Week 1",
  "description": "AI-generated personalized diet plan. Total meals: 49",
  "duration_days": 7,
  "start_date": "2025-11-10T00:00:00Z",
  "end_date": "2025-11-17T00:00:00Z",
  "status": "active",
  "health_goals": "weight loss",
  "dosha_type": "Vata",
  "diet_type": "veg",
  "allergies": "nuts",
  "target_calories": 1800,
  "target_protein_g": 90,
  "target_carbs_g": 200,
  "target_fat_g": 60,
  "created_by_id": 1,
  "created_at": "2025-11-09T10:30:00Z",
  "updated_at": "2025-11-09T10:30:00Z",
  "meals": [
    {
      "id": 301,
      "diet_plan_id": 42,
      "day_number": 1,
      "meal_time": "6:30 AM",
      "meal_type": "Morning Cleanse",
      "food_dish": "Warm Lemon Water with Ginger",
      "portion": "1 glass (250ml)",
      "healing_purpose": "Detoxifies system, kickstarts digestion",
      "dosha_notes": "Balances all three doshas",
      "calories": 10,
      "protein_g": 0,
      "carbs_g": 2,
      "fat_g": 0,
      "order_in_day": 0
    },
    // ... 48 more meals
  ]
}
```

## Frontend Integration

### GenerateDietPlanAIDialog Component

Updated to handle the new response format:

```typescript
const handleStep2 = async () => {
  const response = await dietPlanApi.generateAIStep2(...);
  
  // New format: Saved plan with ID and meals
  if (response.id && response.meals) {
    toast.success(`Diet plan created with ${response.meals.length} meals!`);
    onComplete(); // Refresh parent view
    handleClose(); // Close dialog
  }
};
```

### User Experience Flow

1. **Step 1**: User configures preferences → AI retrieves foods
2. **Review**: User reviews retrieved foods → Can provide feedback
3. **Step 2**: User confirms → AI generates plan → **Automatically saved!**
4. **Success**: Dialog closes → Plan appears in client's diet plan list

## Testing

### Manual Testing

```bash
# Run the test script
cd backend
python scripts/test_ai_diet_plan_flow.py
```

This will:
1. Initialize AI agent
2. Run Step 1 (food retrieval)
3. Run Step 2 (meal plan generation)
4. Parse the response
5. Validate parsed meals
6. Display results

### API Testing

```bash
# Step 1: Retrieve foods
curl -X POST http://localhost:8000/diet-plans/generate-ai/step1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "client_id": 1,
    "duration_days": 7
  }'

# Step 2: Generate and save plan
curl -X POST http://localhost:8000/diet-plans/generate-ai/step2 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "client_id": 1,
    "user_feedback": "confirm",
    "duration_days": 7,
    "name": "Test Plan"
  }'
```

## Configuration

Required environment variables:

```env
# OpenRouter API Key (required)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Model selection (optional, defaults shown)
DIET_PLAN_MODEL=anthropic/claude-3.5-sonnet
DIET_PLAN_TEMPERATURE=0.7
```

## Error Handling

### Common Issues

1. **Parsing Failures**
   - Cause: AI output doesn't match expected format
   - Solution: Parser tries multiple strategies, validates before saving
   - Fallback: Returns detailed error with validation issues

2. **Missing Fields**
   - Cause: AI omits required fields (dish name, day number)
   - Solution: Parser validation catches this before saving
   - Error: "Failed to parse AI-generated plan properly"

3. **Incomplete Plans**
   - Cause: AI generates fewer meals than expected
   - Solution: Validation warns but allows saving if minimum criteria met
   - Warning: "Only X/Y meals have nutritional data"

### Debugging

Check logs at: `backend/logs/app.log`

```log
INFO - Parsing AI-generated diet plan response
INFO - Parsed 49 meals from AI response
WARNING - Parsed meals have warnings: ['Only 42/49 meals have nutritional data']
INFO - User admin generated AI diet plan 42 for client 1 with 49 meals
```

## Database Schema

### DietPlan Table
```sql
CREATE TABLE diet_plans (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    duration_days INTEGER DEFAULT 7,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    health_goals TEXT,
    dosha_type VARCHAR(50),
    diet_type VARCHAR(50),
    allergies TEXT,
    target_calories FLOAT,
    target_protein_g FLOAT,
    target_carbs_g FLOAT,
    target_fat_g FLOAT,
    status VARCHAR(50) DEFAULT 'draft',
    created_by_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### DietPlanMeal Table
```sql
CREATE TABLE diet_plan_meals (
    id SERIAL PRIMARY KEY,
    diet_plan_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    meal_time VARCHAR(20) NOT NULL,
    meal_type VARCHAR(50) NOT NULL,
    food_dish TEXT NOT NULL,
    food_item_ids TEXT,
    healing_purpose TEXT,
    portion VARCHAR(100),
    dosha_notes TEXT,
    notes TEXT,
    calories FLOAT,
    protein_g FLOAT,
    carbs_g FLOAT,
    fat_g FLOAT,
    order_in_day INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (diet_plan_id) REFERENCES diet_plans(id) ON DELETE CASCADE
);
```

## Best Practices

### For Developers

1. **Always validate** parsed data before saving
2. **Log parsing warnings** for monitoring
3. **Test with various AI models** (Claude, LLama, etc.)
4. **Handle edge cases** (missing days, incomplete meals)

### For AI Prompt Engineering

1. **Be explicit** about required format
2. **Use examples** in system prompt
3. **Emphasize structure** over prose
4. **Validate in real-time** with tools

### For Users

1. **Review foods** in Step 1 before proceeding
2. **Provide clear feedback** if modifications needed
3. **Check generated plan** after creation
4. **Edit manually** if needed (all meals are editable)

## Troubleshooting

### Plan Not Saving

**Symptom**: Step 2 completes but no plan in database

**Check:**
```python
# In logs:
"Parsed meals validation failed: ..."
```

**Solution**: Improve AI prompt or adjust parser validation rules

### Incomplete Nutritional Data

**Symptom**: Some meals missing calories/macros

**Cause**: AI doesn't provide nutritional data consistently

**Solution**: Parser accepts meals with missing nutrition (warnings only)

### Wrong Meal Times

**Symptom**: Meals have incorrect times

**Cause**: AI uses non-standard time format

**Solution**: Parser uses default times if parsing fails

## Future Enhancements

1. **Smarter Parsing**: ML-based extraction for more robust parsing
2. **Real-time Validation**: Validate while AI is generating
3. **Iterative Refinement**: Allow user to refine specific days/meals
4. **Template Library**: Save successful plans as templates
5. **A/B Testing**: Compare different AI models and prompts

## Support

For issues or questions:
- Check logs: `backend/logs/app.log`
- Run test script: `python scripts/test_ai_diet_plan_flow.py`
- Review API docs: `http://localhost:8000/docs`
- Contact: [Your support email/channel]

