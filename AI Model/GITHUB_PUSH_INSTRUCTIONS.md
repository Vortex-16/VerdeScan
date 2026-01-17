# 📤 GitHub Push Instructions

Complete step-by-step guide to push Verde Scan to GitHub.

---

## 🎯 Repository Information

**Repository URL**: https://github.com/PyRaghaw/verde_scan.git  
**Branch**: main

---

## ⚡ Quick Push (Copy-Paste Commands)

Open your terminal in the `verde_scan` directory and run these commands:

```bash
# Initialize git repository
git init

# Add remote repository
git remote add origin https://github.com/PyRaghaw/verde_scan.git

# Create and switch to main branch
git checkout -b main

# Add all files
git add .

# Create commit
git commit -m "Initial commit: Complete Verde Scan forest monitoring system

Features:
- ResNet50-based ML model for tree health classification
- FastAPI backend with async processing
- Interactive web dashboard
- Docker deployment configuration
- Complete training pipeline
- Comprehensive documentation

Built for Build with Gemini Hackathon - IIT Kharagpur Kshitij 2026"

# Push to GitHub
git push -u origin main
```

---

## 📋 Step-by-Step Instructions

### Step 1: Initialize Git Repository

```bash
git init
```

**Expected output:**
```
Initialized empty Git repository in /path/to/verde_scan/.git/
```

---

### Step 2: Add Remote Repository

```bash
git remote add origin https://github.com/PyRaghaw/verde_scan.git
```

**Verify remote:**
```bash
git remote -v
```

**Expected output:**
```
origin  https://github.com/PyRaghaw/verde_scan.git (fetch)
origin  https://github.com/PyRaghaw/verde_scan.git (push)
```

---

### Step 3: Create Main Branch

```bash
git checkout -b main
```

**Expected output:**
```
Switched to a new branch 'main'
```

---

### Step 4: Check Status

```bash
git status
```

This will show all untracked files. You should see:
- Python files (`.py`)
- Configuration files (`.yml`, `.env.example`)
- Documentation (`.md`)
- Directories (`api/`, `core/`, `ml_models/`, etc.)

**Note:** The `.gitignore` file will exclude:
- `venv/` (virtual environment)
- `__pycache__/` (Python cache)
- `*.pth` (large model files)
- `hackathon_dataset/` (large dataset)
- `data/` (generated data)

---

### Step 5: Add Files

```bash
git add .
```

**Verify what will be committed:**
```bash
git status
```

You should see files in green (staged for commit).

---

### Step 6: Create Commit

```bash
git commit -m "Initial commit: Complete Verde Scan forest monitoring system

Features:
- ResNet50-based ML model for tree health classification
- FastAPI backend with async processing
- Interactive web dashboard
- Docker deployment configuration
- Complete training pipeline
- Comprehensive documentation

Built for Build with Gemini Hackathon - IIT Kharagpur Kshitij 2026"
```

**Expected output:**
```
[main (root-commit) abc1234] Initial commit: Complete Verde Scan...
 XX files changed, XXXX insertions(+)
 create mode 100644 README.md
 create mode 100644 requirements.txt
 ...
```

---

### Step 7: Push to GitHub

```bash
git push -u origin main
```

**What happens:**
- `-u` sets upstream tracking
- `origin` is the remote name
- `main` is the branch name

---

## 🔐 Authentication

### Option 1: Personal Access Token (Recommended)

