"""
Food Database Loader

Loads Ahara Master Food Database into PostgreSQL and FAISS
"""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from app.models.food_item import FoodItem
from app.utils.logger import logger


class FoodDatabaseLoader:
    """
    Loader for Ahara Master Food Database
    
    Features:
    - Loads JSON food data
    - Creates vector embeddings for semantic search
    - Stores in PostgreSQL with nutritional indexes
    - Stores embeddings in FAISS for similarity search
    """
    
    def __init__(self, data_dir: str = None, faiss_path: str = "./kb_data/faiss"):
        # Auto-detect Resource directory
        if data_dir is None:
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent.parent
            data_dir = backend_dir / "Resource"
            
            if not data_dir.exists():
                data_dir = Path("backend/Resource")
                if not data_dir.exists():
                    data_dir = Path("Resource")
        
        self.data_dir = Path(data_dir)
        self.faiss_path = Path(faiss_path)
        self.faiss_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize FAISS index path for foods
        self.index_file = self.faiss_path / "food_items.index"
        self.metadata_file = self.faiss_path / "food_metadata.pkl"
        
        logger.info(f"Food data directory: {self.data_dir.resolve()}")
        
        # Initialize embedding model
        logger.info("Loading sentence transformer model for foods...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully")
        
        self.index = None
        self.embedding_dimension = 384
    
    def load_json_file(self, filename: str) -> List[Dict]:
        """Load food data from JSON file"""
        filepath = self.data_dir / filename
        logger.info(f"Looking for food file: {filepath.resolve()}")
        
        if not filepath.exists():
            alternative_paths = [
                Path("backend/Resource") / filename,
                Path("Resource") / filename,
                Path(".") / filename,
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    filepath = alt_path
                    logger.info(f"Found file at: {filepath.resolve()}")
                    break
            else:
                raise FileNotFoundError(f"File not found: {filepath}")
        
        logger.info(f"Loading food JSON file: {filepath.resolve()}")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} food items from {filename}")
        return data
    
    def create_searchable_text(self, item: Dict) -> str:
        """
        Create rich text representation for embedding
        
        Combines name, category, nutritional info, and Ayurvedic properties
        """
        parts = []
        
        # Basic info
        if item.get('Food Name'):
            parts.append(f"Food: {item['Food Name']}")
        if item.get('Category'):
            parts.append(f"Category: {item['Category']}")
        
        # Nutritional info
        if item.get('Energy_kcal_per_100g'):
            parts.append(f"Energy: {item['Energy_kcal_per_100g']} kcal")
        if item.get('Protein_g_per_100g'):
            parts.append(f"Protein: {item['Protein_g_per_100g']}g")
        if item.get('Carbs_g_per_100g'):
            parts.append(f"Carbs: {item['Carbs_g_per_100g']}g")
        if item.get('Fat_g_per_100g'):
            parts.append(f"Fat: {item['Fat_g_per_100g']}g")
        
        # Micronutrients
        if item.get('Key_Micronutrients'):
            parts.append(f"Micronutrients: {item['Key_Micronutrients']}")
        
        # Ayurvedic properties
        if item.get('Dosha_Impact'):
            parts.append(f"Dosha: {item['Dosha_Impact']}")
        if item.get('Satvik_Rajasik_Tamasik'):
            parts.append(f"Nature: {item['Satvik_Rajasik_Tamasik']}")
        if item.get('Gut_Biotic_Value'):
            parts.append(f"Gut: {item['Gut_Biotic_Value']}")
        
        # Region
        if item.get('Region'):
            parts.append(f"Region: {item['Region']}")
        
        return " | ".join(parts)
    
    def clear_existing_data(self, db: Session):
        """Clear existing food data"""
        logger.info("Clearing existing food database...")
        
        # Clear PostgreSQL
        db.query(FoodItem).delete()
        db.commit()
        
        # Clear FAISS files
        try:
            if self.index_file.exists():
                self.index_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
        except Exception as e:
            logger.warning(f"Could not clear FAISS files: {e}")
        
        logger.info("Existing food data cleared")
    
    def index_data(
        self,
        db: Session,
        filename: str = "Ahara_Master_Food_Database_V1.0_770foods.json",
        clear_existing: bool = False
    ):
        """
        Load and index food data into PostgreSQL and FAISS
        """
        if clear_existing:
            self.clear_existing_data(db)
        
        # Load JSON data
        data = self.load_json_file(filename)
        
        logger.info(f"Indexing {len(data)} food items...")
        
        documents = []
        metadatas = []
        db_entries = []
        
        for idx, item in enumerate(data):
            try:
                embedding_id = f"food_{idx:04d}"
                
                # Create PostgreSQL record
                db_entry = FoodItem(
                    food_name=item.get("Food Name", ""),
                    category=item.get("Category", ""),
                    serving_size=item.get("Serving Size", ""),
                    region=item.get("Region", ""),
                    energy_kcal=item.get("Energy_kcal_per_100g"),
                    protein_g=item.get("Protein_g_per_100g"),
                    fat_g=item.get("Fat_g_per_100g"),
                    carbs_g=item.get("Carbs_g_per_100g"),
                    key_micronutrients=item.get("Key_Micronutrients", ""),
                    dosha_impact=item.get("Dosha_Impact", ""),
                    satvik_rajasik_tamasik=item.get("Satvik_Rajasik_Tamasik", ""),
                    gut_biotic_value=item.get("Gut_Biotic_Value", ""),
                    embedding_id=embedding_id
                )
                db_entries.append(db_entry)
                
                # Prepare for vector store
                searchable_text = self.create_searchable_text(item)
                documents.append(searchable_text)
                
                metadatas.append({
                    "category": item.get("Category", ""),
                    "food_name": item.get("Food Name", ""),
                    "dosha": item.get("Dosha_Impact", ""),
                    "protein_g": item.get("Protein_g_per_100g", 0),
                    "embedding_id": embedding_id
                })
                
            except Exception as e:
                logger.error(f"Error processing food item {idx}: {e}")
                continue
        
        # Bulk insert to PostgreSQL
        logger.info(f"Inserting {len(db_entries)} food items to PostgreSQL...")
        db.bulk_save_objects(db_entries)
        db.commit()
        logger.info("✓ Food data inserted to PostgreSQL")
        
        # Create full-text search vectors
        self._create_search_vectors(db)
        
        # Create FAISS index
        logger.info("Creating embeddings and FAISS index for foods...")
        if documents:
            embeddings = self.embedding_model.encode(documents, show_progress_bar=True)
            embeddings = np.array(embeddings).astype('float32')
            
            self.index = faiss.IndexFlatL2(self.embedding_dimension)
            self.index.add(embeddings)
            
            faiss.write_index(self.index, str(self.index_file))
            
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(metadatas, f)
            
            logger.info(f"✓ Created and stored embeddings for {len(documents)} food items")
            logger.info(f"✓ FAISS index saved to {self.index_file}")
        
        logger.info("✓ Food database indexed successfully!")
        return len(db_entries)
    
    def _create_search_vectors(self, db: Session):
        """Create PostgreSQL full-text search vectors"""
        logger.info("Creating full-text search vectors for foods...")
        
        try:
            db.execute("""
                UPDATE food_items
                SET search_vector = 
                    to_tsvector('english', 
                        COALESCE(food_name, '') || ' ' ||
                        COALESCE(category, '') || ' ' ||
                        COALESCE(key_micronutrients, '') || ' ' ||
                        COALESCE(dosha_impact, '') || ' ' ||
                        COALESCE(region, '')
                    )
                WHERE search_vector IS NULL
            """)
            db.commit()
            logger.info("✓ Full-text search vectors created for foods")
        except Exception as e:
            logger.error(f"Error creating search vectors: {e}")
            db.rollback()
    
    def get_stats(self, db: Session) -> Dict:
        """Get food database statistics"""
        total_items = db.query(FoodItem).count()
        categories = db.query(FoodItem.category).distinct().all()
        doshas = db.query(FoodItem.dosha_impact).distinct().all()
        
        # Get FAISS stats
        faiss_count = 0
        if self.index_file.exists():
            try:
                index = faiss.read_index(str(self.index_file))
                faiss_count = index.ntotal
            except Exception as e:
                logger.warning(f"Could not read FAISS index: {e}")
        
        return {
            "total_food_items": total_items,
            "categories": sorted([c[0] for c in categories if c[0]]),
            "dosha_impacts": sorted([d[0] for d in doshas if d[0]]),
            "vector_embeddings": faiss_count
        }

