"""
Knowledge Base Retriever

Provides semantic search and filtered retrieval for nutrition knowledge
"""
import pickle
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from app.models.nutrition_knowledge import NutritionKnowledge
from app.utils.logger import logger


class NutritionRetriever:
    """
    Hybrid retrieval system combining:
    - Vector similarity search (FAISS)
    - Structured filtering (PostgreSQL)
    - Full-text search (PostgreSQL)
    """
    
    def __init__(self, faiss_path: str = "./kb_data/faiss"):
        self.faiss_path = Path(faiss_path)
        self.index_file = self.faiss_path / "nutrition_knowledge.index"
        self.metadata_file = self.faiss_path / "nutrition_metadata.pkl"
        
        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Load FAISS index if it exists
            self.index = None
            self.metadata = []
            
            if self.index_file.exists() and self.metadata_file.exists():
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                logger.warning("FAISS index not found. Run load_knowledge_base.py first.")
            
            logger.info("NutritionRetriever initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing NutritionRetriever: {e}")
            raise
    
    def semantic_search(
        self,
        db: Session,
        query: str,
        category: Optional[str] = None,
        dosha: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Semantic search using vector similarity
        
        Args:
            db: Database session
            query: Natural language query (e.g., "foods for diabetes and weight loss")
            category: Filter by category (e.g., "Metabolic & Endocrine")
            dosha: Filter by dosha (e.g., "Kapha")
            top_k: Number of results to return
        
        Returns:
            List of matching nutrition knowledge entries
        """
        logger.info(f"Semantic search: '{query}' (category={category}, dosha={dosha}, top_k={top_k})")
        
        if not self.index or not self.metadata:
            logger.warning("FAISS index not loaded. Run load_knowledge_base.py first.")
            return []
        
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode([query])
            query_embedding = np.array(query_embedding).astype('float32')
            
            # Search in FAISS (get more results for filtering)
            search_k = min(top_k * 3, len(self.metadata))
            distances, indices = self.index.search(query_embedding, search_k)
            
            # Get embedding IDs and filter
            embedding_ids = []
            relevance_scores = []
            
            for idx, distance in zip(indices[0], distances[0]):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                    
                metadata = self.metadata[idx]
                
                # Apply filters
                if category and metadata.get('category') != category:
                    continue
                if dosha and dosha not in metadata.get('dosha', ''):
                    continue
                
                embedding_ids.append(metadata['embedding_id'])
                # Convert L2 distance to similarity score (0-1, higher is better)
                relevance_scores.append(1.0 / (1.0 + distance))
                
                if len(embedding_ids) >= top_k:
                    break
            
            if not embedding_ids:
                logger.warning(f"No results found for query: {query}")
                return []
            
            # Fetch full records from PostgreSQL
            db_query = db.query(NutritionKnowledge).filter(
                NutritionKnowledge.embedding_id.in_(embedding_ids)
            )
            
            results = db_query.all()
            
            # Convert to dictionaries with relevance scores
            results_dict = []
            embedding_id_to_score = dict(zip(embedding_ids, relevance_scores))
            
            for result in results:
                result_dict = result.to_dict()
                result_dict['relevance_score'] = embedding_id_to_score.get(result.embedding_id, 0.0)
                results_dict.append(result_dict)
            
            # Sort by relevance score
            results_dict.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            logger.info(f"Found {len(results_dict)} results")
            return results_dict
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def filter_by_category(
        self,
        db: Session,
        category: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get all entries for a specific category"""
        logger.info(f"Filtering by category: {category}")
        
        results = db.query(NutritionKnowledge).filter(
            NutritionKnowledge.category == category
        ).limit(limit).all()
        
        return [result.to_dict() for result in results]
    
    def filter_by_dosha(
        self,
        db: Session,
        dosha: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get entries for a specific dosha"""
        logger.info(f"Filtering by dosha: {dosha}")
        
        results = db.query(NutritionKnowledge).filter(
            NutritionKnowledge.dosha_dominance.ilike(f"%{dosha}%")
        ).limit(limit).all()
        
        return [result.to_dict() for result in results]
    
    def get_by_disorder(
        self,
        db: Session,
        disorder_name: str
    ) -> Optional[Dict]:
        """Get specific disorder information by exact name"""
        logger.info(f"Getting disorder: {disorder_name}")
        
        result = db.query(NutritionKnowledge).filter(
            NutritionKnowledge.disorder_name == disorder_name
        ).first()
        
        return result.to_dict() if result else None
    
    def search_by_disorder_name(
        self,
        db: Session,
        search_term: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search disorders by partial name match"""
        logger.info(f"Searching disorders with term: {search_term}")
        
        results = db.query(NutritionKnowledge).filter(
            NutritionKnowledge.disorder_name.ilike(f"%{search_term}%")
        ).limit(limit).all()
        
        return [result.to_dict() for result in results]
    
    def fulltext_search(
        self,
        db: Session,
        search_query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Full-text search using PostgreSQL
        
        Good for keyword-based searches
        """
        logger.info(f"Full-text search: {search_query}")
        
        query = db.query(NutritionKnowledge).filter(
            NutritionKnowledge.search_vector.match(search_query)
        )
        
        if category:
            query = query.filter(NutritionKnowledge.category == category)
        
        results = query.limit(limit).all()
        return [result.to_dict() for result in results]
    
    def search_by_conditions(
        self,
        db: Session,
        conditions: List[str],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search by multiple health conditions
        
        Args:
            conditions: List of health conditions (e.g., ["diabetes", "obesity"])
        """
        logger.info(f"Searching by conditions: {conditions}")
        
        # Create a natural language query from conditions
        query = f"Nutritional guidance for: {', '.join(conditions)}"
        
        return self.semantic_search(db, query, top_k=top_k)
    
    def retrieve_for_diet_plan(
        self,
        db: Session,
        user_query: str,
        health_conditions: Optional[List[str]] = None,
        dietary_preferences: Optional[List[str]] = None,
        dosha: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 5
    ) -> Dict:
        """
        Comprehensive retrieval for diet plan generation
        
        Combines multiple search strategies to get the most relevant information
        
        Args:
            user_query: Natural language description of needs
            health_conditions: List of health conditions
            dietary_preferences: List of dietary preferences (vegetarian, etc.)
            dosha: Ayurvedic dosha preference
            category: Health category filter
            top_k: Number of results
        
        Returns:
            Dictionary with retrieved knowledge and metadata
        """
        logger.info(f"Retrieving for diet plan: query='{user_query}', conditions={health_conditions}")
        
        # Enhance query with conditions and preferences
        query_parts = [user_query]
        
        if health_conditions:
            query_parts.append(f"Health conditions: {', '.join(health_conditions)}")
        
        if dietary_preferences:
            query_parts.append(f"Dietary preferences: {', '.join(dietary_preferences)}")
        
        if dosha:
            query_parts.append(f"Dosha: {dosha}")
        
        enhanced_query = " | ".join(query_parts)
        
        # Perform semantic search
        main_results = self.semantic_search(
            db=db,
            query=enhanced_query,
            category=category,
            dosha=dosha,
            top_k=top_k
        )
        
        # Get additional context if health conditions specified
        condition_results = []
        if health_conditions:
            for condition in health_conditions[:2]:  # Limit to 2 conditions
                condition_matches = self.search_by_disorder_name(db, condition, limit=2)
                condition_results.extend(condition_matches)
        
        # Combine and deduplicate results
        all_results = main_results + condition_results
        seen_ids = set()
        unique_results = []
        
        for result in all_results:
            if result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                unique_results.append(result)
        
        return {
            "query": user_query,
            "enhanced_query": enhanced_query,
            "total_results": len(unique_results[:top_k]),
            "results": unique_results[:top_k],
            "metadata": {
                "health_conditions": health_conditions,
                "dietary_preferences": dietary_preferences,
                "dosha": dosha,
                "category": category
            }
        }
    
    def get_all_categories(self, db: Session) -> List[str]:
        """Get list of all available categories"""
        categories = db.query(NutritionKnowledge.category).distinct().all()
        return sorted([c[0] for c in categories if c[0]])
    
    def get_all_doshas(self, db: Session) -> List[str]:
        """Get list of all dosha types"""
        doshas = db.query(NutritionKnowledge.dosha_dominance).distinct().all()
        return sorted([d[0] for d in doshas if d[0]])
    
    def get_stats(self, db: Session) -> Dict:
        """Get knowledge base statistics"""
        total = db.query(NutritionKnowledge).count()
        categories = self.get_all_categories(db)
        doshas = self.get_all_doshas(db)
        
        # Category distribution
        category_counts = {}
        for category in categories:
            count = db.query(NutritionKnowledge).filter(
                NutritionKnowledge.category == category
            ).count()
            category_counts[category] = count
        
        return {
            "total_entries": total,
            "total_categories": len(categories),
            "categories": categories,
            "category_distribution": category_counts,
            "doshas": doshas,
            "vector_embeddings": self.index.ntotal if self.index else 0
        }

