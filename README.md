# Aahaar - Conscious Eating Divine Living

> **A full-stack healthcare and nutrition management system with AI-powered diet planning**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![React Native](https://img.shields.io/badge/React_Native-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactnative.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

## 🌟 Overview

**Aahaar - Conscious Eating Divine Living** is a comprehensive wellness management platform designed for holistic nutritionists and healthcare professionals. The system enables efficient client management, AI-powered personalized diet planning, health profile tracking, and cross-platform access through web and mobile applications.

### Key Features

- 🤖 **AI-Powered Diet Planning** - Intelligent meal plan generation using RAG (Retrieval-Augmented Generation)
- 📊 **Health Profile Management** - Comprehensive client health tracking with Dosha and Gut Health assessments
- 🥗 **Knowledge Base System** - Advanced food database with semantic search capabilities
- 📱 **Cross-Platform Access** - Web dashboard and React Native mobile app
- 🔐 **Secure Authentication** - JWT-based authentication with role-based access control
- 📅 **Appointment Scheduling** - Integrated appointment management system
- 🎯 **Personalized Recommendations** - Context-aware nutrition and wellness suggestions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                        │
│  ┌──────────────────────┐  ┌─────────────────────────────┐ │
│  │  Web Dashboard       │  │  Mobile App (React Native)  │ │
│  │  (React + TypeScript)│  │  (Expo + TypeScript)        │ │
│  └──────────┬───────────┘  └──────────────┬──────────────┘ │
└─────────────┼───────────────────────────────┼────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │ REST API
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Authentication & Authorization (JWT)                 │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  API Routers                                           │ │
│  │  • Auth  • Users  • Clients  • Appointments          │ │
│  │  • Health Profiles  • Diet Plans  • Quizzes           │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  AI Agent Layer                                       │ │
│  │  • Diet Plan Generation  • RAG System                │ │
│  │  • Knowledge Base Retrieval                           │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Knowledge Base System                                │ │
│  │  • FAISS Vector Store  • Food Database               │ │
│  │  • Semantic Search                                    │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Database                              │
│  • Users  • Clients  • Appointments  • Health Profiles      │
│  • Diet Plans  • Quiz Responses                              │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
DrAssistent/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   ├── utils/             # Utilities (AI agent, logger, etc.)
│   │   └── knowledge_base/    # RAG system & food database
│   ├── alembic/               # Database migrations
│   ├── scripts/               # Setup and utility scripts
│   ├── tests/                 # Backend tests
│   ├── docker-compose.yml     # Docker configuration
│   └── requirements.txt       # Python dependencies
│
├── aahaar-wellness-hub/        # Web Dashboard (React)
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom React hooks
│   │   └── lib/               # Utilities
│   ├── package.json
│   └── vite.config.ts
│
├── aahaar-mobile/              # Mobile App (React Native)
│   ├── src/
│   │   ├── components/        # React Native components
│   │   ├── screens/           # App screens
│   │   ├── navigation/        # Navigation setup
│   │   └── theme/             # Theme configuration
│   ├── app.json               # Expo configuration
│   └── package.json
│
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- **Backend**: Python 3.11+, PostgreSQL 15+, Docker (optional)
- **Web Frontend**: Node.js 18+, npm or yarn
- **Mobile App**: Node.js 18+, Expo CLI

### Backend Setup

```bash
cd backend

# Using Docker (Recommended)
docker-compose up -d
docker-compose exec api python scripts/init_db.py

# Or Local Development
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
```

**Backend runs on**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs

### Web Dashboard Setup

```bash
cd aahaar-wellness-hub
npm install
npm run dev
```

**Web app runs on**: http://localhost:5173

### Mobile App Setup

```bash
cd aahaar-mobile
npm install
npm start
```

Scan QR code with Expo Go app or run on simulator/emulator.

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **PostgreSQL** - Relational database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **LangChain** - AI/LLM integration
- **FAISS** - Vector similarity search
- **Pydantic** - Data validation
- **JWT** - Authentication

### Frontend (Web)
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **React Query** - Data fetching
- **React Router** - Routing

### Mobile
- **React Native** - Mobile framework
- **Expo** - Development platform
- **TypeScript** - Type safety
- **React Navigation** - Navigation

## 📚 Key Features Explained

### 1. AI-Powered Diet Planning
- Uses RAG (Retrieval-Augmented Generation) to generate personalized meal plans
- Leverages knowledge base with 770+ foods and nutrition data
- Context-aware recommendations based on client health profiles
- Supports Dosha-based and Gut Health-based meal planning

### 2. Knowledge Base System
- FAISS vector store for semantic food search
- Comprehensive food database with nutritional information
- Holistic nutrition guidelines and recommendations
- Efficient retrieval for AI agent context

### 3. Health Profile Management
- Dosha assessment quiz (Ayurvedic body type)
- Gut Health assessment quiz
- Comprehensive health profile tracking
- Progress monitoring and goal setting

### 4. Cross-Platform Access
- Responsive web dashboard for desktop/tablet
- Native mobile app for iOS and Android
- Consistent user experience across platforms
- Real-time data synchronization

## 📖 Documentation

### Backend Documentation
- [Backend README](backend/README.md) - Complete backend setup guide
- [API Examples](backend/API_EXAMPLES.md) - API usage examples
- [Project Overview](backend/PROJECT_OVERVIEW.md) - Architecture details
- [AI Diet Plan Guide](backend/AI_DIET_PLAN_FORMAT_GUIDE.md) - AI integration guide

### Frontend Documentation
- [Web Dashboard README](aahaar-wellness-hub/README.md)
- [Mobile App README](aahaar-mobile/README.md)

### Feature Documentation
- [AI Agent Implementation](CONVERSATIONAL_AI_AGENT_IMPLEMENTATION.md)
- [Knowledge Base System](ENHANCED_KB_SYSTEM_SUMMARY.md)
- [Food Retrieval Flow](FOOD_RETRIEVAL_FLOW_EXPLAINED.md)

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
pytest --cov=app --cov-report=html
```

### Frontend Tests
```bash
cd aahaar-wellness-hub
npm test
```

## 🐳 Docker Deployment

### Backend
```bash
cd backend
docker-compose up -d
```

### Full Stack (Future)
A docker-compose file at the root can orchestrate all services together.

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user

### Clients
- `GET /api/v1/clients/` - List clients
- `POST /api/v1/clients/` - Create client
- `GET /api/v1/clients/{id}` - Get client details
- `PUT /api/v1/clients/{id}` - Update client

### Health Profiles
- `GET /api/v1/health-profiles/{client_id}` - Get health profile
- `POST /api/v1/health-profiles/` - Create health profile
- `POST /api/v1/dosha-quiz/` - Submit Dosha quiz
- `POST /api/v1/gut-health-quiz/` - Submit Gut Health quiz

### Diet Plans
- `POST /api/v1/diet-plans/generate` - Generate AI diet plan
- `GET /api/v1/diet-plans/{client_id}` - Get client diet plan
- `PUT /api/v1/diet-plans/{id}` - Update diet plan

See [API Documentation](http://localhost:8000/docs) for complete API reference.

## 🔐 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control (Admin, Doctor, Nurse)
- CORS configuration
- Input validation with Pydantic
- SQL injection prevention (SQLAlchemy ORM)

## 🎯 Use Cases

1. **Nutritionists** - Manage clients, create personalized diet plans, track progress
2. **Holistic Health Practitioners** - Integrate Ayurvedic principles (Dosha) into recommendations
3. **Healthcare Clinics** - Centralized client management and appointment scheduling
4. **Wellness Coaches** - Track client health goals and provide AI-assisted recommendations

## 🚧 Future Enhancements

- [ ] Real-time notifications (WebSocket)
- [ ] Advanced analytics dashboard
- [ ] Meal plan templates library
- [ ] Client progress reports (PDF export)
- [ ] Integration with fitness trackers
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Offline mode for mobile app

## 🤝 Contributing

This is a portfolio project, but suggestions and feedback are welcome!

## 📄 License

MIT License - Feel free to use this as a reference for your projects.

## 👨‍💻 Author

**Your Name**  
*Full-Stack Developer | AI/ML Enthusiast*

- Portfolio: [Your Portfolio URL]
- LinkedIn: [Your LinkedIn URL]
- GitHub: [Your GitHub URL]

## 🙏 Acknowledgments

- FastAPI community for excellent documentation
- React and React Native teams
- All open-source contributors whose libraries made this possible

---

**Built with ❤️ for holistic wellness and better health management**

*Balance begins with awareness* 🌿

