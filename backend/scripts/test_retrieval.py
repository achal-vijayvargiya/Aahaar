#!/usr/bin/env python3
"""
Test Nutrition Knowledge Base Retrieval

This script demonstrates various retrieval methods:
- Semantic search
- Category filtering
- Dosha filtering
- Full-text search
- Multi-condition search

Usage:
    python backend/scripts/test_retrieval.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.knowledge_base.retriever import NutritionRetriever
from app.utils.logger import logger


def print_result(result, index=None):
    """Pretty print a single result"""
    prefix = f"\n{index}. " if index else "\n"
    print(prefix + "=" * 60)
    print(f"Disorder: {result['disorder_name']}")
    print(f"Category: {result['category']}")
    print(f"Dosha: {result['dosha_dominance']}")
    
    if 'relevance_score' in result:
        print(f"Relevance Score: {result['relevance_score']:.3f}")
    
    print(f"\nClinical Goals:\n  {result['clinical_goals']}")
    print(f"\nMNT - Macronutrients:\n  {result['mnt_macronutrients']}")
    print(f"\nMNT - Micronutrients:\n  {result['mnt_micronutrients']}")
    print(f"\nAyurvedic View:\n  {result['ayurvedic_view']}")
    print("=" * 60)


def main():
    """Run various retrieval tests"""
    db = SessionLocal()
    
    try:
        retriever = NutritionRetriever()
        
        print("\n" + "=" * 70)
        print("NUTRITION KNOWLEDGE BASE RETRIEVAL TESTS")
        print("=" * 70)
        
        # Get statistics
        stats = retriever.get_stats(db)
        print(f"\nKnowledge Base Statistics:")
        print(f"  Total Entries: {stats['total_entries']}")
        print(f"  Categories: {stats['total_categories']}")
        print(f"  Vector Embeddings: {stats['vector_embeddings']}")
        
        # Test 1: Semantic Search
        print("\n" + "=" * 70)
        print("TEST 1: SEMANTIC SEARCH")
        print("=" * 70)
        print("Query: 'nutrition plan for diabetes and high blood pressure'")
        
        results = retriever.semantic_search(
            db=db,
            query="nutrition plan for diabetes and high blood pressure",
            top_k=3
        )
        
        for i, result in enumerate(results, 1):
            print_result(result, i)
        
        # Test 2: Category Filter
        print("\n" + "=" * 70)
        print("TEST 2: FILTER BY CATEGORY")
        print("=" * 70)
        print("Category: 'Metabolic & Endocrine'")
        
        results = retriever.filter_by_category(
            db=db,
            category="Metabolic & Endocrine",
            limit=3
        )
        
        print(f"\nFound {len(results)} results in this category:")
        for result in results:
            print(f"  - {result['disorder_name']}")
        
        # Test 3: Dosha Filter
        print("\n" + "=" * 70)
        print("TEST 3: FILTER BY DOSHA")
        print("=" * 70)
        print("Dosha: 'Kapha'")
        
        results = retriever.filter_by_dosha(
            db=db,
            dosha="Kapha",
            limit=5
        )
        
        print(f"\nFound {len(results)} results for Kapha dosha:")
        for result in results:
            print(f"  - {result['disorder_name']} ({result['dosha_dominance']})")
        
        # Test 4: Search by Disorder Name
        print("\n" + "=" * 70)
        print("TEST 4: SEARCH BY DISORDER NAME")
        print("=" * 70)
        print("Search term: 'PCOS'")
        
        results = retriever.search_by_disorder_name(
            db=db,
            search_term="PCOS"
        )
        
        if results:
            print_result(results[0])
        
        # Test 5: Multi-Condition Search
        print("\n" + "=" * 70)
        print("TEST 5: MULTI-CONDITION SEARCH")
        print("=" * 70)
        print("Conditions: ['obesity', 'thyroid']")
        
        results = retriever.search_by_conditions(
            db=db,
            conditions=["obesity", "thyroid"],
            top_k=3
        )
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['disorder_name']} ({result['category']})")
            if 'relevance_score' in result:
                print(f"   Relevance: {result['relevance_score']:.3f}")
        
        # Test 6: Comprehensive Diet Plan Retrieval
        print("\n" + "=" * 70)
        print("TEST 6: COMPREHENSIVE DIET PLAN RETRIEVAL")
        print("=" * 70)
        
        diet_plan_data = retriever.retrieve_for_diet_plan(
            db=db,
            user_query="I need help with weight loss and better energy",
            health_conditions=["obesity", "fatigue"],
            dietary_preferences=["vegetarian"],
            dosha="Kapha",
            top_k=3
        )
        
        print(f"\nOriginal Query: {diet_plan_data['query']}")
        print(f"Enhanced Query: {diet_plan_data['enhanced_query']}")
        print(f"Total Results: {diet_plan_data['total_results']}")
        
        print("\nTop Recommendations:")
        for i, result in enumerate(diet_plan_data['results'], 1):
            print(f"\n{i}. {result['disorder_name']}")
            print(f"   Category: {result['category']}")
            print(f"   Dosha: {result['dosha_dominance']}")
        
        # Test 7: List All Categories
        print("\n" + "=" * 70)
        print("TEST 7: ALL CATEGORIES")
        print("=" * 70)
        
        categories = retriever.get_all_categories(db)
        print(f"\nAll Categories ({len(categories)}):")
        for category in categories:
            print(f"  - {category}")
        
        print("\n" + "=" * 70)
        print("✓ All tests completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"Error during retrieval tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

