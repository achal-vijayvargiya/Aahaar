# Quick Start Guide - DrAssistent Backend

## 🚀 Get Started in 5 Minutes

### Step 1: Start with Docker (Easiest)

Open PowerShell in the `backend` directory and run:

```powershell
docker-compose up -d
```

Wait for the containers to start (about 30 seconds), then initialize the database:

```powershell
docker-compose exec api python scripts/init_db.py
```

### Step 2: Access Your API

Open your browser and visit:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Step 3: Login

Use these default credentials in the Swagger UI:

**Admin:**
- Username: `admin`
- Password: `admin123`

**Doctor:**
- Username: `doctor`
- Password: `doctor123`

### Step 4: Test the API

1. Go to http://localhost:8000/docs
2. Click on "Authorize" button (top right)
3. Enter username: `admin` and password: `admin123`
4. Click "Login" and you'll get a token
5. Now you can test all endpoints!

## 📋 Useful Commands

```powershell
# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f db

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# View all running containers
docker-compose ps

# Access database shell
docker-compose exec db psql -U postgres -d drassistent

# Run migrations
docker-compose exec api alembic upgrade head
```

## 🔧 Common Issues

**Port already in use:**
```powershell
# Stop the service using port 8000 or 5432
# Or change the port in docker-compose.yml
```

**Database connection error:**
```powershell
# Make sure PostgreSQL container is healthy
docker-compose ps db

# Restart the database
docker-compose restart db
```

**Permission errors with logs:**
```powershell
# Create logs directory
mkdir logs
```

## 📊 Optional: Access pgAdmin

To access the database GUI, start services with:

```powershell
docker-compose --profile tools up -d
```

Then visit http://localhost:5050:
- Email: `admin@drassistent.com`
- Password: `admin`

## 🛑 Stopping Everything

```powershell
docker-compose down
```

To remove all data:
```powershell
docker-compose down -v
```

## 🔐 Security Note

⚠️ The default credentials are for **development only**. 

Before deploying to production:
1. Change all passwords
2. Update `SECRET_KEY` in `.env`
3. Set `DEBUG=False`
4. Configure proper CORS origins

## 📚 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check out the [API documentation](http://localhost:8000/docs)
- Customize the models in `app/models/`
- Add your own endpoints in `app/routers/`

Happy coding! 🎉

