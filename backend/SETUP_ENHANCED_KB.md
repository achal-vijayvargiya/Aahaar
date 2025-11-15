# Setup Enhanced Knowledge Base - Quick Start

## 🚀 5-Minute Setup

### Step 1: Run Migration (30 seconds)

```bash
cd backend
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade 005 -> 006, Add enhanced food knowledge base tables
```

**This creates:**
- ✅ `food_dosha_effects` table
- ✅ `food_disease_relations` table
- ✅ `food_allergens` table
- ✅ `food_goal_scores` table
- ✅ New columns in `food_items`

### Step 2: Populate Data (2-3 minutes)

```bash
python scripts/populate_enhanced_food_kb.py
```

**Expected output:**
```
INFO  - Populating food dosha effects...
INFO  - Created 2310 dosha effect records
INFO  - Populating food allergens...
INFO  - Created 487 allergen records
INFO  - Populating food-disease relations...
INFO  - Created 213 disease relation records
INFO  - Populating food goal scores...
INFO  - Created 4620 goal score records
INFO  - POPULATION COMPLETE!
```

**If you get errors:**
- Make sure food_items table has data: `SELECT COUNT(*) FROM food_items;`
- If empty, run: `python scripts/load_food_database.py` first

### Step 3: Verify (30 seconds)

```bash
psql -U postgres -d drassistent
```

```sql
-- Check record counts
SELECT COUNT(*) FROM food_dosha_effects;      -- Should be ~2300
SELECT COUNT(*) FROM food_disease_relations;  -- Should be ~200
SELECT COUNT(*) FROM food_allergens;          -- Should be ~500
SELECT COUNT(*) FROM food_goal_scores;        -- Should be ~4600

-- View sample data
SELECT f.food_name, fde.dosha_type, fde.effect, fde.intensity
FROM food_items f
JOIN food_dosha_effects fde ON f.id = fde.food_id
LIMIT 5;
```

### Step 4: Test API (1 minute)

```bash
# Get your auth token first
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Save the token
export TOKEN="your_token_here"

# Test smart retrieval
curl -X POST http://localhost:8000/api/v1/diet-plans/smart-food-retrieval \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "duration_days": 7,
    "custom_goals": "weight loss",
    "custom_allergies": "dairy"
  }'
```

**Expected:** JSON with foods_by_category containing 8 foods per category!

### Step 5: Test in UI (1 minute)

1. Open http://localhost:5173
2. Login
3. Click any client
4. Click "Generate Diet Plan" ▼
5. Select "**Smart Retrieval (New!)**"
6. Fill in goals and click "Retrieve Foods"
7. See foods organized by category! 🎉

## ✅ Success Checklist

After setup, verify:

- [ ] Migration completed without errors
- [ ] Population script created ~7,600 records
- [ ] API endpoint returns foods by category
- [ ] Frontend displays accordion with categories
- [ ] Foods show nutritional info
- [ ] Composite scores visible
- [ ] Dairy excluded when dairy allergy specified
- [ ] Dosha effects displayed correctly

## 🐛 Troubleshooting

### "Table already exists" error
```bash
# Check current migration
alembic current

# If you need to rollback:
alembic downgrade -1

# Then upgrade again:
alembic upgrade head
```

### "No foods in database" error
```bash
# Load food database first
python scripts/load_food_database.py

# Then populate enhanced KB
python scripts/populate_enhanced_food_kb.py
```

### No records created
```bash
# Check food_items has dosha_impact values
psql -U postgres -d drassistent \
  -c "SELECT COUNT(*) FROM food_items WHERE dosha_impact IS NOT NULL;"

# Should be > 0
```

### Frontend shows no categories
- Check backend logs: `tail -f backend/logs/app.log`
- Check browser console for errors
- Verify API returns data (use cURL)
- Check health profile exists for client

## 🎯 What's Next

After successful setup:

1. **Test with different profiles:**
   - Try "weight loss" goal
   - Try "muscle gain" goal
   - Try with diabetes condition
   - Try with different allergies

2. **Review the results:**
   - Are the right foods being retrieved?
   - Do scores make sense?
   - Are allergens properly excluded?

3. **Fine-tune if needed:**
   - Adjust scoring weights in `smart_food_retriever.py`
   - Add more disease rules in `populate_enhanced_food_kb.py`
   - Expand allergen keywords

4. **Connect to meal plan generation:**
   - Pass approved foods to LLM
   - Generate plan using only approved foods
   - Validate nutrition targets

## 📚 Full Documentation

- **Complete Guide:** `ENHANCED_KB_COMPLETE.md`
- **Flow Explanation:** `FOOD_RETRIEVAL_FLOW_EXPLAINED.md`
- **API Integration:** Check router code

---

**Status:** ✅ READY TO USE!

**Time to Setup:** ~5 minutes  
**Time to Test:** ~2 minutes  
**Total Time:** ~7 minutes

**Go build something amazing! 🚀**

