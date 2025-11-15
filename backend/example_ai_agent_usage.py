"""
Example script demonstrating AI Agent Diet Plan generation.

This shows how to use the new AI-powered endpoints to generate
personalized diet plans with user review.

Requirements:
- Backend server running (uvicorn app.main:app --reload)
- Valid authentication token
- OpenRouter API key configured in .env
- Client with health profile in database
"""
import requests
import json
from typing import Dict, Any


class DietPlanAIClient:
    """Client for interacting with AI Diet Plan endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def step1_retrieve_foods(
        self,
        client_id: int,
        duration_days: int = 7,
        custom_goals: str = None,
        prefer_satvik: bool = False,
        meal_variety: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Step 1: Retrieve appropriate foods for review.
        
        Args:
            client_id: ID of the client
            duration_days: Number of days for the plan
            custom_goals: Custom health goals (overrides profile)
            prefer_satvik: Prefer Satvik foods
            meal_variety: low, moderate, or high
        
        Returns:
            Response dict with foods and intermediate steps
        """
        url = f"{self.base_url}/api/v1/diet-plans/generate-ai/step1"
        
        payload = {
            "client_id": client_id,
            "duration_days": duration_days,
            "prefer_satvik": prefer_satvik,
            "meal_variety": meal_variety
        }
        
        if custom_goals:
            payload["custom_goals"] = custom_goals
        
        print(f"🔍 Step 1: Retrieving foods for client {client_id}...")
        print(f"📋 Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Foods retrieved successfully!\n")
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            return None
    
    def step2_generate_plan(
        self,
        client_id: int,
        user_feedback: str = "confirm",
        modifications: Dict[str, str] = None,
        duration_days: int = 7
    ) -> Dict[str, Any]:
        """
        Step 2: Generate complete meal plan.
        
        Args:
            client_id: ID of the client
            user_feedback: User's feedback on retrieved foods
            modifications: Dict of specific modifications
            duration_days: Number of days for the plan
        
        Returns:
            Response dict with complete meal plan
        """
        url = f"{self.base_url}/api/v1/diet-plans/generate-ai/step2"
        
        payload = {
            "client_id": client_id,
            "user_feedback": user_feedback,
            "duration_days": duration_days
        }
        
        if modifications:
            payload["modifications"] = modifications
        
        print(f"📝 Step 2: Generating meal plan for client {client_id}...")
        print(f"📋 Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Meal plan generated successfully!\n")
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            return None
    
    def chat(self, message: str) -> Dict[str, Any]:
        """
        Chat with the AI agent for follow-up questions.
        
        Args:
            message: Your message or question
        
        Returns:
            Response dict with agent's reply
        """
        url = f"{self.base_url}/api/v1/diet-plans/generate-ai/chat"
        
        payload = {"message": message}
        
        print(f"💬 Chatting with agent...")
        print(f"You: {message}")
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Agent: {data['response'][:200]}...\n")
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            return None


def print_foods_summary(data: Dict[str, Any]):
    """Print a summary of retrieved foods"""
    print("=" * 80)
    print("RETRIEVED FOODS SUMMARY")
    print("=" * 80)
    print(f"Status: {data.get('status')}")
    print(f"Client ID: {data.get('client_id')}")
    print(f"Dosha Type: {data.get('dosha_type')}")
    print(f"\nTools Used:")
    for step in data.get('intermediate_steps', []):
        print(f"  {step['step_number']}. {step['tool']}")
    print(f"\nAgent Response (first 500 chars):")
    print(data.get('response', '')[:500])
    print("...\n")
    print("=" * 80)


def print_plan_summary(data: Dict[str, Any]):
    """Print a summary of generated meal plan"""
    print("=" * 80)
    print("GENERATED MEAL PLAN SUMMARY")
    print("=" * 80)
    print(f"Status: {data.get('status')}")
    print(f"Duration: {data.get('duration_days')} days")
    print(f"\nTools Used:")
    for step in data.get('intermediate_steps', []):
        print(f"  {step['step_number']}. {step['tool']}")
    print(f"\nAgent Response (first 1000 chars):")
    print(data.get('response', '')[:1000])
    print("...\n")
    print("=" * 80)


# ============================================
# Example Usage Scenarios
# ============================================

