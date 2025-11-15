"""Dosha Quiz management routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dosha_quiz import DoshaQuiz
from app.models.client import Client
from app.models.user import User
from app.schemas.dosha_quiz import (
    DoshaQuiz as DoshaQuizSchema,
    DoshaQuizCreate,
    DoshaQuizUpdate,
    DoshaQuizWithClient,
    DoshaQuizResult,
    DoshaQuizQuestions
)
from app.utils.logger import logger
from app.routers.auth import get_current_active_user

router = APIRouter(prefix="/dosha-quiz", tags=["Dosha Quiz"])


# Quiz Questions Reference
QUIZ_QUESTIONS = [
    {
        "question_id": "q1_body_frame",
        "question": "Body Frame & Build",
        "option_a": "Slim, light, find it hard to gain weight",
        "option_b": "Medium build, athletic, gain and lose weight easily",
        "option_c": "Broad, strong, tend to gain weight easily",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q2_skin_type",
        "question": "Skin Type",
        "option_a": "Dry, rough, prone to flakiness",
        "option_b": "Warm, reddish, acne-prone",
        "option_c": "Smooth, soft, oily",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q3_hair_type",
        "question": "Hair Type",
        "option_a": "Dry, frizzy, thin",
        "option_b": "Straight, fine, may grey early",
        "option_c": "Thick, lustrous, oily",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q4_appetite",
        "question": "Appetite & Digestion",
        "option_a": "Irregular appetite — sometimes hungry, sometimes not",
        "option_b": "Strong appetite, feel irritable if meals are missed",
        "option_c": "Steady appetite, slow digestion",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q5_sleep",
        "question": "Sleep Pattern",
        "option_a": "Light, interrupted sleep",
        "option_b": "Moderate sleep, wake up refreshed",
        "option_c": "Deep, long, heavy sleep",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q6_personality",
        "question": "Personality & Temperament",
        "option_a": "Creative, quick, easily anxious",
        "option_b": "Confident, focused, can get impatient",
        "option_c": "Calm, grounded, sometimes lazy",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q7_stress",
        "question": "Response to Stress",
        "option_a": "Worry or overthink",
        "option_b": "Get irritated or angry",
        "option_c": "Withdraw or eat/sleep more",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q8_climate",
        "question": "Climate Preference",
        "option_a": "Love warmth, dislike cold",
        "option_b": "Prefer cool weather, dislike heat",
        "option_c": "Enjoy warm, dry climates",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q9_energy",
        "question": "Energy Levels",
        "option_a": "Variable bursts of energy followed by fatigue",
        "option_b": "High, sustained energy",
        "option_c": "Slow but steady energy",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    },
    {
        "question_id": "q10_mind",
        "question": "Mind & Focus",
        "option_a": "Restless, multitasking",
        "option_b": "Sharp, determined",
        "option_c": "Peaceful, consistent",
        "dosha_a": "Vata",
        "dosha_b": "Pitta",
        "dosha_c": "Kapha"
    }
]


@router.get("/questions", response_model=List[DoshaQuizQuestions])
async def get_quiz_questions():
    """Get all dosha quiz questions."""
    return QUIZ_QUESTIONS


@router.get("/", response_model=List[DoshaQuizSchema])
async def read_dosha_quizzes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of all dosha quizzes."""
    quizzes = db.query(DoshaQuiz).offset(skip).limit(limit).all()
    logger.info(f"User {current_user.username} retrieved {len(quizzes)} dosha quizzes")
    return quizzes


