# Quick Deploy Reference - Next Steps

## Prerequisites (Get these ready first)

1. **OpenRouter API Key**: Sign up at https://openrouter.ai/ and get your API key
2. **Strong Secret Key**: Generate with `openssl rand -hex 32`
3. **GitHub Account**: For connecting Render and Vercel

---

## Exact Click-by-Click Steps

### Step 1: Neon Database (5 minutes)

1. Go to https://neon.tech/ → Sign up
2. Create new project: Name = `aahaar-production`, Region = `US East` or closest
3. **Copy the connection string** (looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`)
4. ✅ Done - keep this string safe for Step 2

---

### Step 2: Render Backend (10 minutes)

1. Go to https://render.com/ → Sign up with GitHub
2. New + → Web Service
3. Connect repository: `achal-vijayvargiya/Aahaar`
4. Configure:
   - Name: `aahaar-api`
   - Root Directory: `backend`
   - Runtime: Docker
   - Branch: `main`
   - Instance: Free
5. Click "Advanced" → Add environment variables:
   ```
   DATABASE_URL = <paste your Neon connection string>
   SECRET_KEY = <paste output of: openssl rand -hex 32>
   OPENROUTER_API_KEY = sk-or-v1-<your-key>
   ENVIRONMENT = production
   DEBUG = False
   BACKEND_CORS_ORIGINS = https://your-app.vercel.app
   ```
   ⚠️ You'll update `BACKEND_CORS_ORIGINS` in Step 4 after getting Vercel URL
6. Create Web Service (takes 5 min to deploy)
7. Once deployed, go to Shell tab and run:
   ```bash
   cd /app && alembic upgrade head
   ```
8. **Copy your Render URL**: `https://aahaar-api.onrender.com` (yours will be different)
9. Test it: Open `https://aahaar-api.onrender.com/health` - should see `{"status":"healthy"}`
10. ✅ Done - keep this URL for Step 3

---

### Step 3: Vercel Frontend (10 minutes)

#### Important: Frontend Repository Check

The main repository's `aahaar-wellness-hub/` directory is currently empty (appears to be a git submodule issue).

**You have two options:**

**Option A: Deploy separate frontend repo (if it exists)**
- If you have a separate `aahaar-wellness-hub` repository, deploy that directly
- Continue with steps below using that repo

**Option B: Fix submodule in main repo first**
- If frontend code should be in the main repo's `aahaar-wellness-hub/` directory
- First run: `git submodule update --init --recursive`
- Or copy frontend code into `aahaar-wellness-hub/` directory
- Commit and push changes
- Then continue with steps below

#### Deploy Steps:

1. Go to https://vercel.com/ → Sign up with GitHub
2. Add New → Project
3. Import repository:
   - **If separate repo**: Import `aahaar-wellness-hub` repository
   - **If in main repo**: Import `Aahaar` and set Root Directory to `aahaar-wellness-hub`
4. Configure:
   - Framework Preset: Vite (auto-detected)
   - Build Command: `npm run build`
   - Output Directory: `dist`
5. Add Environment Variable:
   ```
   VITE_API_BASE_URL = https://aahaar-api.onrender.com/api/v1
   ```
   ⚠️ Use YOUR Render URL from Step 2
6. Deploy (takes 2-3 min)
7. **Copy your Vercel URL**: `https://aahaar-wellness-hub.vercel.app` (yours will be different)
8. ✅ Done - update backend CORS in Step 4

---

### Step 4: Connect Frontend to Backend (3 minutes)

1. Go back to Render Dashboard → Your `aahaar-api` service
2. Environment tab → Find `BACKEND_CORS_ORIGINS`
3. Update value to your Vercel URL from Step 3:
   ```
   https://aahaar-wellness-hub.vercel.app
   ```
   (Use YOUR actual Vercel URL)
4. Save Changes
5. Wait 1-2 minutes for auto-redeploy
6. ✅ Done!

---

### Step 5: Verify Everything Works (5 minutes)

**Backend checks:**
```bash
# Should return healthy status
curl https://aahaar-api.onrender.com/health

# Should load Swagger API docs
open https://aahaar-api.onrender.com/docs
```

**Frontend checks:**
1. Open `https://aahaar-wellness-hub.vercel.app`
2. Open browser DevTools (F12) → Console tab
3. Should see no CORS errors
4. Try logging in or accessing the app

**✅ If both work, you're done! Share the Vercel URL with clients.**

---

## What to Share with Clients

**Demo Link**: `https://aahaar-wellness-hub.vercel.app`

**Important Notes for Clients:**
- First load may take 30-60 seconds (free tier cold start)
- Refresh if it times out, it'll be fast after that
- Fully functional demo with AI-powered diet planning

---

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Backend 503 error | Wait 60 seconds (cold start), then refresh |
| CORS error in browser | Update `BACKEND_CORS_ORIGINS` in Render with correct Vercel URL |
| Frontend "Failed to fetch" | Check `VITE_API_BASE_URL` in Vercel points to correct Render URL |
| Database connection error | Verify `DATABASE_URL` in Render matches Neon connection string |
| AI generation fails | Check `OPENROUTER_API_KEY` in Render is correct and has credits |

---

## Summary of Your URLs

After deployment, you'll have:

```
Frontend:  https://aahaar-wellness-hub.vercel.app  (your actual URL)
Backend:   https://aahaar-api.onrender.com         (your actual URL)
API Docs:  https://aahaar-api.onrender.com/docs
Database:  ep-xxx.region.aws.neon.tech            (internal, Neon URL)
```

**Total time**: ~30 minutes  
**Total cost**: $0/month (100% free tier)

---

## After Demo Success - Optional Upgrades

If clients love it and you want always-on service:

- **Render Pro**: $7/month (no spin-down)
- **Neon Scale**: $19/month (more storage/compute)  
- **Vercel Pro**: $20/month (more bandwidth)

But start with free tier - it's perfect for demos!

---

Need help? See full guide: `docs/FREE_TIER_DEPLOY.md`
