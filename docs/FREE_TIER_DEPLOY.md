# Free-Tier Deployment Guide for Aahaar

This guide walks you through deploying Aahaar to free-tier services for a live client demo:

- **Database**: Neon (PostgreSQL free tier)
- **Backend API**: Render (free web service)
- **Frontend**: Vercel (Hobby tier)

**Estimated setup time**: 30-45 minutes

---

## Overview

After following this guide, you will have:

- ✅ A production PostgreSQL database on Neon (always-on, free tier)
- ✅ FastAPI backend deployed to Render with automatic HTTPS
- ✅ React frontend deployed to Vercel with automatic HTTPS
- ✅ A public URL to share with clients for demos

---

## Prerequisites

Before starting, gather the following:

1. GitHub account (for connecting Render and Vercel)
2. OpenRouter API key (get from https://openrouter.ai/)
   - Required for AI diet plan generation
   - Free credits available for testing
3. Strong secret key for JWT tokens (generate with: `openssl rand -hex 32`)

---

## Part 1: Database Setup (Neon)

### 1.1 Create Neon Account

1. Go to https://neon.tech/
2. Sign up with GitHub or email
3. Confirm your email address

### 1.2 Create Database Project

1. Click **"Create a project"**
2. Fill in project details:
   - **Project name**: `aahaar-production`
   - **Region**: Choose closest to your users (e.g., `US East (Ohio)` or `Asia-Pacific`)
   - **PostgreSQL version**: 16 (default)
3. Click **"Create project"**

### 1.3 Copy Connection String

1. On the project dashboard, find the **Connection string** section
2. Select **"Pooled connection"** (recommended for serverless)
3. Copy the connection string - it looks like:
   ```
   postgresql://user:password@ep-xxx-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
4. **Save this securely** - you'll need it for Render configuration

### 1.4 Verify Database

```bash
# Test connection (optional, if you have psql installed locally)
psql "postgresql://user:password@ep-xxx.aws.neon.tech/neondb?sslmode=require"
```

✅ **Neon setup complete!** Your database is ready and always-on.

---

## Part 2: Backend Deployment (Render)

### 2.1 Create Render Account

1. Go to https://render.com/
2. Sign up with GitHub
3. Authorize Render to access your repositories

### 2.2 Create Web Service

1. From Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `achal-vijayvargiya/Aahaar`
3. Configure the service:
   - **Name**: `aahaar-api` (or your preferred name)
   - **Region**: Same as Neon (e.g., Oregon)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Instance Type**: `Free`

### 2.3 Configure Environment Variables

Click **"Advanced"** and add these environment variables:

#### Required Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql://...` | Paste your Neon connection string |
| `SECRET_KEY` | `<generated-key>` | Generate with `openssl rand -hex 32` |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | Your OpenRouter API key |
| `ENVIRONMENT` | `production` | |
| `DEBUG` | `False` | Important for production |
| `LOG_LEVEL` | `INFO` | |
| `DIET_PLAN_MODEL` | `openai/gpt-4o-mini` | Already set in config |
| `BACKEND_CORS_ORIGINS` | `https://your-app.vercel.app` | Update after Vercel deployment (Step 3) |

#### Optional Variables (already have defaults)

- `DIET_PLAN_TEMPERATURE`: `0.7`
- `FOOD_ENRICHMENT_MODEL`: `qwen/qwen-2.5-72b-instruct`
- `FOOD_ENRICHMENT_TEMPERATURE`: `0.3`

### 2.4 Create Service

1. Click **"Create Web Service"**
2. Render will automatically:
   - Build your Docker image
   - Deploy to a subdomain like `aahaar-api.onrender.com`
   - Provide automatic HTTPS

### 2.5 Run Database Migrations

Once the service is deployed and running:

1. Go to your service page on Render
2. Click **"Shell"** in the left sidebar
3. Run the migration script:
   ```bash
   cd /app
   alembic upgrade head
   ```
4. Wait for migrations to complete (should see "Running upgrade..." messages)

**Alternative**: Set up a one-off job:
1. Click **"Jobs"** in the left sidebar
2. Create a new job with command: `/app/scripts/migrate_production.sh`
3. Run it once

### 2.6 Verify Backend

1. Your API URL: `https://aahaar-api.onrender.com`
2. Test endpoints:
   - **Health check**: `https://aahaar-api.onrender.com/health`
   - **API docs**: `https://aahaar-api.onrender.com/docs`
   - **API root**: `https://aahaar-api.onrender.com/`

Expected response from `/health`:
```json
{
  "status": "healthy",
  "environment": "production",
  "version": "1.0.0"
}
```

✅ **Backend deployed!** Note the Render URL for the next step.

### ⚠️ Free Tier Limitations (Render)

- **Spin-down**: Service sleeps after 15 minutes of inactivity
- **Cold starts**: First request after sleep takes 30-60 seconds
- **Runtime**: 750 hours/month (sufficient for demos)
- **Solution**: Keep service warm by pinging `/health` every 10-15 minutes (optional)

---

## Part 3: Frontend Deployment (Vercel)

### 3.1 Prerequisites

The frontend repository `aahaar-wellness-hub` needs to be properly set up. You have two options:

#### Option A: Deploy Frontend Submodule Directly (Recommended)

If `aahaar-wellness-hub` exists as a separate repository:

1. Go to the separate frontend repository on GitHub
2. Deploy that repository directly to Vercel (skip to section 3.2)

#### Option B: Deploy from Main Repository

If the frontend is in the main repo's `aahaar-wellness-hub/` directory:

1. Ensure the directory contains a React/Vite project with `package.json`
2. Continue with section 3.2 below

### 3.2 Create Vercel Account

1. Go to https://vercel.com/
2. Sign up with GitHub
3. Authorize Vercel to access your repositories

### 3.3 Import Project

1. From Vercel Dashboard, click **"Add New..."** → **"Project"**
2. Import your repository:
   - **Option A**: Import the separate frontend repo `aahaar-wellness-hub`
   - **Option B**: Import `Aahaar` and set **Root Directory** to `aahaar-wellness-hub`
3. Vercel should auto-detect **"Vite"** as the framework

### 3.4 Configure Project

**Framework Preset**: Vite (auto-detected)

**Root Directory**: 
- Option A: `.` (root)
- Option B: `aahaar-wellness-hub`

**Build Settings**:
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

### 3.5 Add Environment Variables

Click **"Environment Variables"** and add:

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://aahaar-api.onrender.com/api/v1` |

**Note**: Replace `aahaar-api.onrender.com` with your actual Render URL from Part 2.

### 3.6 Deploy

1. Click **"Deploy"**
2. Vercel will:
   - Install dependencies
   - Build your React app
   - Deploy to a subdomain like `aahaar-wellness-hub.vercel.app`
   - Provide automatic HTTPS

### 3.7 Get Your Frontend URL

After deployment:
- Your app URL: `https://aahaar-wellness-hub.vercel.app`
- You can add a custom domain later (optional)

✅ **Frontend deployed!** Now connect it to the backend.

---

## Part 4: Connect Frontend to Backend

### 4.1 Update Backend CORS

The backend needs to allow requests from your Vercel frontend.

1. Go to Render Dashboard → Your `aahaar-api` service
2. Click **"Environment"** → **"Environment Variables"**
3. Find `BACKEND_CORS_ORIGINS` and update it:
   ```
   https://aahaar-wellness-hub.vercel.app
   ```
   - If you have multiple frontends (e.g., custom domain), use comma separation:
     ```
     https://aahaar-wellness-hub.vercel.app,https://www.your-domain.com
     ```
4. Click **"Save Changes"**
5. Render will automatically redeploy the backend

### 4.2 Wait for Redeploy

- Render will restart the service (takes 1-2 minutes)
- Monitor the "Events" tab for deployment status

### 4.3 Verify Connection

1. Open your frontend: `https://aahaar-wellness-hub.vercel.app`
2. Try to log in or access the API
3. Check browser console for any CORS errors (should be none)

✅ **Full stack connected!** Your demo app is live.

---

## Part 5: Test Your Deployment

### 5.1 Backend Tests

```bash
# Health check (should respond immediately)
curl https://aahaar-api.onrender.com/health

# API documentation (should load Swagger UI)
open https://aahaar-api.onrender.com/docs

# Test authentication endpoint
curl -X POST https://aahaar-api.onrender.com/api/v1/platform/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test"}'
```

### 5.2 Frontend Tests

1. **Navigate to your frontend**: `https://aahaar-wellness-hub.vercel.app`
2. **Test user flows**:
   - ✅ Login page loads
   - ✅ API calls work (check Network tab)
   - ✅ No CORS errors in console
   - ✅ UI renders correctly
3. **Test key features**:
   - Client management
   - Health profile creation
   - Diet plan generation (uses OpenRouter API)

### 5.3 Demo Checklist

Before sharing with clients:

- [ ] Backend `/health` endpoint responds
- [ ] Backend `/docs` loads (Swagger UI)
- [ ] Frontend loads without errors
- [ ] Login/authentication works
- [ ] Can create a test client
- [ ] Can generate a test diet plan
- [ ] No console errors in browser
- [ ] Mobile-responsive design works

---

## Part 6: Share with Clients

### 6.1 Demo URL

Share this URL with clients:
```
https://aahaar-wellness-hub.vercel.app
```

### 6.2 Demo Credentials

**Important**: Create a demo account for clients to test:

```bash
# Option 1: Use API docs to create a user
# Go to: https://aahaar-api.onrender.com/docs
# Use the POST /api/v1/platform/auth/register endpoint

# Option 2: Create via psql (if you have access)
# Use your Neon connection string
```

### 6.3 Client Testing Guide

Provide clients with:

1. **URL**: `https://aahaar-wellness-hub.vercel.app`
2. **Demo credentials**: (username/password you created)
3. **Test scenario**: "Try creating a client and generating a diet plan"
4. **Note about cold starts**: "First load may take 30-60 seconds if the service was idle"

---

## Troubleshooting

### Backend Issues

#### Problem: "Service Unavailable" or 503 errors
- **Cause**: Free tier spin-down
- **Solution**: Wait 30-60 seconds for cold start, then retry

#### Problem: "Database connection failed"
- **Check**: `DATABASE_URL` is set correctly in Render
- **Verify**: Neon database is accessible (check Neon dashboard)
- **Test**: Run `alembic upgrade head` in Render Shell

#### Problem: "CORS errors" in browser console
- **Check**: `BACKEND_CORS_ORIGINS` includes your Vercel URL
- **Verify**: No trailing slashes in URLs
- **Update**: Save changes in Render and wait for redeploy

#### Problem: "AI generation fails"
- **Check**: `OPENROUTER_API_KEY` is set correctly
- **Verify**: API key has credits (check OpenRouter dashboard)
- **Test**: Try with a different model if quota exceeded

### Frontend Issues

#### Problem: "Failed to fetch" errors
- **Check**: `VITE_API_BASE_URL` is set correctly in Vercel
- **Verify**: Backend is running (check `/health`)
- **Update**: Redeploy frontend after changing env vars

#### Problem: "404 Not Found" on page refresh
- **Check**: `vercel.json` has correct rewrite rules (should be present)
- **Fix**: Vercel should handle SPA routing automatically

#### Problem: Build fails on Vercel
- **Check**: `package.json` exists in root or correct directory
- **Verify**: `npm install` works locally
- **Check**: Node version compatibility

---

## Monitoring & Maintenance

### Check Service Health

- **Backend**: https://aahaar-api.onrender.com/health
- **Frontend**: https://aahaar-wellness-hub.vercel.app

### View Logs

**Render logs**:
1. Go to Render Dashboard → `aahaar-api` service
2. Click **"Logs"** tab
3. Filter by time range or search keywords

**Vercel logs**:
1. Go to Vercel Dashboard → Your project
2. Click **"Deployments"**
3. Click on a deployment → **"View Function Logs"**

### Keep Service Warm (Optional)

To avoid cold starts during demos:

1. Use a cron service like cron-job.org or Uptime Robot
2. Ping `https://aahaar-api.onrender.com/health` every 10-15 minutes
3. Free tier: 750 hours/month allows for ~25 days of constant uptime

---

## Cost Breakdown (Free Tier)

| Service | Plan | Cost | Limitations |
|---------|------|------|-------------|
| Neon | Free | $0 | 0.5 GB storage, always-on |
| Render | Free | $0 | Spins down after 15 min, 750 hrs/month |
| Vercel | Hobby | $0 | 100 GB bandwidth, unlimited deployments |
| **Total** | | **$0/month** | Sufficient for demos and light usage |

### Paid Upgrades (Optional, if scaling needed)

- **Render**: $7/month (no spin-down, always-on)
- **Neon**: $19/month (10 GB storage, more compute)
- **Vercel**: $20/month (1 TB bandwidth, custom domains)

---

## Next Steps

### After Demo Validation

1. **Custom domain**: Add your domain in Vercel and Render
2. **SSL certificates**: Automatic with Render and Vercel
3. **Monitoring**: Set up Sentry or LogRocket for error tracking
4. **Analytics**: Add Google Analytics or Plausible
5. **Upgrade**: If demo is successful, upgrade to paid tiers for always-on service

### Code Changes

To update the deployment after making code changes:

1. **Backend**: Push to GitHub → Render auto-deploys
2. **Frontend**: Push to GitHub → Vercel auto-deploys
3. **Database**: Run migrations via Render Shell

---

## Security Notes

### Secrets Management

✅ **Do**:
- Use strong, randomly generated `SECRET_KEY`
- Rotate API keys periodically
- Use environment variables (never commit secrets)
- Enable 2FA on Neon, Render, and Vercel

❌ **Don't**:
- Commit `.env` files
- Share secrets in plaintext
- Use weak passwords for demo accounts
- Expose `DATABASE_URL` publicly

### Production Hardening

- [x] `DEBUG=False` in production
- [x] HTTPS enforced (automatic with Render/Vercel)
- [x] CORS restricted to your frontend URL
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] Password hashing (bcrypt)
- [ ] Rate limiting (TODO - add if needed)
- [ ] API key rotation policy (TODO - document)

---

## Support

### Useful Links

- **Neon docs**: https://neon.tech/docs/
- **Render docs**: https://render.com/docs
- **Vercel docs**: https://vercel.com/docs
- **OpenRouter docs**: https://openrouter.ai/docs

### Getting Help

- Check logs in Render/Vercel dashboards
- Review this guide's Troubleshooting section
- Check service status pages:
  - https://neon.tech/status
  - https://www.renderstatus.com/
  - https://www.vercel-status.com/

---

## Summary

You now have a fully deployed Aahaar stack:

1. ✅ **Database**: Neon PostgreSQL (always-on)
2. ✅ **Backend**: Render FastAPI (auto HTTPS, free tier)
3. ✅ **Frontend**: Vercel React (auto HTTPS, free tier)
4. ✅ **Public URL**: Share with clients for demos
5. ✅ **Total cost**: $0/month

**Your demo URL**: `https://aahaar-wellness-hub.vercel.app`

Happy demoing! 🎉
