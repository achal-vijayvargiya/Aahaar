"""
Knowledge Base Module for Nutrition Information

This module provides functionality for:
- Loading nutrition data from JSON/Excel files
- Creating vector embeddings for semantic search (FAISS)
- Storing data in PostgreSQL with full-text search
- Retrieving relevant information based on queries
- Food database with nutritional and Ayurvedic properties
"""

from app.knowledge_base.loader import NutritionKnowledgeLoader
from app.knowledge_base.retriever import NutritionRetriever
from app.knowledge_base.food_loader import FoodDatabaseLoader
from app.knowledge_base.food_retriever import FoodRetriever

__all__ = [
    "NutritionKnowledgeLoader", 
    "NutritionRetriever",
    "FoodDatabaseLoader",
    "FoodRetriever"
]