def example_basic_flow():
    """
    Example 1: Basic two-step diet plan generation
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Two-Step Flow")
    print("=" * 80 + "\n")
    
    # Initialize client (replace with your actual token)
    client = DietPlanAIClient(token="your_jwt_token_here")
    
    # Step 1: Retrieve foods
    foods_response = client.step1_retrieve_foods(
        client_id=1,
        duration_days=7,
        custom_goals="weight loss and better digestion"
    )
    
    if foods_response:
        print_foods_summary(foods_response)
        
        # In a real app, user would review foods here
        input("\nPress Enter to confirm foods and proceed to Step 2...")
        
        # Step 2: Generate plan
        plan_response = client.step2_generate_plan(
            client_id=1,
            user_feedback="confirm",
            duration_days=7
        )
        
        if plan_response:
            print_plan_summary(plan_response)


def example_with_modifications():
    """
    Example 2: Diet plan with user modifications
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: With User Modifications")
    print("=" * 80 + "\n")
    
    client = DietPlanAIClient(token="your_jwt_token_here")
    
    # Step 1: Retrieve foods
    foods_response = client.step1_retrieve_foods(
        client_id=1,
        custom_goals="muscle gain",
        prefer_satvik=True,
        meal_variety="high"
    )
    
    if foods_response:
        print_foods_summary(foods_response)
        
        # User reviews and wants to make changes
        print("\n📝 User wants to make modifications...")
        
        # Step 2: Generate plan with modifications
        plan_response = client.step2_generate_plan(
            client_id=1,
            user_feedback="I like the suggestions but need some changes",
            modifications={
                "replace_paneer": "tofu (vegan alternative)",
                "no_onion_garlic": "I follow a Jain diet",
                "add_more_protein": "I do intense workouts"
            },
            duration_days=7
        )
        
        if plan_response:
            print_plan_summary(plan_response)


def example_with_chat():
    """
    Example 3: Using chat for follow-up questions
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Follow-up Chat")
    print("=" * 80 + "\n")
    
    client = DietPlanAIClient(token="your_jwt_token_here")
    
    # Generate basic plan first
    foods_response = client.step1_retrieve_foods(client_id=1)
    
    if foods_response:
        plan_response = client.step2_generate_plan(client_id=1)
        
        if plan_response:
            # Now ask follow-up questions
            print("\n💬 Asking follow-up questions...\n")
            
            client.chat("Can you explain why you chose moong dal for breakfast?")
            client.chat("What are some alternatives for quinoa in the lunch meal?")
            client.chat("How can I meal prep for this plan on Sunday?")


def example_different_goals():
    """
    Example 4: Different health goals
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Different Health Goals")
    print("=" * 80 + "\n")
    
    client = DietPlanAIClient(token="your_jwt_token_here")
    
    goals_to_test = [
        "weight loss and fat burning",
        "muscle gain and strength building",
        "better digestion and gut health",
        "more energy throughout the day",
        "managing diabetes naturally"
    ]
    
    for goal in goals_to_test:
        print(f"\n🎯 Testing goal: {goal}")
        print("-" * 80)
        
        foods_response = client.step1_retrieve_foods(
            client_id=1,
            custom_goals=goal
        )
        
        if foods_response:
            # Show just the summary
            print(f"✅ Retrieved foods for: {goal}")
            print(f"   Tools used: {len(foods_response.get('intermediate_steps', []))}")


def example_error_handling():
    """
    Example 5: Error handling scenarios
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Error Handling")
    print("=" * 80 + "\n")
    
    client = DietPlanAIClient(token="invalid_token")
    
    # This will fail due to invalid token
    print("Testing with invalid token...")
    client.step1_retrieve_foods(client_id=1)
    
    # This will fail due to non-existent client
    client = DietPlanAIClient(token="your_jwt_token_here")
    print("\nTesting with non-existent client...")
    client.step1_retrieve_foods(client_id=99999)


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  AI-Powered Diet Plan Generator - Example Usage              ║
    ║                                                              ║
    ║  Before running, make sure:                                  ║
    ║  1. Backend server is running                                ║
    ║  2. You have a valid JWT token                               ║
    ║  3. OpenRouter API key is configured                         ║
    ║  4. Client with health profile exists in database            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("\nAvailable Examples:")
    print("1. Basic two-step flow")
    print("2. With user modifications")
    print("3. Follow-up chat")
    print("4. Different health goals")
    print("5. Error handling")
    
    choice = input("\nEnter example number (1-5) or 'all': ")
    
    if choice == "1":
        example_basic_flow()
    elif choice == "2":
        example_with_modifications()
    elif choice == "3":
        example_with_chat()
    elif choice == "4":
        example_different_goals()
    elif choice == "5":
        example_error_handling()
    elif choice.lower() == "all":
        example_basic_flow()
        example_with_modifications()
        example_with_chat()
        example_different_goals()
        example_error_handling()
    else:
        print("Invalid choice. Please run again and select 1-5 or 'all'")
    
    print("\n✨ Done! Check the output above for results.")
    print("📚 For more info, see: backend/AI_AGENT_DIET_PLAN_GUIDE.md")


