# Client Context Issue - Fixed

## Problem

When users opened the AI chat interface for a specific client (with the client's name visible in the chat header), the agent would still ask for the client ID every time:

> "Please provide the client ID so I can retrieve their profile and create a personalized diet plan."

This was frustrating because:
- The chat was already open in the context of a specific client
- The client's name was visible in the UI header
- The session was already tied to that client in the database
- The agent should already know who it's talking about

## Root Cause

The AI agent had two issues:

1. **System Prompt Issue:** The agent's system prompt said:
   ```
   1. If no client_id provided, ask for it
   ```
   This instructed the agent to ask for client_id even though the session already had this information.

2. **No Context Injection:** When starting a chat session, the agent wasn't told which client the conversation was about. The `client_id` existed in the session object but wasn't communicated to the agent.

## Solution

Implemented a two-part fix:

### 1. Updated Agent System Prompt

**File:** `backend/app/utils/diet_plan_agent.py`

Changed from:
```python
When user asks to create a diet plan:
1. If no client_id provided, ask for it
2. Use get_client_profile to understand the client thoroughly
```

To:
```python
IMPORTANT: The conversation is ALWAYS in the context of a specific client.
The client_id will be provided at the start of the conversation.
NEVER ask for the client_id - it is already known!

When user asks to create a diet plan:
1. Use get_client_profile to understand the client thoroughly (client_id is already known)
2. Use calculate_nutrition to determine nutritional requirements
```

Also updated example interactions to remove "for client 42" from user messages, making it clear the client context is implicit.

### 2. Automatic Client Context Injection

**File:** `backend/app/routers/diet_plans.py`

Added automatic context injection at the start of each new chat session:

```python
# Get client info for context
client = db.query(Client).filter(Client.id == session.client_id).first()
client_name = f"{client.first_name} {client.last_name}" if client else "Unknown"

# Inject client context for new sessions
is_first_message = len(session.agent.memory.chat_memory.messages) == 0

if is_first_message:
    # Prepend client context to the first message
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
```

## How It Works Now

### User Experience Flow

**Before the fix:**
```
User opens chat for "Sarah Johnson"
User: "Generate a meal plan"
Agent: "I'd be happy to help! Please provide the client ID so I can access their profile."
User: "😤 It's Sarah! You can see her name in the header!"
```

**After the fix:**
```
User opens chat for "Sarah Johnson"
User: "Generate a meal plan"
Agent: "I'll create a personalized meal plan for Sarah Johnson. Let me retrieve her profile..."
[Agent automatically uses client_id from session context]
```

### Technical Flow

1. **Frontend opens chat for client ID 1**
   - Sends: `{client_id: 1, message: "Generate a meal plan"}`

2. **Backend creates/retrieves session**
   - Session is tied to `client_id: 1`
   - Checks if this is the first message

3. **First message - Context injection**
   - Retrieves client name: "Sarah Johnson"
   - Prepends system context with client_id and name
   - Agent receives: `[SYSTEM CONTEXT] ... CLIENT ID: 1, Name: Sarah Johnson ... {user message}`

4. **Agent processes message**
   - Sees client context in the message
   - Knows client_id = 1 without asking
   - Can immediately call `get_client_profile(client_id=1)`

5. **Subsequent messages**
   - No context injection needed (it's in conversation history)
   - Agent remembers it's talking about client 1

## Benefits

1. **Better UX:** Agent doesn't ask for information it should already know
2. **More Natural:** Conversations flow more naturally, like talking to a real assistant
3. **Less Confusion:** Users don't need to provide client ID manually
4. **Maintains Security:** Session is still tied to specific client and doctor
5. **Backward Compatible:** Works with existing session management

## Edge Cases Handled

1. **Missing client:** If client not found, shows "Unknown" but session still works
2. **Session restoration:** Context is preserved in conversation history
3. **Multiple tabs:** Each session has its own client context
4. **Session expiration:** New session gets fresh context injection

## Testing

### Manual Test

1. Open the web UI
2. Navigate to a client's profile
3. Click "AI Chat" or similar button
4. Send a message like "Generate a meal plan"
5. **Expected:** Agent immediately starts working without asking for client ID
6. **Verify:** Check that agent uses correct client_id in tool calls

### API Test

```bash
# Start new chat session for client 1
curl -X POST http://localhost:8000/diet-plans/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "message": "Create a diet plan"
  }'

# Expected response should show agent working with client 1
# Should NOT contain "please provide client_id" or similar
```

### Log Verification

Check `backend/logs/app.log` for:

```log
INFO - Chat request from admin: session=None, client=1, message=Create a diet plan
INFO - Created session XXX for client 1 by doctor 1
INFO - [Agent should call get_client_profile(client_id=1)]
```

Should NOT see agent responses asking for client_id.

## Files Changed

1. **`backend/app/utils/diet_plan_agent.py`**
   - Updated system prompt to indicate client context is always known
   - Updated example interactions
   - Removed instruction to ask for client_id

2. **`backend/app/routers/diet_plans.py`**
   - Added client context injection on first message
   - Injects CLIENT ID and client name
   - Provides explicit instructions to use the provided client_id

## Configuration

No configuration changes needed. The fix works automatically with existing sessions.

## Rollback

If issues occur, revert both files:

```bash
cd backend
git checkout HEAD -- app/utils/diet_plan_agent.py app/routers/diet_plans.py
```

Then restart the backend server.

## Future Enhancements

1. **Session Metadata:** Store client context in session metadata table
2. **Visual Indicator:** Show client context in agent's first response
3. **Multi-Client:** Support comparing/discussing multiple clients (with explicit switching)
4. **Context Summary:** Include recent health data in context injection

## Related Issues

- Fixes: Agent asking for client_id in client-specific chat
- Related: Session-based memory management
- See also: `SAVE_MEAL_PLAN_FIX.md` for meal plan saving improvements

## Support

If the agent still asks for client_id:

1. **Check logs:** Verify context injection is happening
2. **Clear sessions:** Delete old sessions that don't have context
3. **Restart backend:** Ensure new prompt is loaded
4. **Check frontend:** Verify client_id is being sent in request

For issues, check:
- `backend/logs/app.log` - Agent behavior and tool calls
- Network tab - Verify client_id in API requests
- Session database - Check AgentChatHistory table

