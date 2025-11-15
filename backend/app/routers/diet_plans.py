"""
Diet Plan management routes.
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diet_plan import DietPlan, DietPlanMeal
from app.models.health_profile import HealthProfile
from app.models.client import Client
from app.models.user import User
from app.schemas.diet_plan import (
    DietPlan as DietPlanSchema,
    DietPlanCreate,
    DietPlanUpdate,
    DietPlanWithMeals,
    DietPlanWithClient,
    DietPlanMeal as DietPlanMealSchema,
    DietPlanMealCreate,
    DietPlanMealUpdate,
    DietPlanGenerateRequest,
    DietPlanAIStep2Request,
    AgentChatRequest,
    AgentChatResponse,
    AgentSessionInfo
)
from app.utils.diet_plan_generator import DietPlanGenerator
from app.utils.diet_plan_agent import DietPlanAgent
from app.utils.smart_food_retriever import SmartFoodRetriever
from app.utils.logger import logger
from app.routers.auth import get_current_active_user
from app.config import settings

router = APIRouter(prefix="/diet-plans", tags=["Diet Plans"])


# ===========================
# Diet Plan CRUD Operations
# ===========================

@router.get("/", response_model=List[DietPlanSchema])
async def list_diet_plans(
    skip: int = 0,
    limit: int = 100,
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of all diet plans with optional filters."""
    query = db.query(DietPlan)
    
    if client_id:
        query = query.filter(DietPlan.client_id == client_id)
    if status:
        query = query.filter(DietPlan.status == status)
    
    plans = query.order_by(DietPlan.created_at.desc()).offset(skip).limit(limit).all()
    logger.info(f"User {current_user.username} retrieved {len(plans)} diet plans")
    return plans


@router.get("/{plan_id}", response_model=DietPlanWithMeals)
async def get_diet_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get diet plan by ID with all meals."""
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    logger.info(f"User {current_user.username} retrieved diet plan {plan_id}")
    return plan


@router.get("/client/{client_id}", response_model=List[DietPlanWithMeals])
async def get_client_diet_plans(
    client_id: int,
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all diet plans for a specific client."""
    # Verify client exists first
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    query = db.query(DietPlan).filter(DietPlan.client_id == client_id)
    
    if status:
        query = query.filter(DietPlan.status == status)
    
    plans = query.order_by(DietPlan.created_at.desc()).all()
    
    # Return empty list if no plans found (not an error!)
    logger.info(f"Retrieved {len(plans)} diet plans for client {client_id}")
    return plans


