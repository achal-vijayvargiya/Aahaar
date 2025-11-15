# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2024-10-29

### Added
- Initial FastAPI backend implementation
- PostgreSQL database integration with SQLAlchemy
- JWT-based authentication system
- User management endpoints
- Client/Patient management endpoints
- Appointment scheduling endpoints
- Docker and Docker Compose configuration
- File-based logging with JSON format and rotation
- Alembic database migrations
- Comprehensive API documentation with Swagger UI
- Test suite with pytest
- Database initialization script with sample data
- Development and production configurations
- CORS support for frontend integration
- Health check endpoint
- Makefile for common tasks
- Comprehensive README and documentation

### Security
- Password hashing with bcrypt
- JWT token authentication
- Environment-based configuration
- Secure password handling

### Features
- RESTful API design
- Auto-generated API documentation
- Database migrations support
- Docker containerization
- Structured logging
- Test coverage
- Development and production modes

## Database Schema

### Users Table
- User authentication and authorization
- Roles: admin, doctor, nurse
- Support for active/inactive users

### Clients Table
- Patient/client information
- Medical history tracking
- Assignment to doctors

### Appointments Table
- Appointment scheduling
- Status tracking (scheduled, completed, cancelled, no-show)
- Duration and notes support

## API Endpoints

### Authentication (`/api/v1/auth`)
- POST `/login` - User login
- GET `/me` - Get current user

### Users (`/api/v1/users`)
- GET `/` - List users
- GET `/{id}` - Get user by ID
- POST `/` - Create user
- PUT `/{id}` - Update user
- DELETE `/{id}` - Delete user

### Clients (`/api/v1/clients`)
- GET `/` - List clients (with search)
- GET `/{id}` - Get client by ID
- POST `/` - Create client
- PUT `/{id}` - Update client
- DELETE `/{id}` - Delete client

### Appointments (`/api/v1/appointments`)
- GET `/` - List appointments (with filters)
- GET `/{id}` - Get appointment by ID
- POST `/` - Create appointment
- PUT `/{id}` - Update appointment
- DELETE `/{id}` - Delete appointment

