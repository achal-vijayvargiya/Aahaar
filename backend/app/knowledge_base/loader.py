"""
Knowledge Base Loader

Loads nutrition data from JSON files into PostgreSQL and FAISS
"""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from app.models.nutrition_knowledge import NutritionKnowledge
from app.utils.logger import logger


class NutritionKnowledgeLoader:
    """
    Loader for nutrition knowledge base data
    
    Features:
    - Loads JSON data files
    - Creates vector embeddings using sentence-transformers
    - Stores in PostgreSQL with full-text search
    - Stores embeddings in FAISS for semantic search
    """
    
    def __init__(self, data_dir: str = None, faiss_path: str = "./kb_data/faiss"):
        # Auto-detect Resource directory
        if data_dir is None:
            # Try to find Resource directory relative to this file
            current_file = Path(__file__).resolve()
            # Go up to backend directory
            backend_dir = current_file.parent.parent.parent
            data_dir = backend_dir / "Resource"
            
            # If that doesn't exist, try other common locations
            if not data_dir.exists():
                # Try from current working directory
                data_dir = Path("backend/Resource")
                if not data_dir.exists():
                    data_dir = Path("Resource")
        
        self.data_dir = Path(data_dir)
        self.faiss_path = Path(faiss_path)
        self.faiss_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize FAISS index path
        self.index_file = self.faiss_path / "nutrition_knowledge.index"
        self.metadata_file = self.faiss_path / "nutrition_metadata.pkl"
        
        # Log the data directory being used
        logger.info(f"Data directory: {self.data_dir.resolve()}")
        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir.resolve()}")
        
        # Initialize embedding model (runs locally, no API needed)
        logger.info("Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully")
        
        # FAISS index (will be created during indexing)
        self.index = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
    
    def load_json_file(self, filename: str) -> List[Dict]:
        """Load data from JSON file"""
        filepath = self.data_dir / filename
        logger.info(f"Looking for file: {filepath.resolve()}")
        
        if not filepath.exists():
            # Try to find the file in alternative locations
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
                logger.error(f"File not found: {filepath.resolve()}")
                logger.error("Tried locations:")
                logger.error(f"  - {filepath.resolve()}")
                for alt in alternative_paths:
                    logger.error(f"  - {alt.resolve()}")
                raise FileNotFoundError(f"File not found: {filepath}")
        
        logger.info(f"Loading JSON file: {filepath.resolve()}")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} entries from {filename}")
        return data
    
    def create_searchable_text(self, entry: Dict) -> str:
        """
        Create rich text representation for embedding
        
        Combines all relevant fields into a comprehensive text
        that captures the semantic meaning of the entry
        """
        parts = []
        
        # Main identification
        if entry.get('Disorder Name'):
            parts.append(f"Condition: {entry['Disorder Name']}")
        if entry.get('Category'):
            parts.append(f"Category: {entry['Category']}")
        
        # Clinical information
        if entry.get('Definition / Etiology'):
            parts.append(f"Definition: {entry['Definition / Etiology']}")
        if entry.get('Clinical Goals'):
            parts.append(f"Clinical Goals: {entry['Clinical Goals']}")
        
        # MNT Details (Medical Nutrition Therapy)
        if entry.get('MNT - Macronutrients'):
            parts.append(f"Macronutrients: {entry['MNT - Macronutrients']}")
        if entry.get('MNT - Micronutrients'):
            parts.append(f"Micronutrients: {entry['MNT - Micronutrients']}")
        if entry.get('MNT - Special Notes'):
            parts.append(f"Special Notes: {entry['MNT - Special Notes']}")
        
        # Ayurvedic perspective
        if entry.get('Ayurvedic View'):
            parts.append(f"Ayurvedic View: {entry['Ayurvedic View']}")
        if entry.get('Dosha Dominance'):
            parts.append(f"Dosha: {entry['Dosha Dominance']}")
        
        # Lifestyle guidance
        if entry.get('Lifestyle & Yogic Guidance'):
            parts.append(f"Lifestyle: {entry['Lifestyle & Yogic Guidance']}")
        
        return " | ".join(parts)
    
    def clear_existing_data(self, db: Session):
        """Clear existing data from database and vector store"""
        logger.info("Clearing existing nutrition knowledge data...")
        
        # Clear PostgreSQL
        db.query(NutritionKnowledge).delete()
        db.commit()
        
        # Clear FAISS index files
        try:
            if self.index_file.exists():
                self.index_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
        except Exception as e:
            logger.warning(f"Could not clear FAISS files: {e}")
        
        logger.info("Existing data cleared")
    
    def index_data(
        self, 
        db: Session, 
        filename: str = "Vaishnavi_Holistic_Nutrition_Notes.json",
        clear_existing: bool = False
    ):
        """
        Load and index data into both PostgreSQL and ChromaDB
        
        Args:
            db: Database session
            filename: JSON file to load
            clear_existing: Whether to clear existing data first
        """
        if clear_existing:
            self.clear_existing_data(db)
        
        # Load JSON data
        data = self.load_json_file(filename)
        
        logger.info(f"Indexing {len(data)} nutrition knowledge entries...")
        
        documents = []
        metadatas = []
        db_entries = []
        
        for idx, entry in enumerate(data):
            try:
                # Create unique embedding ID
                embedding_id = f"nutrition_{idx:04d}"
                
                # Create PostgreSQL record
                db_entry = NutritionKnowledge(
                    category=entry.get("Category", ""),
                    disorder_name=entry.get("Disorder Name", ""),
                    definition_etiology=entry.get("Definition / Etiology", ""),
                    clinical_goals=entry.get("Clinical Goals", ""),
                    mnt_macronutrients=entry.get("MNT - Macronutrients", ""),
                    mnt_micronutrients=entry.get("MNT - Micronutrients", ""),
                    mnt_fluids_electrolytes=entry.get("MNT - Fluids & Electrolytes", ""),
                    mnt_special_notes=entry.get("MNT - Special Notes", ""),
                    ayurvedic_view=entry.get("Ayurvedic View", ""),
                    dosha_dominance=entry.get("Dosha Dominance", ""),
                    lifestyle_yogic_guidance=entry.get("Lifestyle & Yogic Guidance", ""),
                    healing_affirmation=entry.get("Healing Affirmation", ""),
                    embedding_id=embedding_id
                )
                db_entries.append(db_entry)
                
                # Prepare for vector store
                searchable_text = self.create_searchable_text(entry)
                documents.append(searchable_text)
                
                metadatas.append({
                    "category": entry.get("Category", ""),
                    "disorder_name": entry.get("Disorder Name", ""),
                    "dosha": entry.get("Dosha Dominance", ""),
                    "embedding_id": embedding_id
                })
                
            except Exception as e:
                logger.error(f"Error processing entry {idx}: {e}")
                continue
        
        # Bulk insert to PostgreSQL
        logger.info(f"Inserting {len(db_entries)} entries to PostgreSQL...")
        db.bulk_save_objects(db_entries)
        db.commit()
        logger.info("✓ Data inserted to PostgreSQL")
        
        # Create full-text search vectors
        self._create_search_vectors(db)
        
        # Create FAISS index and add embeddings
        logger.info("Creating embeddings and FAISS index...")
        if documents:
            # Create embeddings
            embeddings = self.embedding_model.encode(documents, show_progress_bar=True)
            embeddings = np.array(embeddings).astype('float32')
            
            # Create FAISS index
            self.index = faiss.IndexFlatL2(self.embedding_dimension)
            self.index.add(embeddings)
            
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(metadatas, f)
            
            logger.info(f"✓ Created and stored embeddings for {len(documents)} entries")
            logger.info(f"✓ FAISS index saved to {self.index_file}")
        
        logger.info("✓ Knowledge base indexed successfully!")
        return len(db_entries)
    
    def _create_search_vectors(self, db: Session):
        """Create PostgreSQL full-text search vectors"""
        logger.info("Creating full-text search vectors...")
        
        try:
            db.execute("""
                UPDATE nutrition_knowledge
                SET search_vector = 
                    to_tsvector('english', 
                        COALESCE(disorder_name, '') || ' ' ||
                        COALESCE(category, '') || ' ' ||
                        COALESCE(definition_etiology, '') || ' ' ||
                        COALESCE(clinical_goals, '') || ' ' ||
                        COALESCE(mnt_macronutrients, '') || ' ' ||
                        COALESCE(mnt_micronutrients, '') || ' ' ||
                        COALESCE(mnt_special_notes, '') || ' ' ||
                        COALESCE(ayurvedic_view, '') || ' ' ||
                        COALESCE(dosha_dominance, '') || ' ' ||
                        COALESCE(lifestyle_yogic_guidance, '')
                    )
                WHERE search_vector IS NULL
            """)
            db.commit()
            logger.info("✓ Full-text search vectors created")
        except Exception as e:
            logger.error(f"Error creating search vectors: {e}")
            db.rollback()
    
    def get_stats(self, db: Session) -> Dict:
        """Get statistics about the knowledge base"""
        total_entries = db.query(NutritionKnowledge).count()
        categories = db.query(NutritionKnowledge.category).distinct().all()
        doshas = db.query(NutritionKnowledge.dosha_dominance).distinct().all()
        
        # Get FAISS stats
        faiss_count = 0
        if self.index_file.exists():
            try:
                index = faiss.read_index(str(self.index_file))
                faiss_count = index.ntotal
            except Exception as e:
                logger.warning(f"Could not read FAISS index: {e}")
        
        return {
            "total_entries": total_entries,
            "categories": [c[0] for c in categories],
            "doshas": [d[0] for d in doshas if d[0]],
            "vector_embeddings": faiss_count
        }

