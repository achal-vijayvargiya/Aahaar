#!/usr/bin/env python3
"""
Load Food Database

Loads Ahara Master Food Database into the knowledge base.

Usage:
    python scripts/load_food_database.py --clear --stats
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.knowledge_base.food_loader import FoodDatabaseLoader
from app.knowledge_base.food_retriever import FoodRetriever
from app.utils.logger import logger


def main():
    parser = argparse.ArgumentParser(description='Load food database')
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing food data before loading'
    )
    parser.add_argument(
        '--file',
        type=str,
        default='Ahara_Master_Food_Database_V1.0_770foods.json',
        help='JSON file to load'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics after loading'
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        logger.info("=" * 70)
        logger.info("FOOD DATABASE LOADER")
        logger.info("=" * 70)
        
        # Initialize loader
        loader = FoodDatabaseLoader()
        
        # Load and index data
        count = loader.index_data(
            db=db,
            filename=args.file,
            clear_existing=args.clear
        )
        
        logger.info("=" * 70)
        logger.info(f"✓ Successfully loaded {count} food items")
        logger.info("=" * 70)
        
        # Show statistics
        if args.stats:
            logger.info("\n" + "=" * 70)
            logger.info("FOOD DATABASE STATISTICS")
            logger.info("=" * 70)
            
            stats = loader.get_stats(db)
            logger.info(f"Total Food Items: {stats['total_food_items']}")
            logger.info(f"Vector Embeddings: {stats['vector_embeddings']}")
            
            logger.info(f"\nCategories ({len(stats['categories'])}):")
            for category in stats['categories']:
                logger.info(f"  - {category}")
            
            logger.info(f"\nDosha Impacts ({len(stats['dosha_impacts'])}):")
            for dosha in stats['dosha_impacts']:
                logger.info(f"  - {dosha}")
            
            logger.info("=" * 70)
        
        # Test retrieval
        logger.info("\n" + "=" * 70)
        logger.info("TESTING RETRIEVAL")
        logger.info("=" * 70)
        
        retriever = FoodRetriever()
        
        # Test high protein search
        test_query = "high protein foods for muscle building"
        logger.info(f"\nTest Query: '{test_query}'")
        results = retriever.semantic_search(db, test_query, top_k=5)
        
        logger.info(f"\nTop {len(results)} Results:")
        for i, result in enumerate(results, 1):
            logger.info(f"\n{i}. {result['food_name']} ({result['category']})")
            logger.info(f"   Macros: {result['macros_summary']}")
            logger.info(f"   Dosha: {result['dosha_impact']}")
            if 'relevance_score' in result:
                logger.info(f"   Relevance: {result['relevance_score']:.2f}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ Food database is ready to use!")
        logger.info("=" * 70)
        
    except FileNotFoundError as e:
        logger.error(f"✗ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Error loading food database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

