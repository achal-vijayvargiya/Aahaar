# Nutrition Knowledge Base Module

A modular knowledge base system for storing and retrieving holistic nutrition information using hybrid search (semantic + structured filtering).

## Architecture

The knowledge base uses a **hybrid approach** combining:

1. **PostgreSQL** - Structured data storage with full-text search
2. **ChromaDB** - Vector embeddings for semantic search
3. **Sentence Transformers** - Local embedding model (no API costs)

## Components

### 1. Database Model (`models/nutrition_knowledge.py`)

SQLAlchemy model for storing nutrition knowledge with fields:
- Category, Disorder Name
- Clinical information (definition, goals)
- Medical Nutrition Therapy (MNT) - macronutrients, micronutrients, fluids
- Ayurvedic perspective (dosha, ayurvedic view)
- Lifestyle guidance and healing affirmations

### 2. Loader (`knowledge_base/loader.py`)

**`NutritionKnowledgeLoader`** - Loads and indexes data

Key methods:
- `load_json_file()` - Parse JSON data files
- `index_data()` - Store in PostgreSQL + create embeddings
- `create_searchable_text()` - Generate rich text for embeddings
- `get_stats()` - Knowledge base statistics

### 3. Retriever (`knowledge_base/retriever.py`)

**`NutritionRetriever`** - Retrieve relevant information

Key methods:
- `semantic_search()` - Vector similarity search
- `filter_by_category()` - Filter by health category
- `filter_by_dosha()` - Filter by Ayurvedic dosha
- `search_by_disorder_name()` - Search specific conditions
- `retrieve_for_diet_plan()` - Comprehensive retrieval for diet planning
- `get_all_categories()` - List all categories
- `get_stats()` - Retrieval statistics

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `chromadb` - Vector database
- `sentence-transformers` - Embedding model
- `torch` - Deep learning backend
- `pandas`, `openpyxl` - Data processing

### 2. Run Database Migration

```bash
# From backend directory
alembic upgrade head
```

This creates the `nutrition_knowledge` table with all necessary indexes.

### 3. Load Knowledge Base

```bash
# From backend directory
python scripts/load_knowledge_base.py --clear --stats
```

Options:
- `--clear` - Clear existing data before loading
- `--stats` - Show statistics after loading
- `--file FILENAME` - Specify custom JSON file

This will:
1. Parse `Resource/Vaishnavi_Holistic_Nutrition_Notes.json`
2. Store 46 entries in PostgreSQL
3. Create vector embeddings using `all-MiniLM-L6-v2` model
4. Store embeddings in ChromaDB (stored in `kb_data/chromadb/`)

### 4. Test Retrieval (Optional)

```bash
python scripts/test_retrieval.py
```

This runs comprehensive tests of all retrieval methods.

## Usage Examples

### Basic Usage

```python
from app.database import SessionLocal
from app.knowledge_base import NutritionRetriever

# Initialize
db = SessionLocal()
retriever = NutritionRetriever()

# Semantic search
results = retriever.semantic_search(
    db=db,
    query="nutrition for diabetes and weight loss",
    top_k=5
)

for result in results:
    print(f"{result['disorder_name']}: {result['clinical_goals']}")
```

### Filter by Category

```python
# Get all metabolic conditions
results = retriever.filter_by_category(
    db=db,
    category="Metabolic & Endocrine"
)
```

### Filter by Dosha

```python
# Get Kapha-related conditions
results = retriever.filter_by_dosha(
    db=db,
    dosha="Kapha"
)
```

### Comprehensive Diet Plan Retrieval

```python
# Get relevant info for diet plan generation
diet_data = retriever.retrieve_for_diet_plan(
    db=db,
    user_query="I need to lose weight and have more energy",
    health_conditions=["obesity", "fatigue"],
    dietary_preferences=["vegetarian"],
    dosha="Kapha",
    top_k=5
)

print(f"Found {diet_data['total_results']} relevant entries")
for result in diet_data['results']:
    print(result['disorder_name'])
    print(result['mnt_macronutrients'])
    print(result['ayurvedic_view'])
```

## Data Format

The knowledge base expects JSON files with this structure:

