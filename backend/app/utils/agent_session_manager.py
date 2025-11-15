"""
Client-specific Session Manager with Database Persistence

Manages AI agent sessions with:
- Client-specific isolation
- Database-backed chat history
- Security checks to prevent data leakage
- Automatic session restoration
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.utils.diet_plan_agent import DietPlanAgent
from app.models.agent_chat_history import AgentChatHistory, AgentChatSession
from app.utils.logger import logger


class DatabaseChatMessageHistory(BaseChatMessageHistory):
    """
    Custom chat history that stores messages in PostgreSQL.
    Compatible with LangChain's memory system.
    
    Provides:
    - Persistent storage across server restarts
    - Automatic message retrieval
    - Client-specific isolation
    """
    
    def __init__(self, session_id: str, db: Session, client_id: int, doctor_id: int):
        self.session_id = session_id
        self.db = db
        self.client_id = client_id
        self.doctor_id = doctor_id
        self._messages = None
    
    @property
    def messages(self):
        """Retrieve messages from database"""
        # Cache messages to avoid repeated DB queries
        if self._messages is None:
            self._messages = self._load_messages()
        return self._messages
    
    def _load_messages(self):
        """Load messages from database"""
        chat_history = self.db.query(AgentChatHistory).filter(
            AgentChatHistory.session_id == self.session_id
        ).order_by(AgentChatHistory.created_at.asc()).all()
        
        messages = []
        for record in chat_history:
            if record.role == 'user':
                messages.append(HumanMessage(content=record.message))
            else:
                messages.append(AIMessage(content=record.message))
        
        return messages
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to database"""
        role = 'user' if isinstance(message, HumanMessage) else 'assistant'
        
        chat_record = AgentChatHistory(
            client_id=self.client_id,
            doctor_id=self.doctor_id,
            session_id=self.session_id,
            role=role,
            message=message.content
        )
        
        self.db.add(chat_record)
        self.db.commit()
        
        # Invalidate cache
        self._messages = None
        
        logger.debug(f"Saved {role} message to session {self.session_id}")
    
    def add_messages(self, messages: list[BaseMessage]) -> None:
        """Add multiple messages"""
        for message in messages:
            self.add_message(message)
    
    def clear(self) -> None:
        """Clear all messages for this session"""
        self.db.query(AgentChatHistory).filter(
            AgentChatHistory.session_id == self.session_id
        ).delete()
        self.db.commit()
        
        # Invalidate cache
        self._messages = None
        
        logger.info(f"Cleared chat history for session {self.session_id}")


class ClientAgentSession:
    """
    Enhanced session container with client isolation and metadata.
    
    Wraps an agent instance with:
    - Session tracking
    - Client/doctor association
    - Stage management
    - Last accessed timestamp
    """
    
    def __init__(
        self, 
        agent: DietPlanAgent, 
        client_id: int,
        doctor_id: int,
        db: Session,
        session_record: AgentChatSession
    ):
        self.session_id = session_record.session_id
        self.agent = agent
        self.client_id = client_id
        self.doctor_id = doctor_id
        self.db = db
        self.session_record = session_record
        self.last_accessed = datetime.now()
    
    def touch(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now()
        self.session_record.updated_at = datetime.now()
        self.db.commit()
    
    def update_stage(self, stage: str):
        """Update session stage (initial, foods_retrieved, plan_generated)"""
        self.session_record.stage = stage
        self.db.commit()
        logger.info(f"Session {self.session_id} moved to stage: {stage}")
    
    def complete(self, diet_plan_id: Optional[int] = None):
        """Mark session as completed"""
        self.session_record.status = "completed"
        self.session_record.completed_at = datetime.now()
        if diet_plan_id:
            self.session_record.diet_plan_id = diet_plan_id
        self.db.commit()
        logger.info(f"Session {self.session_id} marked as completed")
    
    def get_context(self) -> dict:
        """Get current session context"""
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "doctor_id": self.doctor_id,
            "status": self.session_record.status,
            "stage": self.session_record.stage,
            "created_at": self.session_record.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat()
        }


