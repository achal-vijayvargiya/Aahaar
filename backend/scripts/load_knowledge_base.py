#!/usr/bin/env python3
"""
Load Nutrition Knowledge Base

This script loads nutrition data from JSON files into the knowledge base:
- Parses JSON data
- Stores in PostgreSQL database
- Creates vector embeddings
- Stores embeddings in ChromaDB

Usage:
    python backend/scripts/load_knowledge_base.py
    
    Options:
    --clear: Clear existing data before loading
    --file: Specify custom JSON file (default: Vaishnavi_Holistic_Nutrition_Notes.json)
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.knowledge_base.loader import NutritionKnowledgeLoader
from app.knowledge_base.retriever import NutritionRetriever
from app.utils.logger import logger


def main():
    """Main function to load knowledge base"""
    parser = argparse.ArgumentParser(description='Load nutrition knowledge base')
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing data before loading'
    )
    parser.add_argument(
        '--file',
        type=str,
        default='Vaishnavi_Holistic_Nutrition_Notes.json',
        help='JSON file to load (default: Vaishnavi_Holistic_Nutrition_Notes.json)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show knowledge base statistics after loading'
    )
    
    args = parser.parse_args()
    
    # Initialize database session
    db = SessionLocal()
    
    try:
        logger.info("=" * 70)
        logger.info("NUTRITION KNOWLEDGE BASE LOADER")
        logger.info("=" * 70)
        
        # Initialize loader
        loader = NutritionKnowledgeLoader()
        
        # Load and index data
        count = loader.index_data(
            db=db,
            filename=args.file,
            clear_existing=args.clear
        )
        
        logger.info("=" * 70)
        logger.info(f"✓ Successfully loaded {count} entries into knowledge base")
        logger.info("=" * 70)
        
        # Show statistics if requested
        if args.stats:
            logger.info("\n" + "=" * 70)
            logger.info("KNOWLEDGE BASE STATISTICS")
            logger.info("=" * 70)
            
            stats = loader.get_stats(db)
            logger.info(f"Total Entries: {stats['total_entries']}")
            logger.info(f"Vector Embeddings: {stats['vector_embeddings']}")
            logger.info(f"\nCategories ({len(stats['categories'])}):")
            for category in stats['categories']:
                logger.info(f"  - {category}")
            
            logger.info(f"\nDoshas ({len(stats['doshas'])}):")
            for dosha in stats['doshas']:
                logger.info(f"  - {dosha}")
            
            logger.info("=" * 70)
        
        # Test retrieval
        logger.info("\n" + "=" * 70)
        logger.info("TESTING RETRIEVAL")
        logger.info("=" * 70)
        
        retriever = NutritionRetriever()
        
        # Test semantic search
        test_query = "foods for diabetes and weight management"
        logger.info(f"\nTest Query: '{test_query}'")
        results = retriever.semantic_search(db, test_query, top_k=3)
        
        logger.info(f"\nTop {len(results)} Results:")
        for i, result in enumerate(results, 1):
            logger.info(f"\n{i}. {result['disorder_name']} ({result['category']})")
            if 'relevance_score' in result:
                logger.info(f"   Relevance: {result['relevance_score']:.2f}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ Knowledge base is ready to use!")
        logger.info("=" * 70)
        
    except FileNotFoundError as e:
        logger.error(f"✗ File not found: {e}")
        logger.error("Make sure the JSON file exists in backend/Resource/ directory")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Error loading knowledge base: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

