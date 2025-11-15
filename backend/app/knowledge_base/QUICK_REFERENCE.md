# Knowledge Base Quick Reference

Quick reference for using the Nutrition Knowledge Base in your code.

## 🚀 Quick Start

```python
from app.database import SessionLocal
from app.knowledge_base import NutritionRetriever

# Initialize
db = SessionLocal()
retriever = NutritionRetriever()

# Search
results = retriever.semantic_search(db, "diabetes diet", top_k=5)

# Don't forget to close
db.close()
```

## 📖 Common Use Cases

### 1. Semantic Search (Most Common)

```python
# Natural language query
results = retriever.semantic_search(
    db=db,
    query="nutrition plan for high blood pressure and diabetes",
    top_k=5
)

# With filters
results = retriever.semantic_search(
    db=db,
    query="weight loss diet",
    category="Metabolic & Endocrine",
    dosha="Kapha",
    top_k=10
)
```

### 2. Get by Category

```python
# All entries in a category
results = retriever.filter_by_category(
    db=db,
    category="Digestive & Gastrointestinal",
    limit=20
)
```

### 3. Get by Dosha

```python
# All Kapha-related conditions
results = retriever.filter_by_dosha(
    db=db,
    dosha="Kapha",
    limit=20
)
```

### 4. Search Specific Disorder

```python
# Exact match
result = retriever.get_by_disorder(
    db=db,
    disorder_name="Diabetes Mellitus (Type 1 & 2)"
)

# Partial match
results = retriever.search_by_disorder_name(
    db=db,
    search_term="diabetes"
)
```

### 5. Full-Text Search

```python
# Keyword-based search
results = retriever.fulltext_search(
    db=db,
    search_query="omega-3 vitamin D",
    limit=10
)
```

### 6. Multi-Condition Search

```python
# Search by multiple conditions
results = retriever.search_by_conditions(
    db=db,
    conditions=["diabetes", "obesity", "hypertension"],
    top_k=5
)
```

### 7. Comprehensive Retrieval (For Diet Plans)

```python
# Most comprehensive - use this for diet plan generation
diet_data = retriever.retrieve_for_diet_plan(
    db=db,
    user_query="I want to lose weight and manage PCOS",
    health_conditions=["PCOS", "obesity"],
    dietary_preferences=["vegetarian", "gluten-free"],
    dosha="Kapha",
    category="Metabolic & Endocrine",
    top_k=5
)

# Returns structured data
print(diet_data['query'])           # Original query
print(diet_data['enhanced_query'])  # Enhanced query used
print(diet_data['total_results'])   # Number of results
print(diet_data['results'])         # List of results
print(diet_data['metadata'])        # Search metadata
```

## 📊 Utility Methods

### Get All Categories

```python
categories = retriever.get_all_categories(db)
# Returns: ['Metabolic & Endocrine', 'Cardiovascular & Circulatory', ...]
```

### Get All Doshas

```python
doshas = retriever.get_all_doshas(db)
# Returns: ['Kapha', 'Pitta', 'Vata', 'Kapha + Pitta', ...]
```

### Get Statistics

```python
stats = retriever.get_stats(db)
print(f"Total entries: {stats['total_entries']}")
print(f"Categories: {stats['total_categories']}")
print(f"Category distribution: {stats['category_distribution']}")
```

## 🔄 Result Format

All retrieval methods return dictionaries with this structure:

```python
{
    "id": 1,
    "category": "Metabolic & Endocrine",
    "disorder_name": "Diabetes Mellitus (Type 1 & 2)",
    "definition_etiology": "Chronic hyperglycemia...",
    "clinical_goals": "Achieve glycemic control...",
    "mnt_macronutrients": "Carbs 45–50% (low-GI)...",
    "mnt_micronutrients": "Chromium, Magnesium...",
    "mnt_fluids_electrolytes": "Adequate hydration...",
    "mnt_special_notes": "Emphasize fiber...",
    "ayurvedic_view": "Kapha–Pitta imbalance...",
    "dosha_dominance": "Kapha + Pitta",
    "lifestyle_yogic_guidance": "Walk 30–45 min...",
    "healing_affirmation": "I allow the sweetness...",
    "relevance_score": 0.87  # Only for semantic search
}
```

## 🎯 Best Practices

### 1. Always Use Context Manager

```python
from contextlib import contextmanager

@contextmanager
def get_retriever():
    db = SessionLocal()
    retriever = NutritionRetriever()
    try:
        yield db, retriever
    finally:
        db.close()

# Usage
with get_retriever() as (db, retriever):
    results = retriever.semantic_search(db, "diabetes diet")
```

### 2. Use Dependency Injection (FastAPI)

```python
from fastapi import Depends
from app.database import get_db

def get_retriever():
    return NutritionRetriever()

@router.get("/search")
async def search(
    query: str,
    db: Session = Depends(get_db),
    retriever: NutritionRetriever = Depends(get_retriever)
):
    results = retriever.semantic_search(db, query)
    return {"results": results}
```

### 3. Cache Retriever Instance

