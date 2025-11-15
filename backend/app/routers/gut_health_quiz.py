"""Gut Health Quiz management routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.gut_health_quiz import GutHealthQuiz
from app.models.client import Client
from app.models.user import User
from app.schemas.gut_health_quiz import (
    GutHealthQuiz as GutHealthQuizSchema,
    GutHealthQuizCreate,
    GutHealthQuizUpdate,
    GutHealthQuizWithClient,
    GutHealthQuizResult,
    GutHealthQuizQuestions
)
from app.utils.logger import logger
from app.routers.auth import get_current_active_user

router = APIRouter(prefix="/gut-health-quiz", tags=["Gut Health Quiz"])


# Quiz Questions Reference
QUIZ_QUESTIONS = [
    {
        "question_id": "gq1_appetite",
        "question": "How regular is your appetite each day?",
        "option_a": "Regular appetite at consistent times",
        "option_b": "Low appetite, sometimes skip meals",
        "option_c": "Very strong appetite, get irritable if delayed",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq2_digestion",
        "question": "After meals, how does your digestion feel?",
        "option_a": "Feel light and satisfied after eating",
        "option_b": "Feel bloated or heavy after meals",
        "option_c": "Experience acidity or burning after meals",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq3_bowel",
        "question": "How often do you have bowel movements?",
        "option_a": "Once daily, well-formed stool",
        "option_b": "Irregular, sometimes constipated",
        "option_c": "Loose stools or frequent urges",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq4_post_meal",
        "question": "How do you feel 1 hour after eating?",
        "option_a": "Energized and stable",
        "option_b": "Sleepy or tired after meals",
        "option_c": "Restless or anxious after meals",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq5_food_reaction",
        "question": "How does your body react to new or heavy foods?",
        "option_a": "Tolerate most foods well",
        "option_b": "Feel bloated or uneasy after new foods",
        "option_c": "Get acidity or quick reactions after certain foods",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq6_tongue_breath",
        "question": "Do you notice coating on your tongue or bad breath?",
        "option_a": "No coating, fresh breath",
        "option_b": "White coating, mild bad breath",
        "option_c": "Red tongue, sour or bitter taste",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq7_sleep",
        "question": "How do you sleep at night?",
        "option_a": "Deep, restful sleep",
        "option_b": "Sleep long but feel tired in the morning",
        "option_c": "Light, disturbed sleep",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq8_eating_habit",
        "question": "How do you usually eat your meals?",
        "option_a": "Eat mindfully without distractions",
        "option_b": "Eat quickly or while watching screens",
        "option_c": "Eat irregularly or skip meals often",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq9_bloating",
        "question": "When do you feel most bloated during the day?",
        "option_a": "Rarely feel bloated",
        "option_b": "Bloating after lunch or dinner",
        "option_c": "Bloating in the morning or after spicy foods",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    },
    {
        "question_id": "gq10_immunity",
        "question": "How strong is your immunity (how often do you fall sick)?",
        "option_a": "Strong immunity, rarely fall sick",
        "option_b": "Catch colds or infections easily",
        "option_c": "Occasionally get inflammation or skin breakouts",
        "state_a": "Balanced Gut",
        "state_b": "Weak Gut",
        "state_c": "Overactive Gut"
    }
]


@router.get("/questions", response_model=List[GutHealthQuizQuestions])
async def get_quiz_questions():
    """Get all gut health quiz questions."""
    return QUIZ_QUESTIONS


@router.get("/", response_model=List[GutHealthQuizSchema])
async def read_gut_health_quizzes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of all gut health quizzes."""
    quizzes = db.query(GutHealthQuiz).offset(skip).limit(limit).all()
    logger.info(f"User {current_user.username} retrieved {len(quizzes)} gut health quizzes")
    return quizzes