@router.get("/{quiz_id}", response_model=DoshaQuizWithClient)
async def read_dosha_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dosha quiz by ID."""
    quiz = db.query(DoshaQuiz).filter(DoshaQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Dosha quiz not found")
    return quiz


@router.get("/{quiz_id}/result", response_model=DoshaQuizResult)
async def get_dosha_quiz_result(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed dosha quiz result with analysis."""
    quiz = db.query(DoshaQuiz).filter(DoshaQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Dosha quiz not found")
    
    result = DoshaQuizResult(
        id=quiz.id,
        client_id=quiz.client_id,
        dominant_dosha=quiz.dominant_dosha,
        vata_score=quiz.vata_score,
        pitta_score=quiz.pitta_score,
        kapha_score=quiz.kapha_score,
        dosha_percentage=quiz.get_dosha_percentage(),
        quiz_responses=quiz.get_quiz_responses(),
        notes=quiz.notes,
        created_at=quiz.created_at,
        updated_at=quiz.updated_at
    )
    return result


@router.get("/client/{client_id}", response_model=List[DoshaQuizWithClient])
async def read_dosha_quizzes_by_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all dosha quizzes for a specific client."""
    quizzes = db.query(DoshaQuiz).filter(DoshaQuiz.client_id == client_id).all()
    if not quizzes:
        raise HTTPException(status_code=404, detail="No dosha quizzes found for this client")
    return quizzes


@router.get("/client/{client_id}/latest", response_model=DoshaQuizWithClient)
async def read_latest_dosha_quiz_by_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the latest dosha quiz for a specific client."""
    quiz = db.query(DoshaQuiz).filter(
        DoshaQuiz.client_id == client_id
    ).order_by(DoshaQuiz.created_at.desc()).first()
    
    if quiz is None:
        raise HTTPException(status_code=404, detail="No dosha quiz found for this client")
    return quiz


@router.post("/", response_model=DoshaQuizSchema, status_code=status.HTTP_201_CREATED)
async def create_dosha_quiz(
    quiz_in: DoshaQuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit a new dosha quiz."""
    # Check if client exists
    client = db.query(Client).filter(Client.id == quiz_in.client_id).first()
    if not client:
        raise HTTPException(
            status_code=404,
            detail=f"Client with id {quiz_in.client_id} not found"
        )
    
    # Create new dosha quiz
    quiz = DoshaQuiz(**quiz_in.model_dump())
    
    # Calculate dosha scores and dominant dosha
    quiz.calculate_dosha()
    
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    logger.info(
        f"User {current_user.username} created dosha quiz for client_id: {quiz.client_id}, "
        f"Result: {quiz.dominant_dosha}"
    )
    return quiz


@router.put("/{quiz_id}", response_model=DoshaQuizSchema)
async def update_dosha_quiz(
    quiz_id: int,
    quiz_in: DoshaQuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update dosha quiz."""
    quiz = db.query(DoshaQuiz).filter(DoshaQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Dosha quiz not found")
    
    # Update fields
    update_data = quiz_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quiz, field, value)
    
    # Recalculate dosha if any answers changed
    answer_fields = [f'q{i}_' for i in range(1, 11)]
    if any(field.startswith(tuple(answer_fields)) for field in update_data.keys()):
        quiz.calculate_dosha()
    
    db.commit()
    db.refresh(quiz)
    
    logger.info(f"User {current_user.username} updated dosha quiz id: {quiz.id}")
    return quiz


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dosha_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete dosha quiz."""
    quiz = db.query(DoshaQuiz).filter(DoshaQuiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Dosha quiz not found")
    
    db.delete(quiz)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted dosha quiz id: {quiz.id}")
    return None


# Helper function for programmatic use
def submit_dosha_quiz(
    client_id: int,
    quiz_data: dict,
    db: Session
) -> DoshaQuiz:
    """
    Submit a dosha quiz for a client.
    This is a helper function for programmatic use.
    
    Args:
        client_id: The ID of the client
        quiz_data: Dictionary containing quiz responses
        db: Database session
    
    Returns:
        DoshaQuiz: The created quiz with calculated results
    """
    quiz_data['client_id'] = client_id
    quiz = DoshaQuiz(**quiz_data)
    quiz.calculate_dosha()
    
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    return quiz


def get_client_latest_dosha(client_id: int, db: Session) -> DoshaQuiz:
    """
    Get the latest dosha quiz for a client.
    Helper function for programmatic use.
    
    Args:
        client_id: The ID of the client
        db: Database session
    
    Returns:
        DoshaQuiz: The latest quiz or None if not found
    """
    return db.query(DoshaQuiz).filter(
        DoshaQuiz.client_id == client_id
    ).order_by(DoshaQuiz.created_at.desc()).first()