```python
# In your module
_retriever_instance = None

def get_cached_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = NutritionRetriever()
    return _retriever_instance
```

### 4. Error Handling

```python
from app.utils.logger import logger

try:
    results = retriever.semantic_search(db, query)
except Exception as e:
    logger.error(f"Search failed: {e}")
    results = []
```

## 🔍 Search Query Tips

### Good Queries (Natural Language)

✅ "nutrition plan for diabetes and high blood pressure"  
✅ "foods to boost immunity after COVID"  
✅ "diet for PCOS and weight management"  
✅ "Ayurvedic approach to digestive health"  
✅ "protein-rich foods for pregnancy"  

### Not-So-Good Queries

❌ "diabetes" (too short, use filter methods instead)  
❌ "food" (too generic)  
❌ Single words (use disorder search instead)  

### Query Enhancement

```python
# Instead of just "diabetes"
query = "nutrition plan for diabetes including foods, supplements, and lifestyle"

# Add context
query = f"Patient with {condition} needs {goal} through {approach}"
```

## 🎨 UI Integration Examples

### Search Autocomplete

```python
# Get disorder suggestions
def get_suggestions(search_term: str, limit: int = 5):
    results = retriever.search_by_disorder_name(
        db=db,
        search_term=search_term,
        limit=limit
    )
    return [r['disorder_name'] for r in results]
```

### Category Dropdown

```python
# Populate category dropdown
categories = retriever.get_all_categories(db)
category_options = [{"label": c, "value": c} for c in categories]
```

### Dosha Selector

```python
# Get dosha options
doshas = retriever.get_all_doshas(db)
dosha_options = [{"label": d, "value": d} for d in doshas]
```

## 🧪 Testing

### Unit Test Example

```python
import pytest
from app.database import SessionLocal
from app.knowledge_base import NutritionRetriever

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def retriever():
    return NutritionRetriever()

def test_semantic_search(db_session, retriever):
    results = retriever.semantic_search(
        db=db_session,
        query="diabetes diet",
        top_k=5
    )
    assert len(results) > 0
    assert 'disorder_name' in results[0]
    assert 'category' in results[0]

def test_filter_by_category(db_session, retriever):
    results = retriever.filter_by_category(
        db=db_session,
        category="Metabolic & Endocrine"
    )
    assert len(results) > 0
    assert all(r['category'] == "Metabolic & Endocrine" for r in results)
```

## 📱 API Response Examples

### Simple Search Response

```json
{
  "query": "diabetes diet",
  "total_results": 3,
  "results": [
    {
      "disorder_name": "Diabetes Mellitus (Type 1 & 2)",
      "category": "Metabolic & Endocrine",
      "mnt_macronutrients": "Carbs 45–50% (low-GI)...",
      "relevance_score": 0.89
    }
  ]
}
```

### Comprehensive Diet Plan Response

```json
{
  "query": "weight loss with PCOS",
  "enhanced_query": "weight loss with PCOS | Health conditions: PCOS, obesity | Dosha: Kapha",
  "total_results": 5,
  "results": [...],
  "metadata": {
    "health_conditions": ["PCOS", "obesity"],
    "dietary_preferences": ["vegetarian"],
    "dosha": "Kapha",
    "category": null
  }
}
```

## 🔗 Common Integrations

### With LLM (OpenAI/Anthropic)

```python
# Retrieve context
knowledge = retriever.retrieve_for_diet_plan(
    db=db,
    user_query=user_input,
    health_conditions=conditions,
    top_k=5
)

# Build prompt
context = "\n\n".join([
    f"Condition: {r['disorder_name']}\n"
    f"MNT: {r['mnt_macronutrients']}\n"
    f"Micronutrients: {r['mnt_micronutrients']}\n"
    f"Ayurvedic: {r['ayurvedic_view']}"
    for r in knowledge['results']
])

prompt = f"""
Based on this nutrition knowledge:
{context}

Create a personalized diet plan for: {user_input}
"""

# Call LLM
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)
```

### With Caching (Redis)

```python
import json
import redis

redis_client = redis.Redis()

def cached_search(query: str, top_k: int = 5):
    cache_key = f"kb_search:{query}:{top_k}"
    
    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Perform search
    results = retriever.semantic_search(db, query, top_k=top_k)
    
    # Cache for 1 hour
    redis_client.setex(cache_key, 3600, json.dumps(results))
    
    return results
```

## 🐛 Common Errors

### Error: "Collection not found"

**Cause**: Knowledge base not loaded  
**Fix**: Run `python scripts/load_knowledge_base.py --clear`

### Error: "No results found"

**Cause**: Query too specific or data not indexed  
**Fix**: Try broader query or check if data exists in DB

### Error: "Database connection failed"

**Cause**: PostgreSQL not running or wrong connection string  
**Fix**: Check DATABASE_URL in .env file

## 📚 More Information

- Full documentation: `backend/app/knowledge_base/README.md`
- Setup guide: `backend/KNOWLEDGE_BASE_SETUP.md`
- Test examples: `backend/scripts/test_retrieval.py`

---

**Last Updated**: 2025-10-30  
**Module Version**: 1.0.0