1. **Generate Token on GitHub:**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (full control)
   - Click "Generate token"
   - **Copy the token** (you won't see it again!)

2. **Use Token When Pushing:**
   ```bash
   git push -u origin main
   ```
   
   When prompted:
   - **Username**: PyRaghaw
   - **Password**: [paste your token]

3. **Save Credentials (Optional):**
   ```bash
   git config --global credential.helper store
   ```

### Option 2: SSH Key

1. **Generate SSH Key:**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **Add to SSH Agent:**
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

3. **Add to GitHub:**
   - Copy public key: `cat ~/.ssh/id_ed25519.pub`
   - Go to: https://github.com/settings/keys
   - Click "New SSH key"
   - Paste and save

4. **Change Remote to SSH:**
   ```bash
   git remote set-url origin git@github.com:PyRaghaw/verde_scan.git
   ```

5. **Push:**
   ```bash
   git push -u origin main
   ```

---

## ✅ Verify Push

After pushing, verify on GitHub:

1. **Visit Repository:**
   https://github.com/PyRaghaw/verde_scan

2. **Check Files:**
   - README.md should be displayed
   - All directories should be visible
   - Commit message should be shown

3. **Check Branches:**
   - Should show "main" branch
   - Should show commit count

---

## 🔧 Troubleshooting

### Error: "Repository not found"

**Solution:**
1. Make sure repository exists on GitHub
2. Check repository name spelling
3. Verify you have access to the repository

**Create repository on GitHub:**
```bash
# Go to: https://github.com/new
# Repository name: verde_scan
# Description: AI-powered forest monitoring system
# Public or Private: Your choice
# Don't initialize with README (we already have one)
# Click "Create repository"
```

---

### Error: "Authentication failed"

**Solution:**
1. Use Personal Access Token instead of password
2. Or set up SSH keys (see above)

---

### Error: "Updates were rejected"

**Solution:**
```bash
# If repository has existing content
git pull origin main --allow-unrelated-histories
git push -u origin main
```

---

### Error: "Large files detected"

**Solution:**
The `.gitignore` should prevent this, but if it happens:

```bash
# Remove large files from staging
git rm --cached ml_models/*.pth
git rm --cached -r hackathon_dataset/

# Commit and push
git commit -m "Remove large files"
git push -u origin main
```

---

## 📊 What Gets Pushed

### ✅ Included Files:
- Source code (`.py` files)
- Configuration files
- Documentation (`.md` files)
- Docker files
- Requirements
- Frontend files
- Test files

### ❌ Excluded Files (via .gitignore):
- Virtual environment (`venv/`)
- Python cache (`__pycache__/`)
- Trained models (`*.pth`)
- Dataset (`hackathon_dataset/`)
- Generated data (`data/`)
- Logs (`logs/`)
- IDE files (`.vscode/`)

---

## 🎉 After Successful Push

### 1. Add Repository Description

On GitHub:
- Click "About" (gear icon)
- Add description: "AI-powered forest monitoring system using drone imagery and deep learning"
- Add topics: `machine-learning`, `computer-vision`, `fastapi`, `pytorch`, `forest-monitoring`, `hackathon`
- Add website: Your deployment URL (if any)

### 2. Enable GitHub Pages (Optional)

- Go to Settings → Pages
- Source: Deploy from branch
- Branch: main, folder: /docs (if you have docs)

### 3. Add Badges to README

Already included in README.md!

### 4. Create Releases

```bash
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

Then create release on GitHub with release notes.

---

## 🔄 Future Updates

### Making Changes

```bash
# Make your changes to files

# Check what changed
git status
git diff

# Add changes
git add .

# Commit
git commit -m "Description of changes"

# Push
git push origin main
```

### Creating Branches

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push branch
git push origin feature/new-feature

# Create Pull Request on GitHub
```

---

## 📞 Need Help?

If you encounter issues:

1. **Check Git status:**
   ```bash
   git status
   ```

2. **Check remote:**
   ```bash
   git remote -v
   ```

3. **Check branch:**
   ```bash
   git branch
   ```

4. **View commit history:**
   ```bash
   git log --oneline
   ```

---

## 🎯 Quick Reference

```bash
# Common Git commands
git status              # Check status
git add .              # Stage all changes
git commit -m "msg"    # Commit changes
git push               # Push to remote
git pull               # Pull from remote
git log                # View history
git branch             # List branches
git checkout -b name   # Create branch
```

---

**Happy Pushing! 🚀**

Your complete forest monitoring system is now on GitHub!
