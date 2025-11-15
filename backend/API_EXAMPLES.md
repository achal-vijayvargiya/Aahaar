# API Usage Examples

This document provides practical examples of using the DrAssistent API.

## Table of Contents
- [Authentication](#authentication)
- [User Management](#user-management)
- [Client Management](#client-management)
- [Appointment Management](#appointment-management)

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

### Login

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Python:**
```python
import requests

url = "http://localhost:8000/api/v1/auth/login"
data = {
    "username": "admin",
    "password": "admin123"
}
response = requests.post(url, data=data)
token = response.json()["access_token"]
print(f"Token: {token}")
```

### Get Current User

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Python:**
```python
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/v1/auth/me", headers=headers)
print(response.json())
```

## User Management

### Create User

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nurse@drassistent.com",
    "username": "nurse1",
    "password": "nurse123",
    "full_name": "Jane Smith",
    "role": "nurse",
    "is_active": true
  }'
```

**Python:**
```python
url = "http://localhost:8000/api/v1/users/"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
data = {
    "email": "nurse@drassistent.com",
    "username": "nurse1",
    "password": "nurse123",
    "full_name": "Jane Smith",
    "role": "nurse",
    "is_active": True
}
response = requests.post(url, headers=headers, json=data)
print(response.json())
```

### List Users

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python:**
```python
response = requests.get(
    "http://localhost:8000/api/v1/users/",
    headers=headers
)
users = response.json()
for user in users:
    print(f"User: {user['username']} - {user['email']}")
```

### Update User

**Request:**
```bash
curl -X PUT "http://localhost:8000/api/v1/users/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Updated Name",
    "is_active": true
  }'
```

### Delete User

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/users/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Client Management

### Create Client

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/clients/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "date_of_birth": "1990-01-15",
    "gender": "male",
    "address": "123 Main St, City, Country",
    "medical_history": "No known allergies",
    "notes": "Regular checkup patient"
  }'
```

**Python:**
```python
url = "http://localhost:8000/api/v1/clients/"
data = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "date_of_birth": "1990-01-15",
    "gender": "male",
    "address": "123 Main St, City, Country",
    "medical_history": "No known allergies",
    "notes": "Regular checkup patient"
}
response = requests.post(url, headers=headers, json=data)
client = response.json()
print(f"Created client: {client['id']}")
```

### List Clients

**Request:**
```bash
# List all clients
curl -X GET "http://localhost:8000/api/v1/clients/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search clients
curl -X GET "http://localhost:8000/api/v1/clients/?search=john" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Pagination
curl -X GET "http://localhost:8000/api/v1/clients/?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python:**
```python
# List all clients
response = requests.get(
    "http://localhost:8000/api/v1/clients/",
    headers=headers
)
clients = response.json()

# Search clients
response = requests.get(
    "http://localhost:8000/api/v1/clients/",
    headers=headers,
    params={"search": "john"}
)
```

### Get Client by ID

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/clients/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Client

**Request:**
```bash
curl -X PUT "http://localhost:8000/api/v1/clients/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+9876543210",
    "notes": "Updated contact information"
  }'
```

**Python:**
```python
url = "http://localhost:8000/api/v1/clients/1"
data = {
    "phone": "+9876543210",
    "notes": "Updated contact information"
}
response = requests.put(url, headers=headers, json=data)
```

### Delete Client

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/clients/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Appointment Management

### Create Appointment

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/appointments/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "doctor_id": 2,
    "appointment_date": "2024-11-15T10:00:00",
    "duration_minutes": 30,
    "status": "scheduled",
    "reason": "Regular checkup",
    "notes": "Annual physical examination"
  }'
```

**Python:**
```python
from datetime import datetime, timedelta

url = "http://localhost:8000/api/v1/appointments/"

# Schedule appointment for tomorrow at 10 AM
appointment_time = datetime.now() + timedelta(days=1)
appointment_time = appointment_time.replace(hour=10, minute=0, second=0)

data = {
    "client_id": 1,
    "doctor_id": 2,
    "appointment_date": appointment_time.isoformat(),
    "duration_minutes": 30,
    "status": "scheduled",
    "reason": "Regular checkup",
    "notes": "Annual physical examination"
}
response = requests.post(url, headers=headers, json=data)
appointment = response.json()
print(f"Appointment created: {appointment['id']}")
```

### List Appointments

**Request:**
```bash
# List all appointments
curl -X GET "http://localhost:8000/api/v1/appointments/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by client
curl -X GET "http://localhost:8000/api/v1/appointments/?client_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by doctor
curl -X GET "http://localhost:8000/api/v1/appointments/?doctor_id=2" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by status
curl -X GET "http://localhost:8000/api/v1/appointments/?status=scheduled" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python:**
```python
# Get all appointments for a specific client
response = requests.get(
    "http://localhost:8000/api/v1/appointments/",
    headers=headers,
    params={"client_id": 1}
)
appointments = response.json()

# Get scheduled appointments
response = requests.get(
    "http://localhost:8000/api/v1/appointments/",
    headers=headers,
    params={"status": "scheduled"}
)
```

### Update Appointment Status

**Request:**
```bash
curl -X PUT "http://localhost:8000/api/v1/appointments/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "notes": "Checkup completed successfully"
  }'
