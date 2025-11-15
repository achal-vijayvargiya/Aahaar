"""
AI-Powered Diet Plan Agent using LangChain

This agent orchestrates the diet plan generation process:
1. Calculate nutritional requirements (using tools)
2. Retrieve appropriate foods from knowledge base
3. Present foods to user for review (Step 1)
4. Generate complete meal plan after user confirmation (Step 2)
5. Validate nutritional targets are met

The agent uses an LLM (via OpenRouter) to control the flow and make intelligent
decisions while delegating specific tasks to specialized tools.
"""
from typing import Dict, List, Optional, Any
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.orm import Session

from app.utils.diet_plan_tools import get_diet_plan_tools
from app.models.dosha_quiz import DoshaQuiz
from app.utils.logger import logger


class DietPlanAgent:
    """
    Intelligent agent for generating personalized Ayurvedic diet plans.
    
    Uses LangChain with OpenRouter LLM to orchestrate:
    - Nutritional calculation (deterministic tool)
    - Food retrieval (semantic search tool)
    - Plan generation (AI-powered creativity)
    - Validation (deterministic tool)
    
    Workflow:
    1. User calls generate_plan_step1() -> Agent retrieves foods
    2. User reviews foods and provides feedback
    3. User calls generate_plan_step2() -> Agent creates final plan
    """
    
    def __init__(
        self,
        db: Session,
        openrouter_api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.7,
        chat_history=None
    ):
        """
        Initialize the diet plan agent.
        
        Args:
            db: SQLAlchemy database session
            openrouter_api_key: API key for OpenRouter
            model: Model to use (e.g., "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-70b-instruct")
            temperature: Temperature for LLM (0.0-1.0, higher = more creative)
            chat_history: Optional custom chat history (for database persistence)
        """
        self.db = db
        self.model = model
        
        # Initialize LLM via OpenRouter
        # OpenRouter provides a unified API for multiple LLM providers
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=3000,
            default_headers={
                "HTTP-Referer": "https://drassistent.com",  # Required by OpenRouter
                "X-Title": "DrAssistent Diet Plan Generator"
            }
        )
        
        # Get specialized tools
        self.tools = get_diet_plan_tools(db)
        
        # We'll set the memory reference later for tools that need it
        self._save_tool = None
        
        # Create system prompt with Ayurvedic expertise
        self.system_prompt = self._create_system_prompt()
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent with tools
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create executor with memory for conversation
        # Use custom chat history if provided (for database persistence)
        if chat_history:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                chat_memory=chat_history,
                output_key="output"  # Explicitly set which key to use
            )
        else:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="output"  # Explicitly set which key to use
            )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=False,  # Disabled to prevent callback errors
            max_iterations=15,
            max_execution_time=120,  # 2 minutes timeout
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )
        
        # Set memory reference for SaveDietPlanTool so it can extract meal plans
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == 'save_diet_plan':
                tool.agent_memory = self.memory
                self._save_tool = tool
                logger.debug("Set memory reference for SaveDietPlanTool")
                break
        
        logger.info(f"DietPlanAgent initialized with model: {model}")
    
    def _create_system_prompt(self) -> str:
        """Create comprehensive system prompt for conversational agent"""
        return """You are Dr. Vaidya, an expert Ayurvedic nutritionist and diet planning specialist.

You are in CONVERSATIONAL MODE. Engage with users naturally through chat to create personalized diet plans.

Your expertise includes:
- Traditional Ayurvedic principles of diet and nutrition
- Modern nutritional science and macro/micronutrient requirements
- Dosha balancing through food selection
- Creating balanced, personalized meal plans
- Understanding gut health and digestion

Available Tools:
- get_client_profile: Get client's health profile, dosha type, and medical history
- calculate_nutrition: Calculate daily calorie and macro requirements
- retrieve_foods: Search for appropriate foods from knowledge base
- modify_food_selection: Add/remove/replace foods based on user feedback
- validate_nutrition: Verify meal plan meets nutritional targets
- save_diet_plan: Save the finalized plan to database (IMPORTANT: Always call this after plan is approved!)

CONVERSATIONAL WORKFLOW:

IMPORTANT: The conversation is ALWAYS in the context of a specific client.
The client_id will be provided at the start of the conversation.
NEVER ask for the client_id - it is already known!

When user asks to create a diet plan:
1. Use get_client_profile to understand the client thoroughly (client_id is already known)
2. Use calculate_nutrition to determine nutritional requirements
3. Use retrieve_foods to get food options for each meal type:
   - Breakfast (25% of daily calories)
   - Mid Snack (10% of daily calories)
   - Lunch (35% of daily calories)
   - Evening Snack (10% of daily calories)
   - Dinner (15% of daily calories)
   - Morning Cleanse & Sleep Tonic (5% of daily calories)
   
   IMPORTANT: When calling retrieve_foods, you MUST provide these exact parameters:
   - query: String like "high protein breakfast foods for weight loss"
   - meal_type: String like "Breakfast" or "Lunch" (exact name)
   - target_calories: Number like 450.0 (calculate from daily calories percentage)
   - dosha_type: String like "Kapha" (optional)
   
   Example correct call (note the parameter names):
   {{
       "query": "high protein energizing breakfast foods for Kapha weight loss",
       "meal_type": "Breakfast",
       "target_calories": 450.0,
       "dosha_type": "Kapha",
       "diet_type": "veg"
   }}
   
   DO NOT pass other parameters like 'goal', 'calorie_percentage', etc.

4. Present foods in an organized format and ASK for user feedback
5. If user wants changes, use modify_food_selection
6. When user confirms, generate the complete 7-day meal plan
7. Present plan and ask if any adjustments needed
8. Make iterative refinements as requested

Example Interactions:

User: "Create a diet plan" or "Generate meal plan"
You: [Use get_client_profile with known client_id] "I've analyzed Sarah's profile. She's 28, wants weight loss, Kapha dosha.
     Target: 1800 kcal/day. Here are recommended foods by meal type:
     [List foods organized by meal]
     
     Would you like to proceed with these or make changes?"

User: "Remove dairy products"
You: [Use modify_food_selection] "Removed all dairy. Added plant-based alternatives:
     [Show updated list]
     Ready to generate the plan?"

User: "Yes, create the 7-day plan"
You: [Generate detailed plan] "Here's your personalized 7-day Ayurvedic plan:
     [Show structured plan]
     
     Would you like any adjustments, or should I save this to the database?"

User: "Looks perfect, save it!"
You: [Use save_diet_plan tool - IMPORTANT: Include the complete meal plan text in the plan_text parameter]
     "✅ Diet plan saved successfully! 
     Plan ID: 42
     The plan is now visible in the client's profile."

User: "Make dinner lighter on day 3"
You: [Adjust] "Day 3 dinner now 200 kcal instead of 270. Updated meal..."

IMPORTANT FOR SAVING:
When user asks to save the plan, you MUST call save_diet_plan with:
- client_id: The client's ID
- plan_name: A descriptive name (e.g., "7-Day Weight Loss Plan")
- plan_text: THE COMPLETE FORMATTED MEAL PLAN TEXT you generated
- duration_days: Number of days (usually 7)

The plan_text should contain the entire meal plan in the structured format with all days.

Meal Plan Format (CRITICAL for Step 2):

Day 1:
- Morning Cleanse (6:30 AM): [Dish Name]
  Portion: [size]
  Healing Purpose: [benefit]
  Dosha Notes: [impact]
  Calories: X, Protein: Xg, Carbs: Xg, Fat: Xg

- Breakfast (8:30 AM): [Dish Name]
  Portion: [size]
  Healing Purpose: [benefit]
  Dosha Notes: [impact]
  Calories: X, Protein: Xg, Carbs: Xg, Fat: Xg

[Continue for all meals...]

Important Guidelines:
- Be conversational and warm, not robotic
- Ask questions to clarify needs
- Explain Ayurvedic reasoning behind choices
- Consider meal timing (digestive fire peaks at noon)
- Prefer Satvik foods when possible
- Always confirm before major steps
- Be helpful with modifications

CRITICAL - Tool Usage Rules:
- When calling retrieve_foods, ALWAYS provide: query, meal_type, target_calories
- The query should be a natural language string (e.g., "high protein breakfast")
- The target_calories should be a NUMBER (e.g., 450.0), not a percentage
- If you get a validation error, check you're passing the exact parameters shown in the example

Communication Style:
- Natural and conversational
- Educational but not preachy
- Ask clarifying questions
- Explain your decisions
- Be supportive and encouraging

Remember: You're having a conversation, not just executing commands. Engage naturally!"""
    
    def generate_plan_step1_retrieve_foods(
        self,
        client_id: int,
        health_profile: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        STEP 1: Calculate nutrition and retrieve foods for user review.
        
        This step:
        1. Calculates nutritional requirements based on client's profile
        2. Retrieves appropriate foods for each meal type
        3. Presents foods to user for review
        4. Waits for user confirmation before proceeding
        
        Args:
            client_id: Database ID of the client
            health_profile: Dict with weight, height, age, activity_level, goals, etc.
            preferences: Optional dict with prefer_satvik, regional_foods, variety level
        
        Returns:
            Dict with status, agent response, and intermediate steps
        """
        logger.info(f"Step 1: Starting food retrieval for client {client_id}")
        
        # Get primary dosha
        dosha_type = self._get_primary_dosha(client_id)
        
        # Build detailed request for agent
        pref = preferences or {}
        request = f"""
CREATE A PERSONALIZED DIET PLAN - STEP 1: RETRIEVE FOODS

Client Profile:
- Client ID: {client_id}
- Weight: {health_profile.get('weight')}kg
- Height: {health_profile.get('height')}cm
- Age: {health_profile.get('age')} years
- Activity Level: {health_profile.get('activity_level', 'moderately_active')}
- Health Goals: {health_profile.get('goals', 'general wellness')}
- Primary Dosha: {dosha_type or 'Unknown (will balance all three)'}
- Diet Type: {health_profile.get('diet_type', 'vegetarian')}
- Allergies/Restrictions: {health_profile.get('allergies', 'None')}

Preferences:
- Prefer Satvik Foods: {pref.get('prefer_satvik', False)}
- Regional Preference: {pref.get('regional_foods', 'Pan-Indian')}
- Meal Variety Level: {pref.get('variety', 'moderate')}

TASK: 
Execute STEP 1 of the workflow:
1. Calculate nutritional requirements using the calculate_nutrition tool
2. Determine appropriate calorie distribution across meals
3. Retrieve suitable foods for each meal type using retrieve_foods tool
4. Present foods in an organized format for user review

Make sure to:
- Consider dosha balancing when retrieving foods
- Distribute calories appropriately (breakfast 25%, lunch 35%, dinner 15%, snacks 10% each, cleanse/tonic 5% total)
- Retrieve diverse foods appropriate for each meal time
- Explain Ayurvedic principles behind recommendations

After presenting foods, ask the user to review and confirm before proceeding to Step 2.
"""
        
        try:
            # Execute agent
            result = self.agent_executor.invoke({"input": request})
            
            response_data = {
                "status": "foods_retrieved",
                "step": 1,
                "client_id": client_id,
                "dosha_type": dosha_type,
                "response": result["output"],
                "intermediate_steps": self._format_intermediate_steps(result.get("intermediate_steps", [])),
                "message": "Foods retrieved successfully! Please review the suggestions above and reply with 'confirm' to proceed to meal plan generation, or provide feedback for adjustments.",
                "next_action": "Call generate_plan_step2() with user feedback to create the complete meal plan"
            }
            
            logger.info(f"Step 1 completed for client {client_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error in step 1 for client {client_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "step": 1,
                "error": str(e),
                "message": f"Failed to retrieve foods: {str(e)}"
            }
    
    def generate_plan_step2_create_plan(
        self,
        client_id: int,
        user_feedback: str = "confirm",
        modifications: Optional[Dict[str, Any]] = None,
        duration_days: int = 7
    ) -> Dict[str, Any]:
        """
        STEP 2: Generate complete meal plan after user confirms foods.
        
        This step:
        1. Takes user's feedback on retrieved foods
        2. Generates a complete 7-day meal plan
        3. Validates nutritional targets are met
        4. Returns structured meal plan ready for database storage
        
        Args:
            client_id: Database ID of the client
            user_feedback: User's response to food suggestions (default: "confirm")
            modifications: Optional dict with specific user requests
            duration_days: Number of days for the plan (default: 7)
        
        Returns:
            Dict with status, meal plan data, and validation results
        """
        logger.info(f"Step 2: Generating meal plan for client {client_id}")
        
        # Build request for plan generation
        mod_text = ""
        if modifications:
            mod_text = f"\n\nUser Modifications:\n" + "\n".join(
                f"- {k}: {v}" for k, v in modifications.items()
            )
        
        request = f"""
CREATE A PERSONALIZED DIET PLAN - STEP 2: GENERATE COMPLETE PLAN

User Feedback on Foods: "{user_feedback}"{mod_text}

TASK:
Execute STEP 2 of the workflow:
1. Using the foods retrieved in Step 1 (and any user modifications)
2. Generate a complete {duration_days}-day meal plan

IMPORTANT: Use this EXACT format for each meal to ensure proper parsing:

Day 1:
- Morning Cleanse (6:30 AM): [Dish Name]
  Portion: [e.g., 1 glass, 200ml, 2 cups]
  Healing Purpose: [Ayurvedic benefit]
  Dosha Notes: [How it affects doshas]
  Calories: [number], Protein: [number]g, Carbs: [number]g, Fat: [number]g

- Breakfast (8:30 AM): [Dish Name]
  Portion: [e.g., 1 bowl, 2 chapatis]
  Healing Purpose: [Ayurvedic benefit]
  Dosha Notes: [How it affects doshas]
  Calories: [number], Protein: [number]g, Carbs: [number]g, Fat: [number]g

- Mid Snack (11:00 AM): [Dish Name]
  Portion: [portion size]
  Healing Purpose: [benefit]
  Dosha Notes: [dosha impact]
  Calories: [number], Protein: [number]g, Carbs: [number]g, Fat: [number]g

- Lunch (1:30 PM): [Dish Name]
  Portion: [portion size]
  Healing Purpose: [benefit]
  Dosha Notes: [dosha impact]
  Calories: [number], Protein: [number]g, Carbs: [number]g, Fat: [number]g

- Evening Snack (4:30 PM): [Dish Name]
  Portion: [portion size]
  Healing Purpose: [benefit]
  Dosha Notes: [dosha impact]
  Calories: [number], Protein: [number]g, Carbs: [number]g, Fat: [number]g

- Dinner (7:00 PM): [Dish Name]
  Portion: [portion size]
  Healing Purpose: [benefit]
  Dosha Notes: [dosha impact]
  Calories: [number], Protein: [number]g, Carbs: [number]g, Fat: [number]g

- Sleep Tonic (9:00 PM): [Dish Name]
  Portion: [portion size]
  Healing Purpose: [benefit]
  Dosha Notes: [dosha impact]
  Calories: [number], Protein: [number]g, Carbs: [number]g, Fat: [number]g

Repeat this EXACT format for Day 2, Day 3, etc. through Day {duration_days}.

CRITICAL FORMATTING RULES:
1. Always start with "Day X:" on its own line
2. Each meal must start with "- [Meal Type] (Time): [Dish Name]"
3. Indented details must be on separate lines: Portion, Healing Purpose, Dosha Notes, nutritional values
4. Nutritional line MUST be in format: "Calories: X, Protein: Xg, Carbs: Xg, Fat: Xg"
5. Use blank line between meals
6. Do NOT add extra commentary between meals - stick to the format

Meal Distribution Guidelines:
- Morning Cleanse: 10-20 calories (light detox drink)
- Breakfast: 25% of daily calories (hearty, grounding meal)
- Mid Snack: 10% of daily calories (light, easy to digest)
- Lunch: 35% of daily calories (largest meal, peak digestive fire)
- Evening Snack: 10% of daily calories (light refreshment)
- Dinner: 15% of daily calories (light, warm, easy to digest)
- Sleep Tonic: 10-20 calories (calming drink)

Ensure:
- Variety across days (don't repeat exact same meals)
- Foods are from those retrieved in Step 1
- Portions are realistic and specific
- All nutritional values are provided

After generating ALL days:
- Use validate_nutrition tool to verify targets are met
- Provide a final summary with total daily averages
- Ask user if they want to save the plan
- When user confirms, use save_diet_plan tool to save it to database

CRITICAL: Always call save_diet_plan when user approves the final plan!
"""
        
        try:
            # Execute agent
            result = self.agent_executor.invoke({"input": request})
            
            response_data = {
                "status": "plan_generated",
                "step": 2,
                "client_id": client_id,
                "duration_days": duration_days,
                "response": result["output"],
                "intermediate_steps": self._format_intermediate_steps(result.get("intermediate_steps", [])),
                "message": "Diet plan generated successfully!",
                "note": "Parse the meal plan from the response and save to database."
            }
            
            logger.info(f"Step 2 completed for client {client_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error in step 2 for client {client_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "step": 2,
                "error": str(e),
                "message": f"Failed to generate meal plan: {str(e)}"
            }
    
    def chat(self, message: str) -> Dict[str, Any]:
        """
        General chat interface for follow-up questions or refinements.
        
        Use this for iterative improvements after the plan is generated.
        
        Args:
            message: User's message or question
        
        Returns:
            Dict with response and conversation history
        """
        try:
            result = self.agent_executor.invoke({"input": message})
            
            return {
                "status": "success",
                "response": result["output"],
                "intermediate_steps": self._format_intermediate_steps(result.get("intermediate_steps", []))
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": f"Chat error: {str(e)}"
            }
    
    def reset_conversation(self):
        """Reset conversation memory for a new client/session"""
        self.memory.clear()
        logger.info("Agent conversation memory cleared")
    
    def _get_primary_dosha(self, client_id: int) -> Optional[str]:
        """
        Get the primary dosha for a client from their quiz results.
        
        Args:
            client_id: Database ID of the client
        
        Returns:
            Primary dosha name (Vata, Pitta, or Kapha) or None
        """
        try:
            quiz_result = self.db.query(DoshaQuiz).filter(
                DoshaQuiz.client_id == client_id
            ).order_by(DoshaQuiz.created_at.desc()).first()
            
            if not quiz_result:
                logger.warning(f"No dosha quiz result found for client {client_id}")
                return None
            
            # Find dosha with highest score
            doshas = {
                "Vata": quiz_result.vata_score or 0,
                "Pitta": quiz_result.pitta_score or 0,
                "Kapha": quiz_result.kapha_score or 0
            }
            
            primary = max(doshas, key=doshas.get)
            logger.info(f"Primary dosha for client {client_id}: {primary}")
            return primary
            
        except Exception as e:
            logger.error(f"Error getting dosha for client {client_id}: {e}")
            return None
    
    def _format_intermediate_steps(self, steps: List) -> List[Dict]:
        """
        Format intermediate steps for easier reading.
        
        Args:
            steps: Raw intermediate steps from agent execution
        
        Returns:
            List of formatted step dictionaries
        """
        formatted = []
        for i, (action, observation) in enumerate(steps, 1):
            formatted.append({
                "step_number": i,
                "tool": action.tool if hasattr(action, 'tool') else "unknown",
                "tool_input": action.tool_input if hasattr(action, 'tool_input') else {},
                "observation": str(observation)[:500] + "..." if len(str(observation)) > 500 else str(observation)
            })
        return formatted
    
    def get_conversation_history(self) -> List[Dict]:
        """
        Get the current conversation history.
        
        Returns:
            List of message dictionaries with role and content
        """
        messages = self.memory.chat_memory.messages
        return [
            {
                "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                "content": msg.content
            }
            for msg in messages
        ]