```json
[
  {
    "Category": "Metabolic & Endocrine",
    "Disorder Name": "Diabetes Mellitus (Type 1 & 2)",
    "Definition / Etiology": "...",
    "Clinical Goals": "...",
    "MNT - Macronutrients": "...",
    "MNT - Micronutrients": "...",
    "MNT - Fluids & Electrolytes": "...",
    "MNT - Special Notes": "...",
    "Ayurvedic View": "...",
    "Dosha Dominance": "Kapha + Pitta",
    "Lifestyle & Yogic Guidance": "...",
    "Healing Affirmation": "..."
  }
]
```

## How It Works

### Indexing Process

1. **JSON Parsing** - Reads structured nutrition data
2. **Text Generation** - Creates rich searchable text combining all fields
3. **Embedding Creation** - Uses `all-MiniLM-L6-v2` to create 384-dim vectors
4. **Storage** - Stores in both PostgreSQL (structured) and ChromaDB (vectors)
5. **Full-Text Search** - Creates PostgreSQL TSVECTOR for keyword search

### Retrieval Process

1. **Query Enhancement** - Combines user query with filters
2. **Vector Search** - Finds semantically similar entries using cosine similarity
3. **Structured Filtering** - Applies category, dosha, condition filters
4. **Result Ranking** - Returns top-k results with relevance scores
5. **Deduplication** - Removes duplicate entries

## Performance

- **Embedding Model**: Runs locally, ~50ms per query
- **Vector Search**: Retrieves 10 results in ~20-50ms
- **Database Queries**: <10ms with proper indexes
- **Total Latency**: ~100-150ms for full retrieval

## Storage

- **PostgreSQL**: ~50-100KB per entry (structured data)
- **ChromaDB**: ~1.5KB per entry (384-dim vectors)
- **Total**: ~5-10MB for 46 entries

## Extending the Knowledge Base

### Adding New Data Files

```python
loader = NutritionKnowledgeLoader()
loader.index_data(
    db=db,
    filename="new_nutrition_data.json",
    clear_existing=False  # Append to existing data
)
```

### Adding Excel Support

The system is designed to support Excel files. To add:

```python
# In loader.py, add method:
def load_excel_file(self, filename: str) -> List[Dict]:
    import pandas as pd
    df = pd.read_excel(self.data_dir / filename)
    return df.to_dict('records')
```

## API Integration

To integrate with API endpoints, see example router in documentation.

### Example: Diet Plan Generation

```python
# In your router
from app.knowledge_base import NutritionRetriever

retriever = NutritionRetriever()

@router.post("/generate-diet-plan")
async def generate_diet_plan(
    request: DietPlanRequest,
    db: Session = Depends(get_db)
):
    # Retrieve relevant knowledge
    knowledge = retriever.retrieve_for_diet_plan(
        db=db,
        user_query=request.query,
        health_conditions=request.conditions,
        dosha=request.dosha
    )
    
    # Pass to LLM for personalized plan generation
    diet_plan = await generate_with_llm(knowledge['results'])
    
    return {"plan": diet_plan, "sources": knowledge['results']}
```

## Maintenance

### Rebuilding Indexes

```bash
# Clear and reload all data
python scripts/load_knowledge_base.py --clear --stats
```

### Backup

- **PostgreSQL**: Use standard PostgreSQL backup tools
- **ChromaDB**: Backup `kb_data/chromadb/` directory

### Monitoring

```python
# Get current statistics
stats = retriever.get_stats(db)
print(f"Total entries: {stats['total_entries']}")
print(f"Vector embeddings: {stats['vector_embeddings']}")
```

## Troubleshooting

### Issue: ChromaDB not found

**Solution**: Ensure ChromaDB directory exists:
```bash
mkdir -p kb_data/chromadb
```

### Issue: Model download fails

**Solution**: Pre-download the model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

### Issue: PostgreSQL full-text search not working

**Solution**: Ensure search vectors are created:
```sql
-- Check search vectors
SELECT COUNT(*) FROM nutrition_knowledge WHERE search_vector IS NOT NULL;

-- Recreate if needed
UPDATE nutrition_knowledge SET search_vector = 
    to_tsvector('english', disorder_name || ' ' || category);
```

## Future Enhancements

- [ ] Support for multiple languages
- [ ] Recipe database integration
- [ ] Meal planning algorithms
- [ ] User preference learning
- [ ] Integration with nutrition APIs
- [ ] Export to meal planning apps

## License

Internal use only - Part of DrAssistent application

