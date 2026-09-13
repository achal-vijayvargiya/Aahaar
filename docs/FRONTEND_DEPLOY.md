# Frontend Deployment Notes

## Current Status

The `aahaar-wellness-hub/` directory in this repository is currently **empty**. This appears to be a git submodule that was not properly initialized or has been removed.

## Deployment Options

### Option 1: Deploy Separate Frontend Repository (Recommended)

If the frontend exists as a separate repository (e.g., `achal-vijayvargiya/aahaar-wellness-hub` or `achal-vijayvargiya/baseveda-wellness-hub`):

1. **Go to that repository** on GitHub
2. **Deploy it directly to Vercel** using the instructions in `docs/QUICK_DEPLOY.md`
3. **Use the root directory** (`.`) as the Vercel Root Directory
4. **Set environment variable**: `VITE_API_BASE_URL=https://your-api.onrender.com/api/v1`

### Option 2: Vendor Frontend Code Into Main Repo

If you want to deploy from this monorepo:

1. **Copy the frontend code** into the `aahaar-wellness-hub/` directory
2. **Ensure it has**: `package.json`, `src/`, `index.html`, `vite.config.ts`
3. **Commit and push** to GitHub
4. **Deploy to Vercel** with Root Directory set to `aahaar-wellness-hub`

### Option 3: Fix Git Submodule

If this was supposed to be a submodule:

```bash
# Find the submodule URL (check with repo owner)
# Then initialize it:
git submodule add <frontend-repo-url> aahaar-wellness-hub
git submodule update --init --recursive
git commit -m "Add frontend submodule"
git push
```

## Vercel Configuration

The `vercel.json` in the repository root is pre-configured for a Vite/React app:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "env": {
    "VITE_API_BASE_URL": "https://aahaar-api.onrender.com/api/v1"
  }
}
```

**Important**: Update `VITE_API_BASE_URL` in Vercel dashboard with your actual Render URL.

### What the Config Does

- **`rewrites`**: Enables SPA routing (all routes serve `index.html`)
- **`env.VITE_API_BASE_URL`**: Tells the frontend where the API is deployed
- **`outputDirectory: "dist"`**: Standard Vite build output location
- **Security headers**: Adds basic security headers to all responses

## Required Environment Variables for Vercel

Set these in the Vercel dashboard under **Settings → Environment Variables**:

| Variable | Value | Example |
|----------|-------|---------|
| `VITE_API_BASE_URL` | Your Render API URL + `/api/v1` | `https://aahaar-api.onrender.com/api/v1` |

## Troubleshooting Frontend Deployment

### Build Fails: "No package.json found"

**Problem**: The frontend directory is empty or misconfigured.

**Solution**: 
1. Check that `aahaar-wellness-hub/` contains a valid React/Vite project
2. Or deploy the frontend from its separate repository (Option 1)

### "Failed to fetch" in Browser Console

**Problem**: Frontend can't reach the backend API.

**Solutions**:
1. Verify `VITE_API_BASE_URL` is set correctly in Vercel
2. Check backend is running: `curl https://your-api.onrender.com/health`
3. Verify CORS is configured: Backend's `BACKEND_CORS_ORIGINS` must include your Vercel URL

### CORS Errors

**Problem**: Backend rejects requests from frontend.

**Solution**:
1. Go to Render dashboard → Your API service → Environment
2. Set `BACKEND_CORS_ORIGINS` to your Vercel URL: `https://your-app.vercel.app`
3. Save and wait for redeploy (1-2 minutes)

## Frontend Technology Stack

Based on the project documentation, the frontend uses:

- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Data Fetching**: React Query
- **Routing**: React Router

Ensure all these dependencies are in `package.json` of the frontend project.

## Next Steps

1. **Identify** which option above applies to your setup
2. **Follow** the corresponding deployment steps in `docs/QUICK_DEPLOY.md`
3. **Update** `BACKEND_CORS_ORIGINS` on Render after deployment
4. **Test** the deployed frontend thoroughly

## Questions?

- Check the full deployment guide: `docs/FREE_TIER_DEPLOY.md`
- Review the quick reference: `docs/QUICK_DEPLOY.md`
