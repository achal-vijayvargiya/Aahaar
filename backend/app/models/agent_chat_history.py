"""
Agent Chat History Model

Stores conversation history between AI agent and doctor for each client.
This enables:
- Persistent conversations across sessions
- Review of past interactions
- Data isolation per client
- Audit trail for diet plan decisions
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class AgentChatHistory(Base):
    """
    Stores individual messages in agent conversations.
    
    Each client can have multiple sessions, each session has multiple messages.
    """
    __tablename__ = "agent_chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Session tracking
    session_id = Column(String(100), nullable=False, index=True)
    
    # Message data
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message = Column(Text, nullable=False)
    
    # Metadata
    tool_calls = Column(JSON)  # Which tools were called (if assistant message)
    intermediate_steps = Column(JSON)  # Tool results
    context_snapshot = Column(JSON)  # Stage, foods retrieved, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    client = relationship("Client", backref="chat_history")
    doctor = relationship("User", backref="agent_chats", foreign_keys=[doctor_id])
    
    __table_args__ = (
        Index('idx_client_session', 'client_id', 'session_id'),
        Index('idx_session_created', 'session_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AgentChatHistory(client={self.client_id}, role={self.role})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "doctor_id": self.doctor_id,
            "session_id": self.session_id,
            "role": self.role,
            "message": self.message,
            "tool_calls": self.tool_calls,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AgentChatSession(Base):
    """
    Tracks agent chat sessions (one session per diet plan creation).
    """
    __tablename__ = "agent_chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Session metadata
    status = Column(String(50), default="active")  # active, completed, abandoned
    stage = Column(String(50), default="initial")  # initial, foods_retrieved, plan_generated
    
    # Results
    diet_plan_id = Column(Integer, ForeignKey("diet_plans.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship("Client", backref="agent_sessions")
    doctor = relationship("User", backref="agent_sessions", foreign_keys=[doctor_id])
    diet_plan = relationship("DietPlan", backref="agent_session")
    
    def __repr__(self):
        return f"<AgentChatSession(client={self.client_id}, status={self.status})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "client_id": self.client_id,
            "doctor_id": self.doctor_id,
            "status": self.status,
            "stage": self.stage,
            "diet_plan_id": self.diet_plan_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

