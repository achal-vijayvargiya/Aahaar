# DrAssistent Backend - Project Overview

## 📋 Executive Summary

A production-ready FastAPI backend for healthcare management that provides:
- User authentication and authorization
- Client/patient management
- Appointment scheduling
- Complete API with auto-generated documentation
- Docker containerization for easy deployment
- Comprehensive logging and testing

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Clients                     │
│  (React Web App, React Native Mobile, Other Services)  │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP/HTTPS (REST API)
                  ↓
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │            Authentication Layer                  │   │
│  │         (JWT Token Verification)                 │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │              API Routers                         │   │
│  │  - Auth    - Users    - Clients                  │   │
│  │  - Appointments                                  │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Business Logic                         │   │
│  │  (Pydantic Schemas, SQLAlchemy Models)          │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Database Layer                      │   │
│  │          (SQLAlchemy ORM)                        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Database                         │
│  - users         - clients        - appointments         │
└─────────────────────────────────────────────────────────┘
```

## 🔄 Request Flow

```
1. Client Request
   ↓
2. CORS Middleware (validate origin)
   ↓
3. Authentication (JWT token verification)
   ↓
4. API Router (endpoint mapping)
   ↓
5. Pydantic Schema (request validation)
   ↓
6. Business Logic (processing)
   ↓
7. SQLAlchemy ORM (database query)
   ↓
8. PostgreSQL Database
   ↓
9. Response Schema (response validation)
   ↓
10. JSON Response to Client
```

## 📦 Technology Stack

### Core Framework
- **FastAPI** (0.109.0) - Modern async web framework
- **Uvicorn** (0.27.0) - ASGI server
- **Python** (3.11+) - Programming language

### Database
- **PostgreSQL** (15) - Relational database
- **SQLAlchemy** (2.0.25) - ORM
- **Alembic** (1.13.1) - Database migrations
- **psycopg2** (2.9.9) - PostgreSQL adapter

### Security
- **python-jose** (3.3.0) - JWT token handling
- **passlib** (1.7.4) - Password hashing
- **bcrypt** (4.1.2) - Password encryption

### Validation
- **Pydantic** (2.5.3) - Data validation
- **email-validator** (2.1.0) - Email validation

### Logging
- **python-json-logger** (2.0.7) - Structured logging

### Development
- **pytest** - Testing framework
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

## 🗂️ Code Organization

### Models (Database Layer)
Located in `app/models/`:
- `user.py` - Healthcare professionals (doctors, admins, nurses)
- `client.py` - Patients/clients with medical history
- `appointment.py` - Scheduling and tracking appointments

### Schemas (Validation Layer)
Located in `app/schemas/`:
- Request validation (Create, Update schemas)
- Response serialization (Read schemas)
- Type safety and documentation

### Routers (API Layer)
Located in `app/routers/`:
- `auth.py` - Login, token management
- `users.py` - User CRUD operations
- `clients.py` - Client CRUD operations
- `appointments.py` - Appointment CRUD operations

### Utilities
Located in `app/utils/`:
- `logger.py` - Logging configuration
- `security.py` - Password hashing, JWT tokens

## 🔐 Security Features

### Authentication
- JWT (JSON Web Tokens) for stateless authentication
- Token expiration (configurable)
- Secure password hashing with bcrypt

### Authorization
- Role-based access (admin, doctor, nurse)
- User activation status
- Superuser privileges

### Data Protection
- SQL injection prevention (SQLAlchemy ORM)
- Input validation (Pydantic)
- CORS configuration
- Environment-based secrets

### Best Practices
- Passwords never stored in plain text
- Tokens include expiration
- Secure session management
- HTTPS support ready

## 📊 Database Schema

### Users Table
```sql
users (
  id SERIAL PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  username VARCHAR UNIQUE NOT NULL,
  hashed_password VARCHAR NOT NULL,
  full_name VARCHAR,
  role VARCHAR DEFAULT 'doctor',
  is_active BOOLEAN DEFAULT true,
  is_superuser BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)
```

### Clients Table
```sql
clients (
  id SERIAL PRIMARY KEY,
  first_name VARCHAR NOT NULL,
  last_name VARCHAR NOT NULL,
  email VARCHAR UNIQUE,
  phone VARCHAR,
  date_of_birth DATE,
  gender VARCHAR,
  address TEXT,
  medical_history TEXT,
  notes TEXT,
  assigned_doctor_id INTEGER REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)
```

### Appointments Table
```sql
appointments (
  id SERIAL PRIMARY KEY,
  client_id INTEGER REFERENCES clients(id) NOT NULL,
  doctor_id INTEGER REFERENCES users(id) NOT NULL,
  appointment_date TIMESTAMP NOT NULL,
  duration_minutes INTEGER DEFAULT 30,
  status VARCHAR DEFAULT 'scheduled',
  reason VARCHAR,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)