```

**Python:**
```python
url = "http://localhost:8000/api/v1/appointments/1"
data = {
    "status": "completed",
    "notes": "Checkup completed successfully"
}
response = requests.put(url, headers=headers, json=data)
```

### Cancel Appointment

**Request:**
```bash
curl -X PUT "http://localhost:8000/api/v1/appointments/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "cancelled"}'
```

### Delete Appointment

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/appointments/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Complete Python Example

Here's a complete Python script that demonstrates the full workflow:

```python
import requests
from datetime import datetime, timedelta

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

class DrAssistentAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.headers = {}
    
    def login(self, username, password):
        """Login and store token."""
        url = f"{self.base_url}/auth/login"
        data = {"username": username, "password": password}
        response = requests.post(url, data=data)
        response.raise_for_status()
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        print("✓ Logged in successfully")
    
    def create_client(self, client_data):
        """Create a new client."""
        url = f"{self.base_url}/clients/"
        response = requests.post(url, headers=self.headers, json=client_data)
        response.raise_for_status()
        return response.json()
    
    def create_appointment(self, appointment_data):
        """Create a new appointment."""
        url = f"{self.base_url}/appointments/"
        response = requests.post(url, headers=self.headers, json=appointment_data)
        response.raise_for_status()
        return response.json()
    
    def get_clients(self, search=None):
        """Get list of clients."""
        url = f"{self.base_url}/clients/"
        params = {"search": search} if search else {}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

# Usage
api = DrAssistentAPI(BASE_URL)
api.login("admin", "admin123")

# Create a client
client_data = {
    "first_name": "Alice",
    "last_name": "Johnson",
    "email": "alice.johnson@example.com",
    "phone": "+1234567890",
    "date_of_birth": "1985-03-20",
    "gender": "female"
}
client = api.create_client(client_data)
print(f"✓ Created client: {client['first_name']} {client['last_name']}")

# Create an appointment
appointment_time = datetime.now() + timedelta(days=7)
appointment_data = {
    "client_id": client["id"],
    "doctor_id": 2,
    "appointment_date": appointment_time.isoformat(),
    "duration_minutes": 45,
    "reason": "Initial consultation"
}
appointment = api.create_appointment(appointment_data)
print(f"✓ Created appointment for {appointment_time.strftime('%Y-%m-%d %H:%M')}")

# List all clients
clients = api.get_clients()
print(f"✓ Total clients: {len(clients)}")
```

## Error Handling

All endpoints return standard HTTP status codes:

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **204 No Content** - Resource deleted successfully
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Authentication required or failed
- **404 Not Found** - Resource not found
- **422 Unprocessable Entity** - Validation error

**Example Error Response:**
```json
{
  "detail": "User with this email already exists"
}
```

**Python Error Handling:**
```python
try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
except requests.exceptions.HTTPError as e:
    print(f"Error: {e.response.json()['detail']}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

## JavaScript/TypeScript Example

```javascript
// Using fetch API
const BASE_URL = 'http://localhost:8000/api/v1';

// Login
async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData
  });
  
  const data = await response.json();
  return data.access_token;
}

// Create client
async function createClient(token, clientData) {
  const response = await fetch(`${BASE_URL}/clients/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(clientData)
  });
  
  return await response.json();
}

// Usage
const token = await login('admin', 'admin123');
const client = await createClient(token, {
  first_name: 'John',
  last_name: 'Doe',
  email: 'john@example.com'
});
```

## Testing with Swagger UI

The easiest way to test the API is using the built-in Swagger UI:

1. Visit http://localhost:8000/docs
2. Click the "Authorize" button (🔒 icon)
3. Enter username and password
4. Click "Authorize"
5. Now you can test any endpoint directly in the browser!

For more information, see the [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md).

