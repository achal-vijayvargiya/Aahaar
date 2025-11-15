"""
Food Database Retriever

Provides intelligent food recommendation based on user requirements
"""
import pickle
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from app.models.food_item import FoodItem
from app.utils.logger import logger


class FoodRetriever:
    """
    Intelligent food retrieval system combining:
    - Vector similarity search (FAISS)
    - Nutritional filtering (protein, carbs, fat)
    - Dosha-based filtering
    - Category-based grouping
    """
    
    def __init__(self, faiss_path: str = "./kb_data/faiss"):
        self.faiss_path = Path(faiss_path)
        self.index_file = self.faiss_path / "food_items.index"
        self.metadata_file = self.faiss_path / "food_metadata.pkl"
        
        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Load FAISS index
            self.index = None
            self.metadata = []
            
            if self.index_file.exists() and self.metadata_file.exists():
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                logger.info(f"Loaded food FAISS index with {self.index.ntotal} vectors")
            else:
                logger.warning("Food FAISS index not found. Run load_food_database.py first.")
            
            logger.info("FoodRetriever initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing FoodRetriever: {e}")
            raise
    
    def get_best_foods_by_category(
        self,
        db: Session,
        user_query: str,
        categories: Optional[List[str]] = None,
        dosha_preference: Optional[str] = None,
        min_protein: Optional[float] = None,
        max_carbs: Optional[float] = None,
        top_per_category: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Get best foods from each category based on user requirements
        
        Args:
            user_query: Natural language description (e.g., "high protein foods for muscle building")
            categories: List of specific categories to include (None = all categories)
            dosha_preference: Dosha to favor (e.g., "Kapha ↓")
            min_protein: Minimum protein per 100g
            max_carbs: Maximum carbs per 100g
            top_per_category: Number of foods to return per category
        
        Returns:
            Dictionary mapping category names to lists of food items
        """
        logger.info(f"Finding best foods by category for: '{user_query}'")
        
        # Get all categories
        if categories is None:
            category_results = db.query(FoodItem.category).distinct().all()
            categories = [c[0] for c in category_results if c[0]]
        
        results_by_category = {}
        
        for category in categories:
            # Search for foods in this category
            foods = self.semantic_search(
                db=db,
                query=user_query,
                category=category,
                dosha_preference=dosha_preference,
                min_protein=min_protein,
                max_carbs=max_carbs,
                top_k=top_per_category
            )
            
            if foods:
                results_by_category[category] = foods
        
        logger.info(f"Found foods in {len(results_by_category)} categories")
        return results_by_category
    
    def semantic_search(
        self,
        db: Session,
        query: str,
        category: Optional[str] = None,
        dosha_preference: Optional[str] = None,
        min_protein: Optional[float] = None,
        max_protein: Optional[float] = None,
        min_carbs: Optional[float] = None,
        max_carbs: Optional[float] = None,
        min_fat: Optional[float] = None,
        max_fat: Optional[float] = None,
        satvik_only: bool = False,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Semantic search for foods with nutritional filters
        """
        logger.info(f"Semantic search for foods: '{query}' (category={category})")
        
        if not self.index or not self.metadata:
            logger.warning("FAISS index not loaded. Falling back to database query.")
            return self._database_fallback(
                db, category, dosha_preference, min_protein, max_protein,
                min_carbs, max_carbs, min_fat, max_fat, satvik_only, top_k
            )
        
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode([query])
            query_embedding = np.array(query_embedding).astype('float32')
            
            # Search in FAISS
            search_k = min(top_k * 5, len(self.metadata))
            distances, indices = self.index.search(query_embedding, search_k)
            
            # Get embedding IDs and filter
            embedding_ids = []
            relevance_scores = []
            
            for idx, distance in zip(indices[0], distances[0]):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                
                metadata = self.metadata[idx]
                
                # Apply category filter
                if category and metadata.get('category') != category:
                    continue
                
                # Apply dosha filter
                if dosha_preference and dosha_preference not in metadata.get('dosha', ''):
                    continue
                
                embedding_ids.append(metadata['embedding_id'])
                relevance_scores.append(1.0 / (1.0 + distance))
                
                if len(embedding_ids) >= top_k * 2:  # Get extra for nutritional filtering
                    break
            
            if not embedding_ids:
                logger.warning("No results after filtering")
                return []
            
            # Fetch from database with nutritional filters
            db_query = db.query(FoodItem).filter(
                FoodItem.embedding_id.in_(embedding_ids)
            )
            
            # Apply nutritional filters
            if min_protein is not None:
                db_query = db_query.filter(FoodItem.protein_g >= min_protein)
            if max_protein is not None:
                db_query = db_query.filter(FoodItem.protein_g <= max_protein)
            if min_carbs is not None:
                db_query = db_query.filter(FoodItem.carbs_g >= min_carbs)
            if max_carbs is not None:
                db_query = db_query.filter(FoodItem.carbs_g <= max_carbs)
            if min_fat is not None:
                db_query = db_query.filter(FoodItem.fat_g >= min_fat)
            if max_fat is not None:
                db_query = db_query.filter(FoodItem.fat_g <= max_fat)
            if satvik_only:
                db_query = db_query.filter(FoodItem.satvik_rajasik_tamasik == 'Satvik')
            
            results = db_query.limit(top_k).all()
            
            # Add relevance scores
            results_dict = []
            embedding_id_to_score = dict(zip(embedding_ids, relevance_scores))
            
            for result in results:
                result_dict = result.to_dict()
                result_dict['relevance_score'] = embedding_id_to_score.get(result.embedding_id, 0.0)
                result_dict['macros_summary'] = result.get_macros_summary()
                results_dict.append(result_dict)
            
            # Sort by relevance
            results_dict.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            logger.info(f"Found {len(results_dict)} food results")
            return results_dict
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def _database_fallback(
        self, db, category, dosha, min_protein, max_protein,
        min_carbs, max_carbs, min_fat, max_fat, satvik_only, top_k
    ):
        """Fallback to database query when FAISS not available"""
        query = db.query(FoodItem)
        
        if category:
            query = query.filter(FoodItem.category == category)
        if dosha:
            query = query.filter(FoodItem.dosha_impact.ilike(f"%{dosha}%"))
        if min_protein is not None:
            query = query.filter(FoodItem.protein_g >= min_protein)
        if max_protein is not None:
            query = query.filter(FoodItem.protein_g <= max_protein)
        if min_carbs is not None:
            query = query.filter(FoodItem.carbs_g >= min_carbs)
        if max_carbs is not None:
            query = query.filter(FoodItem.carbs_g <= max_carbs)
        if min_fat is not None:
            query = query.filter(FoodItem.fat_g >= min_fat)
        if max_fat is not None:
            query = query.filter(FoodItem.fat_g <= max_fat)
        if satvik_only:
            query = query.filter(FoodItem.satvik_rajasik_tamasik == 'Satvik')
        
        results = query.limit(top_k).all()
        return [r.to_dict() for r in results]
    
    def get_high_protein_foods(
        self,
        db: Session,
        min_protein: float = 15.0,
        category: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """Get foods high in protein"""
        query = db.query(FoodItem).filter(FoodItem.protein_g >= min_protein)
        
        if category:
            query = query.filter(FoodItem.category == category)
        
        results = query.order_by(FoodItem.protein_g.desc()).limit(top_k).all()
        return [r.to_dict() for r in results]
    
    def get_low_carb_foods(
        self,
        db: Session,
        max_carbs: float = 20.0,
        category: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """Get low carbohydrate foods"""
        query = db.query(FoodItem).filter(FoodItem.carbs_g <= max_carbs)
        
        if category:
            query = query.filter(FoodItem.category == category)
        
        results = query.order_by(FoodItem.carbs_g.asc()).limit(top_k).all()
        return [r.to_dict() for r in results]
    
    def get_foods_by_dosha(
        self,
        db: Session,
        dosha_impact: str,
        category: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Get foods for specific dosha impact
        
        Args:
            dosha_impact: e.g., "Kapha ↓", "Vata ↓", "Pitta ↓"
        """
        query = db.query(FoodItem).filter(
            FoodItem.dosha_impact.ilike(f"%{dosha_impact}%")
        )
        
        if category:
            query = query.filter(FoodItem.category == category)
        
        results = query.limit(top_k).all()
        return [r.to_dict() for r in results]
    
    def get_all_categories(self, db: Session) -> List[str]:
        """Get list of all food categories"""
        categories = db.query(FoodItem.category).distinct().all()
        return sorted([c[0] for c in categories if c[0]])
    
    def get_category_summary(self, db: Session, category: str) -> Dict:
        """Get summary statistics for a category"""
        foods = db.query(FoodItem).filter(FoodItem.category == category).all()
        
        if not foods:
            return {"error": "Category not found"}
        
        proteins = [f.protein_g for f in foods if f.protein_g is not None]
        carbs = [f.carbs_g for f in foods if f.carbs_g is not None]
        fats = [f.fat_g for f in foods if f.fat_g is not None]
        
        return {
            "category": category,
            "total_foods": len(foods),
            "avg_protein": sum(proteins) / len(proteins) if proteins else 0,
            "avg_carbs": sum(carbs) / len(carbs) if carbs else 0,
            "avg_fat": sum(fats) / len(fats) if fats else 0,
            "max_protein_food": max(foods, key=lambda x: x.protein_g or 0).food_name if proteins else None,
            "min_carb_food": min(foods, key=lambda x: x.carbs_g or float('inf')).food_name if carbs else None
        }
    
    def get_stats(self, db: Session) -> Dict:
        """Get food database statistics"""
        total = db.query(FoodItem).count()
        categories = self.get_all_categories(db)
        
        return {
            "total_food_items": total,
            "total_categories": len(categories),
            "categories": categories,
            "vector_embeddings": self.index.ntotal if self.index else 0
        }