@router.post("/", response_model=DietPlanWithMeals, status_code=status.HTTP_201_CREATED)
async def create_diet_plan(
    plan_in: DietPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new diet plan manually."""
    # Verify client exists
    client = db.query(Client).filter(Client.id == plan_in.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Create diet plan
    plan_data = plan_in.model_dump(exclude={"meals"})
    plan_data["created_by_id"] = current_user.id
    
    plan = DietPlan(**plan_data)
    db.add(plan)
    db.flush()  # Get the plan ID
    
    # Create meals if provided
    if plan_in.meals:
        for meal_data in plan_in.meals:
            meal = DietPlanMeal(
                diet_plan_id=plan.id,
                **meal_data.model_dump()
            )
            db.add(meal)
    
    db.commit()
    db.refresh(plan)
    
    logger.info(f"User {current_user.username} created diet plan {plan.id} for client {plan.client_id}")
    return plan


@router.put("/{plan_id}", response_model=DietPlanSchema)
async def update_diet_plan(
    plan_id: int,
    plan_in: DietPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update diet plan metadata."""
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    # Update fields
    update_data = plan_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    
    db.commit()
    db.refresh(plan)
    
    logger.info(f"User {current_user.username} updated diet plan {plan_id}")
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diet_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a diet plan and all its meals."""
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    db.delete(plan)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted diet plan {plan_id}")
    return None


# ===========================
# AI Diet Plan Generation
# ===========================

@router.post("/generate", response_model=DietPlanWithMeals, status_code=status.HTTP_201_CREATED)
async def generate_diet_plan(
    request: DietPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate an AI-powered personalized diet plan based on health profile.
    
    This endpoint:
    1. Fetches the client's health profile
    2. Calculates nutritional requirements
    3. Selects appropriate foods from the database
    4. Creates a complete 7-day meal plan
    """
    # Verify client exists
    client = db.query(Client).filter(Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get health profile
    health_profile = db.query(HealthProfile).filter(
        HealthProfile.client_id == request.client_id
    ).first()
    
    if not health_profile:
        raise HTTPException(
            status_code=404,
            detail="Health profile not found. Please create a health profile first."
        )
    
    # Validate health profile has required data
    if not health_profile.weight or not health_profile.height:
        raise HTTPException(
            status_code=400,
            detail="Health profile must have weight and height to generate a diet plan. Please update the client's health profile."
        )
    
    if not health_profile.age and not health_profile.date_of_birth:
        raise HTTPException(
            status_code=400,
            detail="Health profile must have age or date of birth to generate a diet plan. Please update the client's health profile."
        )
    
    # Generate diet plan
    try:
        generator = DietPlanGenerator(db)
        logger.info(f"DietPlanGenerator initialized successfully")
        
        plan_data = generator.generate_plan(
            client_id=request.client_id,
            health_profile=health_profile,
            duration_days=request.duration_days,
            custom_goals=request.custom_goals,
            custom_diet_type=request.custom_diet_type,
            custom_allergies=request.custom_allergies,
            prefer_satvik=request.prefer_satvik,
            include_regional_foods=request.include_regional_foods,
            meal_variety=request.meal_variety
        )
        logger.info(f"Diet plan generated successfully with {len(plan_data.get('meals', []))} meals")
    except FileNotFoundError as e:
        logger.error(f"Food database not found: {e}")
        raise HTTPException(
            status_code=500,
            detail="Food database not loaded. Please run: python scripts/load_food_database.py"
        )
    except AttributeError as e:
        logger.error(f"Missing health profile data: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Health profile is missing required data: {str(e)}. Please ensure weight, height, and age are provided."
        )
    except Exception as e:
        logger.error(f"Error generating diet plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate diet plan: {str(e)}. Check backend logs for details."
        )
    
    # Create diet plan in database
    meals_data = plan_data.pop("meals")
    
    # Set start and end dates if not provided
    if request.start_date:
        plan_data["start_date"] = request.start_date
        plan_data["end_date"] = request.start_date + timedelta(days=request.duration_days)
    
    # Override name if provided
    if request.name:
        plan_data["name"] = request.name
    
    plan_data["created_by_id"] = current_user.id
    plan_data["status"] = "active"
    
    # Create plan
    plan = DietPlan(**plan_data)
    db.add(plan)
    db.flush()
    
    # Create meals
    for meal_data in meals_data:
        meal = DietPlanMeal(
            diet_plan_id=plan.id,
            **meal_data
        )
        db.add(meal)
    
    db.commit()
    db.refresh(plan)
    
    logger.info(
        f"User {current_user.username} generated diet plan {plan.id} "
        f"for client {request.client_id} with {len(meals_data)} meals"
    )
    
    return plan


# ===========================
# AI-Powered Diet Plan Generation (Two-Step Process)
# ===========================

@router.post("/generate-ai/step1", status_code=status.HTTP_200_OK)
async def generate_diet_plan_ai_step1(
    request: DietPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    STEP 1: AI Agent retrieves foods from knowledge base for user review.
    
    This endpoint uses an LLM-powered agent to:
    1. Calculate nutritional requirements based on client profile
    2. Search the food knowledge base for appropriate foods
    3. Present foods to the user for review before generating the plan
    
    The agent uses specialized tools:
    - calculate_nutrition: Computes daily calorie and macro requirements
    - retrieve_foods: Semantic search for foods matching criteria
    
    Returns foods for user to review. Call step2 after user confirmation.
    """
    logger.info(f"AI Diet Plan Step 1 initiated for client {request.client_id} by user {current_user.username}")
    
    # Verify client exists
    client = db.query(Client).filter(Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get health profile
    health_profile = db.query(HealthProfile).filter(
        HealthProfile.client_id == request.client_id
    ).first()
    
    if not health_profile:
        raise HTTPException(
            status_code=404,
            detail="Health profile not found. Please create a health profile first."
        )
    
    # Validate required health profile data
    if not health_profile.weight or not health_profile.height:
        raise HTTPException(
            status_code=400,
            detail="Health profile must have weight and height. Please update the client's health profile."
        )
    
    if not health_profile.age and not health_profile.date_of_birth:
        raise HTTPException(
            status_code=400,
            detail="Health profile must have age or date of birth. Please update the client's health profile."
        )
    
    # Check if OpenRouter API key is configured
    logger.info(f"OpenRouter API Key check: {settings.OPENROUTER_API_KEY[:20]}..." if settings.OPENROUTER_API_KEY else "None")
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "sk-or-v1-placeholder-get-from-openrouter-ai":
        raise HTTPException(
            status_code=500,
            detail=f"OpenRouter API key not configured. Current value starts with: {settings.OPENROUTER_API_KEY[:30] if settings.OPENROUTER_API_KEY else 'None'}. Please set OPENROUTER_API_KEY in .env file. Get your key from https://openrouter.ai/"
        )
    
    try:
        # UNIFIED APPROACH: Use session manager (same as chat flow)
        from app.utils.agent_session_manager import get_session_manager
        
        session_manager = get_session_manager()
        session_id = session_manager.create_session(
            db=db,
            client_id=request.client_id,
            doctor_id=current_user.id,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.DIET_PLAN_MODEL,
            temperature=settings.DIET_PLAN_TEMPERATURE
        )
        
        session = session_manager.get_session(
            session_id=session_id,
            client_id=request.client_id,
            doctor_id=current_user.id,
            db=db,
            api_key=settings.OPENROUTER_API_KEY
        )
        
        # Build structured message for food retrieval
        preferences_text = []
        if request.prefer_satvik:
            preferences_text.append("prefer Satvik foods")
        if request.include_regional_foods:
            preferences_text.append(f"include {request.include_regional_foods} regional foods")
        if request.meal_variety:
            preferences_text.append(f"{request.meal_variety} meal variety")
        
        custom_requirements = []
        if request.custom_goals:
            custom_requirements.append(f"Goals: {request.custom_goals}")
        if request.custom_diet_type:
            custom_requirements.append(f"Diet: {request.custom_diet_type}")
        if request.custom_allergies:
            custom_requirements.append(f"Avoid: {request.custom_allergies}")
        
        pref_string = ", ".join(preferences_text) if preferences_text else "standard preferences"
        custom_string = ". ".join(custom_requirements) if custom_requirements else ""
        
        message = f"""Retrieve foods for creating a diet plan for this client (ID: {request.client_id}).

Preferences: {pref_string}
{custom_string}

Please:
1. Get the client's health profile
2. Calculate nutritional requirements  
3. Retrieve appropriate foods for each meal type
4. Present them in an organized format for review

Present the foods grouped by meal type (Breakfast, Lunch, Dinner, Snacks, etc.)."""
        
        # Execute via chat
        result = session.agent.chat(message)
        
        # Update session stage
        session.update_stage("foods_retrieved")
        
        logger.info(f"AI Diet Plan Step 1 completed for client {request.client_id}, session: {session_id}")
        
        return {
            "status": "foods_retrieved",
            "step": 1,
            "session_id": session_id,  # IMPORTANT: Return this for Step 2
            "client_id": request.client_id,
            "response": result.get("response", ""),
            "intermediate_steps": result.get("intermediate_steps", []),
            "message": "Foods retrieved successfully! Review the suggestions and proceed to Step 2.",
            "next_action": "Call Step 2 with this session_id to generate the complete meal plan"
        }
        
    except Exception as e:
        logger.error(f"Error in AI diet plan step 1: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve foods: {str(e)}"
        )


@router.post("/generate-ai/step2", response_model=DietPlanWithMeals, status_code=status.HTTP_201_CREATED)
async def generate_diet_plan_ai_step2(
    request: DietPlanAIStep2Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    STEP 2: Generate final meal plan after user confirms foods.
    
    This endpoint:
    1. Takes user's feedback on the foods retrieved in Step 1
    2. Uses the AI agent to generate a complete 7-day meal plan
    3. Validates nutritional targets are met
    4. Parses the AI response into structured data
    5. Saves the diet plan and meals to the database
    6. Returns the complete saved plan
    """
    logger.info(f"AI Diet Plan Step 2 initiated for client {request.client_id} by user {current_user.username}")
    
    # Verify client exists
    client = db.query(Client).filter(Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get health profile for metadata
    health_profile = db.query(HealthProfile).filter(
        HealthProfile.client_id == request.client_id
    ).first()
    
    # Check API key
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "sk-or-v1-placeholder-get-from-openrouter-ai":
        raise HTTPException(
            status_code=500,
            detail="OpenRouter API key not configured. Please set OPENROUTER_API_KEY in .env file."
        )
    
    try:
        # UNIFIED APPROACH: Use session from Step 1 or create new one
        from app.utils.agent_session_manager import get_session_manager
        
        session_manager = get_session_manager()
        
        # Get session from Step 1
        if request.session_id:
            session = session_manager.get_session(
                session_id=request.session_id,
                client_id=request.client_id,
                doctor_id=current_user.id,
                db=db,
                api_key=settings.OPENROUTER_API_KEY,
                model=settings.DIET_PLAN_MODEL,
                temperature=settings.DIET_PLAN_TEMPERATURE
            )
            
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {request.session_id} not found or expired. Please restart from Step 1."
                )
        else:
            # Fallback: Create new session if no session_id provided (backward compatibility)
            logger.warning("No session_id provided in Step 2. Creating new session (conversation history will be lost).")
            session_id = session_manager.create_session(
                db=db,
                client_id=request.client_id,
                doctor_id=current_user.id,
                api_key=settings.OPENROUTER_API_KEY,
                model=settings.DIET_PLAN_MODEL,
                temperature=settings.DIET_PLAN_TEMPERATURE
            )
            
            session = session_manager.get_session(
                session_id=session_id,
                client_id=request.client_id,
                doctor_id=current_user.id,
                db=db,
                api_key=settings.OPENROUTER_API_KEY
            )
        
        # Build message for plan generation
        feedback_text = request.user_feedback or "User approved the food selections"
        modifications_text = ""
        if request.modifications:
            mods = [f"{k}: {v}" for k, v in request.modifications.items()]
            modifications_text = f"\n\nUser modifications: {', '.join(mods)}"
        
        plan_name = request.name or f"AI Diet Plan - {datetime.now().strftime('%Y-%m-%d')}"
        
        message = f"""Generate a complete {request.duration_days}-day meal plan.

User feedback: {feedback_text}{modifications_text}

Please:
1. Generate the complete meal plan in the specified format
2. Ensure all nutritional targets are met
3. Use validate_nutrition tool to verify the plan
4. IMPORTANT: After generating and validating the plan, automatically call save_diet_plan tool with:
   - client_id: {request.client_id}
   - plan_name: "{plan_name}"
   - plan_text: [the complete formatted meal plan you just generated]
   - duration_days: {request.duration_days}

This will save the plan to the database so it appears in the client's profile."""
        
        # Execute via chat
        result = session.agent.chat(message)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Failed to generate meal plan")
            )
        
        # Update session stage
        session.update_stage("plan_generated")
        
        # Check if the plan was saved by the agent
        ai_response = result.get("response", "")
        logger.info(f"AI Response for Step 2: {ai_response[:500]}")
        
        # Extract plan_id from intermediate steps if save_diet_plan was called
        plan_id = None
        intermediate_steps = result.get("intermediate_steps", [])
        
        for step in intermediate_steps:
            if step.get("tool") == "save_diet_plan":
                observation = step.get("observation", "")
                # Extract plan ID from the observation
                import re
                plan_id_match = re.search(r'Plan ID:\s*(\d+)', observation)
                if plan_id_match:
                    plan_id = int(plan_id_match.group(1))
                    logger.info(f"Plan saved by agent with ID: {plan_id}")
                    break
        
        # If agent didn't save the plan, parse and save manually (fallback)
        if not plan_id:
            logger.warning("Agent did not call save_diet_plan. Parsing and saving manually.")
            
            from app.utils.diet_plan_parser import DietPlanParser
            parser = DietPlanParser()
            
            parsed_data = parser.parse_diet_plan(ai_response)
            
            # Validate parsed data
            validation = parser.validate_meals(parsed_data["meals"])
            
            if not validation["valid"]:
                logger.error(f"Parsed meals validation failed: {validation['errors']}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse AI-generated plan. Errors: {'; '.join(validation['errors'])}"
                )
        
            if validation["warnings"]:
                logger.warning(f"Parsed meals have warnings: {validation['warnings']}")
            
            # Create diet plan in database manually
            meals_data = parsed_data["meals"]
            nutritional_summary = parsed_data.get("nutritional_summary", {})
            
            # Build plan metadata
            client_name = f"{client.first_name} {client.last_name}"
            plan_data = {
                "client_id": request.client_id,
                "name": request.name if hasattr(request, 'name') and request.name else f"{client_name} - AI Generated Plan",
                "description": f"AI-generated personalized diet plan. Total meals: {len(meals_data)}",
                "duration_days": request.duration_days,
                "created_by_id": current_user.id,
                "status": "active"
            }
            
            # Add health profile context if available
            if health_profile:
                plan_data["health_goals"] = health_profile.goals
                plan_data["diet_type"] = health_profile.diet_type
                plan_data["allergies"] = health_profile.allergies
            
            # Get dosha type from dosha quiz
            from app.models.dosha_quiz import DoshaQuiz
            dosha_quiz = db.query(DoshaQuiz).filter(
                DoshaQuiz.client_id == request.client_id
            ).order_by(DoshaQuiz.created_at.desc()).first()
            
            if dosha_quiz:
                # Determine primary dosha
                doshas = {
                    "Vata": dosha_quiz.vata_score or 0,
                    "Pitta": dosha_quiz.pitta_score or 0,
                    "Kapha": dosha_quiz.kapha_score or 0
                }
                primary_dosha = max(doshas, key=doshas.get)
                plan_data["dosha_type"] = primary_dosha
        
            # Add nutritional targets from summary or health profile
            if nutritional_summary:
                plan_data["target_calories"] = nutritional_summary.get("target_calories")
                plan_data["target_protein_g"] = nutritional_summary.get("target_protein_g")
                plan_data["target_carbs_g"] = nutritional_summary.get("target_carbs_g")
                plan_data["target_fat_g"] = nutritional_summary.get("target_fat_g")
            
            # Set dates if provided
            if request.start_date if hasattr(request, 'start_date') else None:
                plan_data["start_date"] = request.start_date
                plan_data["end_date"] = request.start_date + timedelta(days=request.duration_days)
            
            # Create plan
            plan = DietPlan(**plan_data)
            db.add(plan)
            db.flush()  # Get the plan ID
            plan_id = plan.id
            
            # Create meals
            for meal_data in meals_data:
                meal = DietPlanMeal(
                    diet_plan_id=plan.id,
                    day_number=meal_data.get("day_number", 1),
                    meal_time=meal_data.get("meal_time", "12:00 PM"),
                    meal_type=meal_data.get("meal_type", "Meal"),
                    food_dish=meal_data.get("food_dish", ""),
                    food_item_ids=meal_data.get("food_item_ids"),
                    healing_purpose=meal_data.get("healing_purpose"),
                    portion=meal_data.get("portion"),
                    dosha_notes=meal_data.get("dosha_notes"),
                    notes=meal_data.get("notes"),
                    calories=meal_data.get("calories"),
                    protein_g=meal_data.get("protein_g"),
                    carbs_g=meal_data.get("carbs_g"),
                    fat_g=meal_data.get("fat_g"),
                    order_in_day=meal_data.get("order_in_day", 0)
                )
                db.add(meal)
            
            db.commit()
            db.refresh(plan)
            
            logger.info(
                f"User {current_user.username} generated AI diet plan {plan.id} "
                f"for client {request.client_id} with {len(meals_data)} meals (manual save)"
            )
        else:
            # Plan was saved by agent - just retrieve it
            plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
            if not plan:
                raise HTTPException(
                    status_code=500,
                    detail=f"Plan was saved but could not be retrieved (ID: {plan_id})"
                )
            
            logger.info(
                f"User {current_user.username} generated AI diet plan {plan.id} "
                f"for client {request.client_id} (saved by agent)"
            )
        
        # Mark session as completed
        session.complete(diet_plan_id=plan_id)
        
        return plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in AI diet plan step 2: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate and save meal plan: {str(e)}"
        )


# ===========================
# Conversational Agent Chat Interface
# ===========================

@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    request: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Conversational interface for AI diet plan generation.
    
    This is the main entry point for natural language interaction with the AI agent.
    
    Flow:
    1. First message: "Generate diet plan for client 42"
       → Creates session, agent retrieves foods
    
    2. Follow-up: "Remove dairy products"
       → Agent modifies food selection
    
    3. Confirmation: "Perfect, create the 7-day plan"
       → Agent generates complete meal plan
    
    4. Refinement: "Make dinner lighter on day 3"
       → Agent adjusts specific meals
    
    Session Management:
    - New conversation: Don't provide session_id, DO provide client_id
    - Continue conversation: Provide session_id from previous response
    - Sessions are client-specific and doctor-specific (isolated data)
    - Sessions auto-expire after 30 minutes of inactivity
    - Chat history is persisted in database
    
    Security:
    - Sessions are tied to specific client + doctor
    - Cannot access another doctor's sessions
    - Cannot access sessions for different clients
    
    Args:
        request: Chat request with message, optional session_id, optional client_id
        db: Database session
        current_user: Authenticated user (doctor)
    
    Returns:
        AgentChatResponse with session_id, message, context, and tool results
    """
    from app.schemas.diet_plan import AgentChatRequest, AgentChatResponse
    from app.utils.agent_session_manager import get_session_manager
    
    logger.info(
        f"Chat request from {current_user.username}: "
        f"session={request.session_id}, client={request.client_id}, "
        f"message={request.message[:100]}"
    )
    
    # Check API key
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "sk-or-v1-placeholder-get-from-openrouter-ai":
        raise HTTPException(
            status_code=500,
            detail="OpenRouter API key not configured. Please set OPENROUTER_API_KEY in environment."
        )
    
    session_manager = get_session_manager()
    
    # Get or create session
    if request.session_id:
        # Continue existing session
        if not request.client_id:
            raise HTTPException(
                status_code=400,
                detail="client_id required when continuing a session"
            )
        
        session = session_manager.get_session(
            session_id=request.session_id,
            client_id=request.client_id,
            doctor_id=current_user.id,
            db=db,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.DIET_PLAN_MODEL,
            temperature=settings.DIET_PLAN_TEMPERATURE
        )
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {request.session_id} not found, expired, or access denied"
            )
        
        session_id = request.session_id
    else:
        # Create new session
        if not request.client_id:
            raise HTTPException(
                status_code=400,
                detail="client_id required for new chat session"
            )
        
        # Verify client exists and belongs to this doctor
        client = db.query(Client).filter(Client.id == request.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Create session
        session_id = session_manager.create_session(
            db=db,
            client_id=request.client_id,
            doctor_id=current_user.id,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.DIET_PLAN_MODEL,
            temperature=settings.DIET_PLAN_TEMPERATURE
        )
        
        session = session_manager.get_session(
            session_id=session_id,
            client_id=request.client_id,
            doctor_id=current_user.id,
            db=db,
            api_key=settings.OPENROUTER_API_KEY
        )
    
    try:
        # Get client info for context
        client = db.query(Client).filter(Client.id == session.client_id).first()
        client_name = f"{client.first_name} {client.last_name}" if client else "Unknown"
        
        # Inject client context for new sessions or first message
        # Check if this is the first message (no history yet)
        is_first_message = len(session.agent.memory.chat_memory.messages) == 0
        
        if is_first_message:
            # Prepend client context to the message
            context_message = f"""[SYSTEM CONTEXT]
This chat session is for CLIENT ID: {session.client_id}
Client Name: {client_name}

IMPORTANT: 
- All your actions should be for this client (ID: {session.client_id})
- When using tools that need client_id, use: {session.client_id}
- You do NOT need to ask the user for client_id
- The client context is already set

[END SYSTEM CONTEXT]

{request.message}"""
            result = session.agent.chat(context_message)
        else:
            # Continue conversation normally
            result = session.agent.chat(request.message)
        
        # Auto-detect stage changes (optional enhancement)
        response_text = result.get("response", "").lower()
        if "retrieved" in response_text and "foods" in response_text:
            session.update_stage("foods_retrieved")
        elif "day 1" in response_text or "day 7" in response_text:
            session.update_stage("plan_generated")
        
        return AgentChatResponse(
            session_id=session_id,
            client_id=session.client_id,
            message=result.get("response", ""),
            context=session.get_context(),
            intermediate_steps=result.get("intermediate_steps", [])
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.delete("/chat/{session_id}")
async def end_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    End a chat session and free up resources.
    
    Note: This only removes the session from memory cache.
    Chat history remains in database for audit/review purposes.
    
    Args:
        session_id: Session ID to end
        current_user: Authenticated user
    
    Returns:
        Success message
    """
    from app.utils.agent_session_manager import get_session_manager
    from app.models.agent_chat_history import AgentChatSession
    
    session_manager = get_session_manager()
    
    # Verify session belongs to current user
    session_record = db.query(AgentChatSession).filter(
        AgentChatSession.session_id == session_id
    ).first()
    
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_record.doctor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Session belongs to another user"
        )
    
    # Mark as completed in database
    session_record.status = "completed"
    session_record.completed_at = datetime.utcnow()
    db.commit()
    
    # Remove from cache
    session_manager.delete_session(session_id)
    
    logger.info(f"Ended session {session_id} for user {current_user.username}")
    
    return {
        "message": f"Session {session_id} ended successfully",
        "session_id": session_id
    }


