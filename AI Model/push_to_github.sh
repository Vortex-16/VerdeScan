#!/bin/bash

# Verde Scan - GitHub Push Script
# This script initializes git and pushes to GitHub

echo "🌲 Verde Scan - GitHub Push Script"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git is not installed. Please install git first.${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Step 1: Initializing Git Repository${NC}"
if [ -d ".git" ]; then
    echo "✅ Git repository already initialized"
else
    git init
    echo "✅ Git repository initialized"
fi

echo ""
echo -e "${BLUE}📋 Step 2: Adding Remote Repository${NC}"
git remote remove origin 2>/dev/null
git remote add origin https://github.com/PyRaghaw/verde_scan.git
echo "✅ Remote repository added"

echo ""
echo -e "${BLUE}📋 Step 3: Checking Current Branch${NC}"
CURRENT_BRANCH=$(git branch --show-current)
if [ -z "$CURRENT_BRANCH" ]; then
    echo "Creating main branch..."
    git checkout -b main
else
    echo "Current branch: $CURRENT_BRANCH"
    if [ "$CURRENT_BRANCH" != "main" ]; then
        echo "Switching to main branch..."
        git checkout -b main 2>/dev/null || git checkout main
    fi
fi

echo ""
echo -e "${BLUE}📋 Step 4: Adding Files to Git${NC}"
git add .
echo "✅ Files added to staging"

echo ""
echo -e "${BLUE}📋 Step 5: Creating Commit${NC}"
git commit -m "Initial commit: Complete Verde Scan forest monitoring system

Features:
- ResNet50-based ML model for tree health classification
- FastAPI backend with async processing
- Interactive web dashboard
- Docker deployment configuration
- Complete training pipeline
- Comprehensive documentation

Built for Build with Gemini Hackathon - IIT Kharagpur Kshitij 2026"

if [ $? -eq 0 ]; then
    echo "✅ Commit created successfully"
else
    echo "⚠️  No changes to commit or commit failed"
fi

echo ""
echo -e "${BLUE}📋 Step 6: Pushing to GitHub${NC}"
echo "Pushing to: https://github.com/PyRaghaw/verde_scan.git"
echo ""

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 SUCCESS! Repository pushed to GitHub${NC}"
    echo ""
    echo "📍 Repository URL: https://github.com/PyRaghaw/verde_scan"
    echo ""
    echo "Next steps:"
    echo "1. Visit your repository on GitHub"
    echo "2. Add a description and topics"
    echo "3. Enable GitHub Pages (optional)"
    echo "4. Set up GitHub Actions (optional)"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Push failed. Common issues:${NC}"
    echo "1. Authentication required - you may need to:"
    echo "   - Use a Personal Access Token instead of password"
    echo "   - Configure SSH keys"
    echo "2. Repository doesn't exist - create it on GitHub first"
    echo "3. No write access - check repository permissions"
    echo ""
    echo "To push manually:"
    echo "  git push -u origin main"
    echo ""
    exit 1
fi