```

## 🚀 Deployment Options

### Option 1: Docker (Recommended)
```bash
docker-compose up -d
```
- Easiest setup
- Consistent environment
- Includes PostgreSQL

### Option 2: Cloud Platforms

#### Heroku
```bash
heroku create drassistent-api
heroku addons:create heroku-postgresql
git push heroku main
```

#### DigitalOcean App Platform
- Connect GitHub repository
- Auto-deploy on push
- Managed PostgreSQL database

#### AWS
- **ECS/Fargate** - Container deployment
- **RDS** - Managed PostgreSQL
- **ALB** - Load balancer

#### Azure
- **App Service** - Web app hosting
- **PostgreSQL** - Managed database

### Option 3: VPS (Ubuntu/Debian)
```bash
# Install dependencies
sudo apt update
sudo apt install python3.11 postgresql nginx

# Clone repository
git clone <repo>

# Setup and run
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📈 Performance Considerations

### Database
- Connection pooling (10 connections, 20 max overflow)
- Indexed columns (email, username, foreign keys)
- Efficient queries with SQLAlchemy

### API
- Async/await for I/O operations
- Pagination for list endpoints
- Efficient serialization with Pydantic

### Caching (Future Enhancement)
- Redis for session storage
- Query result caching
- Rate limiting

## 🧪 Testing Strategy

### Unit Tests
- Test individual functions
- Mock external dependencies
- Fast execution

### Integration Tests
- Test API endpoints
- Use in-memory SQLite
- Test authentication flow

### Test Coverage
```bash
pytest --cov=app --cov-report=html
```

## 📝 Logging Strategy

### Log Levels
- **DEBUG** - Detailed information for debugging
- **INFO** - General information (requests, responses)
- **WARNING** - Warning messages
- **ERROR** - Error messages
- **CRITICAL** - Critical issues

### Log Format
JSON structured logging:
```json
{
  "asctime": "2024-10-29 10:30:00",
  "name": "drassistent",
  "levelname": "INFO",
  "message": "User admin logged in successfully",
  "pathname": "/app/routers/auth.py",
  "lineno": 45
}
```

### Log Rotation
- Max size: 10MB per file
- Keep 5 backup files
- Automatic rotation

## 🔄 Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# Edit code in app/

# Test locally
docker-compose up -d
pytest
```

### 2. Database Changes
```bash
# Update models in app/models/
# Create migration
alembic revision --autogenerate -m "add new field"

# Apply migration
alembic upgrade head
```

### 3. Testing
```bash
# Run tests
pytest

# Check coverage
pytest --cov=app
```

### 4. Deployment
```bash
# Commit changes
git add .
git commit -m "Add new feature"
git push origin feature/new-feature

# Create pull request
# After review, merge to main
```

## 🎯 API Design Principles

### RESTful
- Resource-based URLs
- HTTP methods (GET, POST, PUT, DELETE)
- Proper status codes

### Consistent
- Uniform response format
- Standard error handling
- Predictable behavior

### Documented
- Auto-generated OpenAPI spec
- Interactive Swagger UI
- Request/response examples

### Versioned
- API version in URL (`/api/v1/`)
- Backward compatibility
- Deprecation warnings

## 🔮 Future Enhancements

### High Priority
- [ ] Email notifications (appointment reminders)
- [ ] File upload for medical documents
- [ ] Password reset flow
- [ ] Audit logging for compliance

### Medium Priority
- [ ] Real-time updates (WebSockets)
- [ ] Export data (PDF reports)
- [ ] Advanced search and filtering
- [ ] Multi-language support

### Low Priority
- [ ] Analytics dashboard
- [ ] Mobile push notifications
- [ ] Video consultation integration
- [ ] Payment processing

## 📊 Metrics and Monitoring

### Health Checks
- `/health` - Basic health check
- Database connection status
- Service availability

### Future Monitoring
- Request rate and latency
- Error rates
- Database query performance
- Resource utilization

### Recommended Tools
- **Sentry** - Error tracking
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **ELK Stack** - Log aggregation

## 🤝 Contributing

### Code Style
- Follow PEP 8
- Type hints required
- Docstrings for functions
- Meaningful variable names

### Testing
- Write tests for new features
- Maintain test coverage > 80%
- Test edge cases

### Documentation
- Update API docs
- Add code comments
- Update CHANGELOG.md

## 📞 Support and Resources

### Documentation
- **SETUP_COMPLETE.md** - Setup guide
- **QUICKSTART.md** - Quick start (5 min)
- **README.md** - Full documentation
- **API_EXAMPLES.md** - Usage examples

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### External Resources
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/docs/

## 📄 License

MIT License - Feel free to use in your projects!

---

**Project**: DrAssistent Backend API  
**Version**: 1.0.0  
**Created**: October 29, 2024  
**Stack**: FastAPI + PostgreSQL + Docker