@router.get("/chat/client/{client_id}/sessions", response_model=List[AgentSessionInfo])
async def get_client_chat_sessions(
    client_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get recent chat sessions for a specific client.
    
    Useful for:
    - Showing chat history on client detail page
    - Resuming previous conversations
    - Audit trail of AI interactions
    
    Args:
        client_id: Client ID
        limit: Maximum number of sessions to return (default: 10)
        current_user: Authenticated user
    
    Returns:
        List of session metadata
    """
    from app.utils.agent_session_manager import get_session_manager
    from app.schemas.diet_plan import AgentSessionInfo
    
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    session_manager = get_session_manager()
    sessions = session_manager.get_client_sessions(client_id, db, limit=limit)
    
    return [AgentSessionInfo(**session) for session in sessions]


@router.get("/chat/session/{session_id}/history")
async def get_session_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get complete chat history for a session.
    
    Returns all messages in chronological order.
    
    Args:
        session_id: Session ID
        current_user: Authenticated user
    
    Returns:
        List of chat messages with timestamps
    """
    from app.utils.agent_session_manager import get_session_manager
    from app.models.agent_chat_history import AgentChatSession
    
    # Verify session belongs to current user
    session_record = db.query(AgentChatSession).filter(
        AgentChatSession.session_id == session_id
    ).first()
    
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_record.doctor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Session belongs to another user"
        )
    
    session_manager = get_session_manager()
    history = session_manager.get_session_history(session_id, db)
    
    return {
        "session_id": session_id,
        "client_id": session_record.client_id,
        "status": session_record.status,
        "message_count": len(history),
        "messages": history
    }


