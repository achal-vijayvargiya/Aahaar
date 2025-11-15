# DrAssistent Backend API

A FastAPI-based backend for healthcare assistant management with PostgreSQL database, Docker support, and file-based logging.

## Features

- 🚀 **FastAPI** - Modern, fast web framework for building APIs
- 🐘 **PostgreSQL** - Robust relational database
- 🐳 **Docker** - Containerized deployment with Docker Compose
- 📝 **File-based Logging** - Structured JSON logging with rotation
- 🔐 **JWT Authentication** - Secure token-based authentication
- 📊 **SQLAlchemy ORM** - Powerful database ORM
- 🔄 **Alembic Migrations** - Database version control
- 📚 **Auto-generated API Docs** - Interactive Swagger UI and ReDoc

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection setup
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── client.py
│   │   └── appointment.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── appointment.py
│   │   └── token.py
│   ├── routers/             # API routes
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── clients.py
│   │   └── appointments.py
│   └── utils/               # Utilities
│       ├── logger.py        # Logging configuration
│       └── security.py      # Security utilities
├── alembic/                 # Database migrations
├── scripts/                 # Helper scripts
│   └── init_db.py          # Database initialization
├── logs/                    # Application logs
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+ (for local development)

### Option 1: Using Docker (Recommended)

1. **Clone and navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start services with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database:**
   ```bash
   docker-compose exec api python scripts/init_db.py
   ```

5. **Access the API:**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

### Option 2: Local Development

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL database:**
   ```bash
   createdb drassistent
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Update DATABASE_URL in .env
   ```

5. **Initialize database:**
   ```bash
   python scripts/init_db.py
   ```

6. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login and get access token
- `GET /api/v1/auth/me` - Get current user information

### Users
- `GET /api/v1/users/` - List all users
- `GET /api/v1/users/{id}` - Get user by ID
- `POST /api/v1/users/` - Create new user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Clients
- `GET /api/v1/clients/` - List all clients (with search)
- `GET /api/v1/clients/{id}` - Get client by ID
- `POST /api/v1/clients/` - Create new client
- `PUT /api/v1/clients/{id}` - Update client
- `DELETE /api/v1/clients/{id}` - Delete client

### Appointments
- `GET /api/v1/appointments/` - List appointments (with filters)
- `GET /api/v1/appointments/{id}` - Get appointment by ID
- `POST /api/v1/appointments/` - Create new appointment
- `PUT /api/v1/appointments/{id}` - Update appointment
- `DELETE /api/v1/appointments/{id}` - Delete appointment

## Default Credentials

After running `init_db.py`, you can login with:

**Admin User:**
- Username: `admin`
- Password: `admin123`
- Email: `admin@drassistent.com`

**Doctor User:**
- Username: `doctor`
- Password: `doctor123`
- Email: `doctor@drassistent.com`

⚠️ **Change these passwords immediately in production!**

## Database Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

## Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild containers
docker-compose up -d --build

# Start with pgAdmin
docker-compose --profile tools up -d
```

## Logging

Logs are written to `logs/app.log` with:
- JSON format for structured logging
- Automatic rotation (10MB max per file)
- 5 backup files retained
- Console output in development

## Configuration

Key environment variables (in `.env`):

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API
DEBUG=True
ENVIRONMENT=development

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Logging
LOG_LEVEL=INFO
```

## Testing

Run tests with pytest:
```bash
pytest
```

## Production Deployment

1. **Update environment variables:**
   - Set strong `SECRET_KEY`
   - Set `DEBUG=False`
   - Set `ENVIRONMENT=production`
   - Configure proper `BACKEND_CORS_ORIGINS`

2. **Use production database:**
   - Set up managed PostgreSQL instance
   - Update `DATABASE_URL`

3. **Enable HTTPS:**
   - Use reverse proxy (Nginx, Traefik)
   - Configure SSL certificates

4. **Security checklist:**
   - Change default passwords
   - Enable firewall rules
   - Set up monitoring and alerts
   - Regular backups
   - Keep dependencies updated

## Troubleshooting

**Database connection issues:**
```bash
# Check if PostgreSQL is running
docker-compose ps db

# View database logs
docker-compose logs db
```

**API not starting:**
```bash
# View API logs
docker-compose logs api

# Restart API
docker-compose restart api
```

**Permission issues:**
```bash
# Fix log directory permissions
sudo chown -R $USER:$USER logs/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.

