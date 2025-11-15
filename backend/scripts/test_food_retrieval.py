#!/usr/bin/env python3
"""
Test Food Database Retrieval

Demonstrates various food retrieval methods including:
- Best foods by category
- Nutritional filtering
- Dosha-based recommendations
- Semantic search

Usage:
    python scripts/test_food_retrieval.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.knowledge_base.food_retriever import FoodRetriever
from app.utils.logger import logger


def print_food(food, index=None):
    """Pretty print a food item"""
    prefix = f"\n{index}. " if index else "\n"
    print(prefix + "="*60)
    print(f"Food: {food['food_name']}")
    print(f"Category: {food['category']}")
    print(f"Macros: {food['macros_summary']}")
    print(f"Micronutrients: {food['key_micronutrients']}")
    print(f"Dosha Impact: {food['dosha_impact']}")
    print(f"Nature: {food['satvik_rajasik_tamasik']}")
    print(f"Region: {food['region']}")
    if 'relevance_score' in food:
        print(f"Relevance Score: {food['relevance_score']:.3f}")
    print("="*60)


def main():
    db = SessionLocal()
    
    try:
        retriever = FoodRetriever()
        
        print("\n" + "="*70)
        print("FOOD DATABASE RETRIEVAL TESTS")
        print("="*70)
        
        # Get statistics
        stats = retriever.get_stats(db)
        print(f"\nTotal Food Items: {stats['total_food_items']}")
        print(f"Categories: {stats['total_categories']}")
        print(f"Vector Embeddings: {stats['vector_embeddings']}")
        
        # Test 1: Get Best Foods by Category
        print("\n" + "="*70)
        print("TEST 1: BEST FOODS BY CATEGORY")
        print("="*70)
        print("Query: 'high protein foods for muscle building'")
        
        results_by_category = retriever.get_best_foods_by_category(
            db=db,
            user_query="high protein foods for muscle building",
            categories=["Cereal", "Pulses", "Dairy"],  # Specific categories
            min_protein=10.0,
            top_per_category=3
        )
        
        for category, foods in results_by_category.items():
            print(f"\n--- {category} ---")
            for i, food in enumerate(foods, 1):
                print(f"{i}. {food['food_name']} - {food['macros_summary']}")
        
        # Test 2: High Protein Foods
        print("\n" + "="*70)
        print("TEST 2: HIGH PROTEIN FOODS")
        print("="*70)
        print("Criteria: Minimum 15g protein per 100g")
        
        high_protein = retriever.get_high_protein_foods(
            db=db,
            min_protein=15.0,
            top_k=10
        )
        
        for i, food in enumerate(high_protein[:5], 1):
            print(f"\n{i}. {food['food_name']} ({food['category']})")
            print(f"   Protein: {food['protein_g']}g per 100g")
            print(f"   Dosha: {food['dosha_impact']}")
        
        # Test 3: Low Carb Foods
        print("\n" + "="*70)
        print("TEST 3: LOW CARB FOODS")
        print("="*70)
        print("Criteria: Maximum 10g carbs per 100g")
        
        low_carb = retriever.get_low_carb_foods(
            db=db,
            max_carbs=10.0,
            top_k=10
        )
        
        for i, food in enumerate(low_carb[:5], 1):
            print(f"\n{i}. {food['food_name']} ({food['category']})")
            print(f"   Carbs: {food['carbs_g']}g per 100g")
            print(f"   {food['macros_summary']}")
        
        # Test 4: Foods for Specific Dosha
        print("\n" + "="*70)
        print("TEST 4: FOODS FOR KAPHA DOSHA")
        print("="*70)
        print("Criteria: Foods that reduce Kapha (Kapha ↓)")
        
        kapha_foods = retriever.get_foods_by_dosha(
            db=db,
            dosha_impact="Kapha ↓",
            top_k=10
        )
        
        print(f"\nFound {len(kapha_foods)} Kapha-reducing foods:")
        for i, food in enumerate(kapha_foods[:5], 1):
            print(f"{i}. {food['food_name']} ({food['category']}) - {food['dosha_impact']}")
        
        # Test 5: Semantic Search with Filters
        print("\n" + "="*70)
        print("TEST 5: SEMANTIC SEARCH WITH NUTRITIONAL FILTERS")
        print("="*70)
        print("Query: 'foods for weight loss and energy'")
        print("Filters: High protein (>10g), Low carbs (<30g), Satvik only")
        
        weight_loss_foods = retriever.semantic_search(
            db=db,
            query="foods for weight loss and energy",
            min_protein=10.0,
            max_carbs=30.0,
            satvik_only=True,
            top_k=8
        )
        
        for i, food in enumerate(weight_loss_foods, 1):
            print(f"\n{i}. {food['food_name']}")
            print(f"   Category: {food['category']}")
            print(f"   {food['macros_summary']}")
            print(f"   Nature: {food['satvik_rajasik_tamasik']}")
            if 'relevance_score' in food:
                print(f"   Relevance: {food['relevance_score']:.3f}")
        
        # Test 6: Category Summary
        print("\n" + "="*70)
        print("TEST 6: CATEGORY SUMMARY")
        print("="*70)
        
        categories = retriever.get_all_categories(db)
        print(f"\nAll Categories ({len(categories)}):")
        for category in categories[:10]:  # Show first 10
            summary = retriever.get_category_summary(db, category)
            print(f"\n{category}:")
            print(f"  Total Foods: {summary['total_foods']}")
            print(f"  Avg Protein: {summary['avg_protein']:.1f}g")
            print(f"  Avg Carbs: {summary['avg_carbs']:.1f}g")
            print(f"  Highest Protein: {summary['max_protein_food']}")
        
        # Test 7: Best Foods from Each Major Category
        print("\n" + "="*70)
        print("TEST 7: COMPREHENSIVE DIET PLAN - BEST FOODS BY CATEGORY")
        print("="*70)
        print("User Goal: High protein, moderate carbs for muscle gain")
        
        comprehensive_results = retriever.get_best_foods_by_category(
            db=db,
            user_query="high protein foods for muscle gain with good micronutrients",
            categories=None,  # All categories
            min_protein=5.0,
            top_per_category=2
        )
        
        print(f"\nFound foods in {len(comprehensive_results)} categories:\n")
        
        for category, foods in sorted(comprehensive_results.items()):
            print(f"\n📋 {category}")
            for food in foods:
                print(f"  • {food['food_name']} - {food['macros_summary']}")
                print(f"    Micronutrients: {food['key_micronutrients']}")
        
        # Test 8: Context-aware Food Recommendations
        print("\n" + "="*70)
        print("TEST 8: CONTEXT-AWARE RECOMMENDATIONS")
        print("="*70)
        
        contexts = [
            {
                "query": "breakfast foods high in energy and protein",
                "dosha": "Kapha ↓",
                "min_protein": 8.0
            },
            {
                "query": "light dinner options for digestion",
                "satvik_only": True,
                "max_carbs": 20.0
            },
            {
                "query": "post-workout recovery foods",
                "min_protein": 12.0,
                "category": "Pulses"
            }
        ]
        
        for i, context in enumerate(contexts, 1):
            print(f"\nContext {i}: {context['query']}")
            
            results = retriever.semantic_search(
                db=db,
                query=context['query'],
                category=context.get('category'),
                dosha_preference=context.get('dosha'),
                min_protein=context.get('min_protein'),
                max_carbs=context.get('max_carbs'),
                satvik_only=context.get('satvik_only', False),
                top_k=3
            )
            
            for j, food in enumerate(results, 1):
                print(f"  {j}. {food['food_name']} - {food['macros_summary']}")
        
        print("\n" + "="*70)
        print("✓ All tests completed successfully!")
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error during tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