@router.get("/{quiz_id}", response_model=GutHealthQuizWithClient)
async def read_gut_health_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get gut health quiz by ID."""
    quiz = db.query(GutHealthQuiz).filter(GutHealthQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Gut health quiz not found")
    return quiz


@router.get("/{quiz_id}/result", response_model=GutHealthQuizResult)
async def get_gut_health_quiz_result(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed gut health quiz result with analysis."""
    quiz = db.query(GutHealthQuiz).filter(GutHealthQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Gut health quiz not found")
    
    result = GutHealthQuizResult(
        id=quiz.id,
        client_id=quiz.client_id,
        gut_health_state=quiz.gut_health_state,
        balanced_score=quiz.balanced_score,
        weak_score=quiz.weak_score,
        overactive_score=quiz.overactive_score,
        percentage=quiz.get_percentage(),
        quiz_responses=quiz.get_quiz_responses(),
        recommendations=quiz.get_recommendations(),
        notes=quiz.notes,
        created_at=quiz.created_at,
        updated_at=quiz.updated_at
    )
    return result


@router.get("/client/{client_id}", response_model=List[GutHealthQuizWithClient])
async def read_gut_health_quizzes_by_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all gut health quizzes for a specific client."""
    quizzes = db.query(GutHealthQuiz).filter(GutHealthQuiz.client_id == client_id).all()
    if not quizzes:
        raise HTTPException(status_code=404, detail="No gut health quizzes found for this client")
    return quizzes


@router.get("/client/{client_id}/latest", response_model=GutHealthQuizWithClient)
async def read_latest_gut_health_quiz_by_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the latest gut health quiz for a specific client."""
    quiz = db.query(GutHealthQuiz).filter(
        GutHealthQuiz.client_id == client_id
    ).order_by(GutHealthQuiz.created_at.desc()).first()
    
    if quiz is None:
        raise HTTPException(status_code=404, detail="No gut health quiz found for this client")
    return quiz


@router.post("/", response_model=GutHealthQuizSchema, status_code=status.HTTP_201_CREATED)
async def create_gut_health_quiz(
    quiz_in: GutHealthQuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit a new gut health quiz."""
    # Check if client exists
    client = db.query(Client).filter(Client.id == quiz_in.client_id).first()
    if not client:
        raise HTTPException(
            status_code=404,
            detail=f"Client with id {quiz_in.client_id} not found"
        )
    
    # Create new gut health quiz
    quiz = GutHealthQuiz(**quiz_in.model_dump())
    
    # Calculate gut health state and scores
    quiz.calculate_gut_health()
    
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    logger.info(
        f"User {current_user.username} created gut health quiz for client_id: {quiz.client_id}, "
        f"Result: {quiz.gut_health_state}"
    )
    return quiz


@router.put("/{quiz_id}", response_model=GutHealthQuizSchema)
async def update_gut_health_quiz(
    quiz_id: int,
    quiz_in: GutHealthQuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update gut health quiz."""
    quiz = db.query(GutHealthQuiz).filter(GutHealthQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Gut health quiz not found")
    
    # Update fields
    update_data = quiz_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quiz, field, value)
    
    # Recalculate gut health if any answers changed
    answer_fields = [f'gq{i}_' for i in range(1, 11)]
    if any(field.startswith(tuple(answer_fields)) for field in update_data.keys()):
        quiz.calculate_gut_health()
    
    db.commit()
    db.refresh(quiz)
    
    logger.info(f"User {current_user.username} updated gut health quiz id: {quiz.id}")
    return quiz


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gut_health_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete gut health quiz."""
    quiz = db.query(GutHealthQuiz).filter(GutHealthQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Gut health quiz not found")
    
    db.delete(quiz)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted gut health quiz id: {quiz.id}")
    return None


# Helper function for programmatic use
def submit_gut_health_quiz(
    client_id: int,
    quiz_data: dict,
    db: Session
) -> GutHealthQuiz:
    """
    Submit a gut health quiz for a client.
    This is a helper function for programmatic use.
    
    Args:
        client_id: The ID of the client
        quiz_data: Dictionary containing quiz responses
        db: Database session
    
    Returns:
        GutHealthQuiz: The created quiz with calculated results
    """
    quiz_data['client_id'] = client_id
    quiz = GutHealthQuiz(**quiz_data)
    quiz.calculate_gut_health()
    
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    return quiz


def get_client_latest_gut_health(client_id: int, db: Session) -> GutHealthQuiz:
    """
    Get the latest gut health quiz for a client.
    Helper function for programmatic use.
    
    Args:
        client_id: The ID of the client
        db: Database session
    
    Returns:
        GutHealthQuiz: The latest quiz or None if not found
    """
    return db.query(GutHealthQuiz).filter(
        GutHealthQuiz.client_id == client_id
    ).order_by(GutHealthQuiz.created_at.desc()).first()