# ===========================
# Smart Food Retrieval (Enhanced KB)
# ===========================

@router.post("/smart-food-retrieval", status_code=status.HTTP_200_OK)
async def smart_food_retrieval(
    request: DietPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Smart Food Retrieval - Get top 8 foods per category.
    
    This endpoint:
    1. Retrieves foods organized by category (Grains, Fruits, Vegetables, etc.)
    2. Filters out allergens automatically
    3. Excludes foods contraindicated for medical conditions
    4. Prioritizes foods that balance user's dosha
    5. Ranks by goal compatibility
    6. Returns top 8 foods per category
    
    No AI agent - direct, transparent, fast retrieval.
    Perfect for user review before meal plan generation.
    """
    logger.info(f"Smart food retrieval for client {request.client_id} by user {current_user.username}")
    
    # Verify client exists
    client = db.query(Client).filter(Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get health profile
    health_profile = db.query(HealthProfile).filter(
        HealthProfile.client_id == request.client_id
    ).first()
    
    if not health_profile:
        raise HTTPException(
            status_code=404,
            detail="Health profile not found. Please create a health profile first."
        )
    
    try:
        # Initialize smart retriever
        retriever = SmartFoodRetriever(db)
        
        # Get foods by category
        foods_by_category = retriever.get_foods_by_category_for_user(
            client_id=request.client_id,
            goals=request.custom_goals or health_profile.goals,
            dosha_type=None,  # Will auto-detect from quiz
            diet_type=request.custom_diet_type or health_profile.diet_type or "veg",
            allergies=request.custom_allergies or health_profile.allergies,
            medical_conditions=health_profile.disease,  # Correct field name
            top_k_per_category=8
        )
        
        # Get category summary
        category_summary = retriever.get_category_summary()
        
        total_foods = sum(len(foods) for foods in foods_by_category.values())
        
        return {
            "status": "success",
            "client_id": request.client_id,
            "foods_by_category": foods_by_category,
            "total_categories": len(foods_by_category),
            "total_foods": total_foods,
            "category_summary": category_summary,
            "filters_applied": {
                "allergies": request.custom_allergies or health_profile.allergies or "None",
                "diseases": health_profile.disease or "None",  # Correct field name
                "diet_type": request.custom_diet_type or health_profile.diet_type or "veg",
                "goals": request.custom_goals or health_profile.goals or "general wellness"
            },
            "message": f"Retrieved {total_foods} foods across {len(foods_by_category)} categories. Review and approve to proceed."
        }
        
    except Exception as e:
        logger.error(f"Error in smart food retrieval: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve foods: {str(e)}"
        )


# ===========================
# Meal Operations
# ===========================

@router.get("/{plan_id}/meals", response_model=List[DietPlanMealSchema])
async def get_plan_meals(
    plan_id: int,
    day_number: Optional[int] = Query(None, ge=1, le=7, description="Filter by day"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all meals for a diet plan, optionally filtered by day."""
    # Verify plan exists
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    query = db.query(DietPlanMeal).filter(DietPlanMeal.diet_plan_id == plan_id)
    
    if day_number:
        query = query.filter(DietPlanMeal.day_number == day_number)
    
    meals = query.order_by(
        DietPlanMeal.day_number,
        DietPlanMeal.order_in_day
    ).all()
    
    return meals


@router.post("/{plan_id}/meals", response_model=DietPlanMealSchema, status_code=status.HTTP_201_CREATED)
async def add_meal_to_plan(
    plan_id: int,
    meal_in: DietPlanMealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a new meal to an existing diet plan."""
    # Verify plan exists
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    meal = DietPlanMeal(
        diet_plan_id=plan_id,
        **meal_in.model_dump()
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    
    logger.info(f"User {current_user.username} added meal to diet plan {plan_id}")
    return meal


@router.put("/meals/{meal_id}", response_model=DietPlanMealSchema)
async def update_meal(
    meal_id: int,
    meal_in: DietPlanMealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a specific meal in a diet plan."""
    meal = db.query(DietPlanMeal).filter(DietPlanMeal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    # Update fields
    update_data = meal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meal, field, value)
    
    db.commit()
    db.refresh(meal)
    
    logger.info(f"User {current_user.username} updated meal {meal_id}")
    return meal


@router.delete("/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a specific meal from a diet plan."""
    meal = db.query(DietPlanMeal).filter(DietPlanMeal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    db.delete(meal)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted meal {meal_id}")
    return None


# ===========================
# Export and Formatting
# ===========================

@router.get("/{plan_id}/export", response_model=dict)
async def export_diet_plan(
    plan_id: int,
    format: str = Query("json", description="Export format: json, csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export diet plan in various formats suitable for sharing or printing.
    """
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    # Organize meals by day
    meals_by_day = {}
    for meal in plan.meals:
        day = meal.day_number
        if day not in meals_by_day:
            meals_by_day[day] = []
        meals_by_day[day].append(meal.to_dict())
    
    export_data = {
        "plan_id": plan.id,
        "client_id": plan.client_id,
        "plan_name": plan.name,
        "description": plan.description,
        "duration_days": plan.duration_days,
        "start_date": plan.start_date.isoformat() if plan.start_date else None,
        "end_date": plan.end_date.isoformat() if plan.end_date else None,
        "diet_type": plan.diet_type,
        "dosha_type": plan.dosha_type,
        "nutritional_targets": {
            "calories": plan.target_calories,
            "protein_g": plan.target_protein_g,
            "carbs_g": plan.target_carbs_g,
            "fat_g": plan.target_fat_g
        },
        "meals_by_day": meals_by_day
    }
    
    if format == "csv":
        # TODO: Implement CSV export
        raise HTTPException(status_code=501, detail="CSV export not yet implemented")
    
    logger.info(f"User {current_user.username} exported diet plan {plan_id}")
    return export_data


@router.get("/{plan_id}/summary", response_model=dict)
async def get_plan_summary(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get nutritional summary and statistics for a diet plan.
    """
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    # Calculate averages
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    meal_count = 0
    
    for meal in plan.meals:
        if meal.calories:
            total_calories += meal.calories
        if meal.protein_g:
            total_protein += meal.protein_g
        if meal.carbs_g:
            total_carbs += meal.carbs_g
        if meal.fat_g:
            total_fat += meal.fat_g
        meal_count += 1
    
    days = plan.duration_days or 7
    
    summary = {
        "plan_id": plan.id,
        "plan_name": plan.name,
        "duration_days": days,
        "total_meals": meal_count,
        "daily_averages": {
            "calories": round(total_calories / days, 1) if days > 0 else 0,
            "protein_g": round(total_protein / days, 1) if days > 0 else 0,
            "carbs_g": round(total_carbs / days, 1) if days > 0 else 0,
            "fat_g": round(total_fat / days, 1) if days > 0 else 0
        },
        "targets": {
            "calories": plan.target_calories,
            "protein_g": plan.target_protein_g,
            "carbs_g": plan.target_carbs_g,
            "fat_g": plan.target_fat_g
        }
    }
    
    logger.info(f"Retrieved summary for diet plan {plan_id}")
    return summary