class ClientAgentSessionManager:
    """
    Manages agent sessions with client-specific isolation.
    
    Features:
    - Creates new sessions tied to specific clients
    - Restores sessions from database
    - Enforces security (client/doctor verification)
    - Manages memory cache for active sessions
    - Auto-cleanup of expired sessions
    
    Architecture:
    - In-memory cache for fast access (self.sessions)
    - Database persistence for reliability
    - Lazy loading from DB when needed
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, ClientAgentSession] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        logger.info(f"ClientAgentSessionManager initialized (timeout: {session_timeout_minutes}m)")
    
    def create_session(
        self,
        db: Session,
        client_id: int,
        doctor_id: int,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.7
    ) -> str:
        """
        Create new client-specific session.
        
        Args:
            db: Database session
            client_id: ID of client this session is for
            doctor_id: ID of doctor creating the session
            api_key: OpenRouter API key
            model: LLM model to use
            temperature: LLM temperature
        
        Returns:
            session_id: UUID string for the new session
        """
        
        # Create session record in database
        session_id = str(uuid.uuid4())
        session_record = AgentChatSession(
            session_id=session_id,
            client_id=client_id,
            doctor_id=doctor_id,
            status="active",
            stage="initial"
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)
        
        # Create custom chat history backed by database
        chat_history = DatabaseChatMessageHistory(
            session_id=session_id,
            db=db,
            client_id=client_id,
            doctor_id=doctor_id
        )
        
        # Create agent with database-backed memory
        agent = DietPlanAgent(
            db=db,
            openrouter_api_key=api_key,
            model=model,
            temperature=temperature,
            chat_history=chat_history
        )
        
        # Store in memory cache
        session = ClientAgentSession(
            agent=agent,
            client_id=client_id,
            doctor_id=doctor_id,
            db=db,
            session_record=session_record
        )
        self.sessions[session_id] = session
        
        logger.info(f"Created session {session_id} for client {client_id} by doctor {doctor_id}")
        return session_id
    
    def get_session(
        self, 
        session_id: str, 
        client_id: int,
        doctor_id: int,
        db: Session,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.7
    ) -> Optional[ClientAgentSession]:
        """
        Get session with security checks.
        
        Security guarantees:
        - Session must belong to specified client
        - Session must have been created by specified doctor
        - Session must be active (not completed/abandoned)
        
        If session not in cache, restores from database.
        
        Args:
            session_id: UUID of the session
            client_id: Expected client ID
            doctor_id: Expected doctor ID
            db: Database session
            api_key: OpenRouter API key (for restoration)
            model: LLM model (for restoration)
            temperature: LLM temperature (for restoration)
        
        Returns:
            ClientAgentSession if found and authorized, None otherwise
        """
        
        # Check memory cache first
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Security: Verify client and doctor match
            if session.client_id != client_id:
                logger.warning(
                    f"Access denied: Session {session_id} belongs to client {session.client_id}, not {client_id}"
                )
                return None
            
            if session.doctor_id != doctor_id:
                logger.warning(
                    f"Access denied: Session {session_id} created by doctor {session.doctor_id}, not {doctor_id}"
                )
                return None
            
            session.touch()
            return session
        
        # Not in cache - check database and restore
        session_record = db.query(AgentChatSession).filter(
            AgentChatSession.session_id == session_id,
            AgentChatSession.client_id == client_id,
            AgentChatSession.doctor_id == doctor_id,
            AgentChatSession.status == "active"
        ).first()
        
        if not session_record:
            logger.warning(f"Session {session_id} not found or not active")
            return None
        
        # Restore agent from database
        chat_history = DatabaseChatMessageHistory(
            session_id=session_id,
            db=db,
            client_id=client_id,
            doctor_id=doctor_id
        )
        
        agent = DietPlanAgent(
            db=db,
            openrouter_api_key=api_key,
            model=model,
            temperature=temperature,
            chat_history=chat_history
        )
        
        session = ClientAgentSession(
            agent=agent,
            client_id=client_id,
            doctor_id=doctor_id,
            db=db,
            session_record=session_record
        )
        
        self.sessions[session_id] = session
        logger.info(f"Restored session {session_id} from database")
        return session
    
    def get_client_sessions(self, client_id: int, db: Session, limit: int = 10) -> list:
        """
        Get recent sessions for a specific client.
        
        Args:
            client_id: Client ID
            db: Database session
            limit: Maximum number of sessions to return
        
        Returns:
            List of session metadata dictionaries
        """
        sessions = db.query(AgentChatSession).filter(
            AgentChatSession.client_id == client_id
        ).order_by(AgentChatSession.created_at.desc()).limit(limit).all()
        
        return [s.to_dict() for s in sessions]
    
    def get_session_history(self, session_id: str, db: Session) -> list:
        """
        Get chat message history for a session.
        
        Args:
            session_id: Session ID
            db: Database session
        
        Returns:
            List of message dictionaries
        """
        messages = db.query(AgentChatHistory).filter(
            AgentChatHistory.session_id == session_id
        ).order_by(AgentChatHistory.created_at.asc()).all()
        
        return [msg.to_dict() for msg in messages]
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session from cache (database record remains for history).
        
        Args:
            session_id: Session ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Removed session {session_id} from cache")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove sessions that have been inactive too long"""
        now = datetime.now()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session.last_accessed > self.session_timeout
        ]
        
        for sid in expired:
            del self.sessions[sid]
            logger.info(f"Cleaned up expired session {sid}")
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def get_stats(self) -> dict:
        """Get session manager statistics"""
        return {
            "active_sessions_in_cache": len(self.sessions),
            "timeout_minutes": self.session_timeout.total_seconds() / 60,
            "sessions_by_client": self._count_by_client()
        }
    
    def _count_by_client(self) -> dict:
        """Count active sessions per client"""
        counts = {}
        for session in self.sessions.values():
            client_id = session.client_id
            counts[client_id] = counts.get(client_id, 0) + 1
        return counts


# Global session manager instance
_session_manager: Optional[ClientAgentSessionManager] = None


def get_session_manager() -> ClientAgentSessionManager:
    """
    Get or create global session manager.
    
    Singleton pattern ensures one manager across all requests.
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = ClientAgentSessionManager(session_timeout_minutes=30)
    return _session_manager

