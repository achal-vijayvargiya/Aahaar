# Aahaar - Setup Guide for GitHub

This guide will help you prepare and push your Aahaar project to GitHub as a professional monorepo showcase.

## 📋 Pre-Push Checklist

### 1. Clean Up Sensitive Data

Before pushing, ensure you've removed:
- [ ] `.env` files (use `.env.example` instead)
- [ ] API keys and secrets
- [ ] Database credentials
- [ ] Personal information in code comments

### 2. Create Environment Template Files

**Backend** (`backend/.env.example`):
```env
DATABASE_URL=postgresql://user:password@localhost:5432/drassistent
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
ENVIRONMENT=development
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
LOG_LEVEL=INFO
```

**Frontend** (`aahaar-wellness-hub/.env.example`):
```env
VITE_API_URL=http://localhost:8000
```

**Mobile** (`aahaar-mobile/.env.example`):
```env
EXPO_PUBLIC_API_URL=http://localhost:8000
```

### 3. Remove Large/Unnecessary Files

Consider removing or adding to `.gitignore`:
- Large binary files (images, videos)
- Generated files that can be regenerated
- FAISS index files (can be regenerated from scripts)
- `node_modules/` (already in .gitignore)
- `venv/` (already in .gitignore)

### 4. Update Documentation

- [ ] Update README.md with your information
- [ ] Add screenshots/demo links if available
- [ ] Update author information
- [ ] Add deployment links if live

## 🚀 GitHub Setup Steps

### Step 1: Initialize Git Repository (if not already done)

```bash
# In the root directory (DrAssistent/)
git init
```

### Step 2: Add All Files

```bash
git add .
```

### Step 3: Create Initial Commit

```bash
git commit -m "Initial commit: Aahaar - Conscious Eating Divine Living full-stack wellness platform

- FastAPI backend with AI-powered diet planning
- React web dashboard
- React Native mobile app
- PostgreSQL database
- RAG-based knowledge base system"
```

### Step 4: Create GitHub Repository

1. Go to GitHub.com
2. Click "New repository"
3. Name it: `aahaar-wellness-platform` (or your preferred name)
4. Description: "Aahaar - Conscious Eating Divine Living | Full-stack holistic wellness management platform with AI-powered diet planning"
5. Set to **Public** (for showcase)
6. **Don't** initialize with README, .gitignore, or license (you already have them)
7. Click "Create repository"

### Step 5: Connect and Push

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/aahaar-wellness-platform.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## 📝 Repository Settings

### Recommended GitHub Repository Settings:

1. **Description**: "Full-stack holistic wellness management platform with AI-powered diet planning | FastAPI + React + React Native"

2. **Topics/Tags**: Add these topics for better discoverability:
   - `fastapi`
   - `react`
   - `react-native`
   - `typescript`
   - `postgresql`
   - `ai`
   - `rag`
   - `healthcare`
   - `nutrition`
   - `full-stack`
   - `monorepo`

3. **Website**: Add if you have a live demo

4. **Pin Repository**: Pin this to your GitHub profile

## 🎨 Enhance Your Repository

### Add Visual Elements

1. **Screenshots**: Add a `screenshots/` folder with:
   - Web dashboard screenshot
   - Mobile app screenshots
   - API documentation screenshot

2. **Architecture Diagram**: Add to README or create `docs/architecture.md`

3. **Demo Video**: Link to a demo video (YouTube, Loom, etc.)

### Update README with:

- [ ] Live demo links (if deployed)
- [ ] Screenshots/GIFs
- [ ] Architecture diagram
- [ ] Technology badges
- [ ] Your contact information
- [ ] Key achievements/metrics

## 🔒 Security Best Practices

1. **Never commit**:
   - `.env` files
   - API keys
   - Database passwords
   - Private keys
   - JWT secrets

2. **Use environment variables** for all sensitive data

3. **Review** your commit history before pushing:
   ```bash
   git log --oneline
   ```

4. **If you accidentally committed secrets**:
   - Use `git-filter-repo` or BFG Repo-Cleaner to remove them
   - Rotate all exposed credentials immediately

## 📊 LinkedIn Showcase Tips

### What to Highlight:

1. **Full-Stack Capabilities**: Mention all three parts (backend, web, mobile)

2. **AI Integration**: Emphasize the RAG system and AI-powered features

3. **Technologies**: List key technologies used

4. **Architecture**: Mention monorepo structure and system design

5. **Features**: Highlight unique features like Dosha assessment, knowledge base

### Sample LinkedIn Post:

```
🚀 Excited to share my latest project: Aahaar - Conscious Eating Divine Living - A full-stack holistic wellness management platform!

✨ What I Built:
• FastAPI backend with AI-powered diet planning using RAG
• React TypeScript web dashboard
• React Native mobile app (iOS & Android)
• PostgreSQL database with comprehensive health tracking
• Knowledge base system with semantic search (FAISS)

🎯 Key Features:
• AI-generated personalized meal plans
• Dosha & Gut Health assessments
• Cross-platform client management
• Real-time appointment scheduling

🛠️ Tech Stack: FastAPI, React, React Native, TypeScript, PostgreSQL, LangChain, FAISS

Check it out: [GitHub Link]

#FullStackDevelopment #AI #React #FastAPI #ReactNative #HealthcareTech
```

## 🎯 Next Steps After Pushing

1. **Deploy Backend**: Consider deploying to:
   - Railway
   - Render
   - DigitalOcean
   - AWS/GCP/Azure

2. **Deploy Web App**: Consider:
   - Vercel
   - Netlify
   - GitHub Pages

3. **Add CI/CD**: GitHub Actions for:
   - Automated testing
   - Code quality checks
   - Deployment

4. **Add Issues/Projects**: Create GitHub Issues for future enhancements

5. **Write Blog Post**: Consider writing a technical blog post about the project

## 📚 Additional Resources

- [GitHub Documentation](https://docs.github.com/)
- [Writing Great READMEs](https://www.makeareadme.com/)
- [Git Best Practices](https://www.atlassian.com/git/tutorials/comparing-workflows)

---

**Ready to showcase your amazing work! 🎉**

