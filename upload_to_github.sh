
#!/bin/bash
set -e  # Exit immediately on error

# Configuration
REPO_URL="https://github.com/caidavies1600-oss/RoW-v1.2.3.git"
GIT_USER="caidavies1600-oss"
EMAIL="ci@replitpush.com"
VERSION_FILE="version.txt"
ARCHIVE_DIR="previous_versions"

# Check for required environment variable
if [ -z "$GH_TOKEN" ]; then
  echo "❌ GH_TOKEN is not set. Add it to Replit Secrets."
  exit 1
fi

echo "🚀 Starting deployment process..."

# Get current version and bump it
if [ ! -f "$VERSION_FILE" ]; then
    echo "v1.0.0" > "$VERSION_FILE"
fi

CURRENT_VERSION=$(cat "$VERSION_FILE")
IFS='.' read -r MAJOR MINOR PATCH <<< "${CURRENT_VERSION#v}"
PATCH=$((PATCH + 1))
NEW_VERSION="v$MAJOR.$MINOR.$PATCH"
echo "$NEW_VERSION" > "$VERSION_FILE"

echo "🔧 Bumping version: $CURRENT_VERSION → $NEW_VERSION"

# Create a clean deployment directory
DEPLOY_DIR="deploy_temp"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

echo "📦 Copying bot files to deployment directory..."

# Copy ALL directories for Railway deployment
for dir in bot cogs config services utils sheets data scripts; do
    if [ -d "$dir" ]; then
        cp -r "$dir/" "$DEPLOY_DIR/" && echo "✅ Copied $dir/"
    else
        echo "⚠️ $dir/ directory not found"
    fi
done

# Remove logs from data directory if it exists (but keep data structure)
if [ -d "$DEPLOY_DIR/data/logs" ]; then
    rm -rf "$DEPLOY_DIR/data/logs"
    echo "🗑️ Removed logs from data directory"
fi

echo "⏭️ Skipping dashboard/ directory (excluded from deployment)"
echo "⏭️ Skipping attached_assets/ directory (excluded from deployment)"

# Copy ALL individual files needed for Railway
cp main.py "$DEPLOY_DIR/" 2>/dev/null && echo "✅ Copied main.py" || echo "⚠️ main.py not found"
cp requirements.txt "$DEPLOY_DIR/" 2>/dev/null && echo "✅ Copied requirements.txt" || echo "⚠️ requirements.txt not found"
cp README.md "$DEPLOY_DIR/" 2>/dev/null && echo "✅ Copied README.md" || echo "⚠️ README.md not found"
cp "$VERSION_FILE" "$DEPLOY_DIR/" && echo "✅ Copied $VERSION_FILE"

# Create comprehensive .gitignore for the deployment
cat > "$DEPLOY_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
data/logs/
logs/

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
deploy_temp/

# Local environment files (Railway will use environment variables)
.env
token.txt

# Replit specific (not needed on Railway)
.replit
replit.nix
.upm/

# Local backups
data/backups/

# Development files
attached_assets/
dashboard/
EOF

echo "✅ Created comprehensive .gitignore"

# Create Railway-specific files
cat > "$DEPLOY_DIR/railway.toml" << 'EOF'
[build]
builder = "nixpacks"

[deploy]
startCommand = "python main.py"
restartPolicyType = "always"

[environments.production.variables]
PYTHON_VERSION = "3.12"
EOF

echo "✅ Created railway.toml configuration"

# Create a deployment README with setup instructions
cat > "$DEPLOY_DIR/DEPLOYMENT.md" << 'EOF'
# Railway Deployment Setup

## Required Environment Variables

Set these in your Railway dashboard:

1. **BOT_TOKEN** - Your Discord bot token
2. **GOOGLE_SHEETS_CREDENTIALS** - Your Google service account JSON (optional)
3. **GOOGLE_SHEETS_ID** - Your Google Sheets ID (optional)

## Setup Steps

1. Connect this GitHub repo to Railway
2. Set the environment variables above
3. Deploy automatically starts with `python main.py`

## Server-Specific Configuration

Update `config/settings.py` with your Discord server's:
- Role IDs
- Channel IDs  
- Admin user IDs

The bot will work with default settings but customize for your server.

## Data Storage

- Bot uses JSON files in `data/` directory
- Google Sheets integration is optional
- All data persists between deployments

## Support

Check logs in Railway dashboard for any deployment issues.
EOF

echo "✅ Created deployment instructions"

# Archive previous version if it exists
if [ -d "$ARCHIVE_DIR" ]; then
    mkdir -p "$ARCHIVE_DIR/$CURRENT_VERSION"
    # Copy current repo state to archive (excluding deploy_temp)
    for item in *; do
        if [ "$item" != "$DEPLOY_DIR" ] && [ "$item" != "$ARCHIVE_DIR" ]; then
            cp -r "$item" "$ARCHIVE_DIR/$CURRENT_VERSION/" 2>/dev/null || true
        fi
    done
    echo "📁 Archived previous version: $CURRENT_VERSION"
fi

# Initialize git in deployment directory
cd "$DEPLOY_DIR"

echo "🔧 Setting up Git repository..."
git init
git config user.name "$GIT_USER"
git config user.email "$EMAIL"

# Create comprehensive commit message
COMMIT_MSG="🚀 Deploy RoW Bot $NEW_VERSION for Railway

✨ Features:
- Complete Discord RoW Bot with all modules
- Google Sheets integration (optional)
- Comprehensive admin commands
- Event management system
- Player statistics tracking
- Clean JSON data storage

🛠️ Railway Ready:
- All configuration files included
- Environment variable setup
- Persistent data storage
- Automatic restart configuration

📊 Deployment Stats:
- $(find . -name "*.py" | wc -l) Python files
- $(du -sh . | cut -f1) total size
- Version: $NEW_VERSION"

# Add all files and commit
git add .
git commit -m "$COMMIT_MSG"

# Setup remote and push
git remote add origin "https://$GH_TOKEN@github.com/${REPO_URL#https://github.com/}"
git branch -M main

echo "📤 Pushing to GitHub..."
if git push -f origin main; then
    echo "✅ Successfully pushed to GitHub!"
    echo "🌐 Repository: $REPO_URL"
    echo "📋 Version: $NEW_VERSION"
    echo ""
    echo "🚀 Ready for Railway deployment!"
    echo "   1. Connect this GitHub repo to Railway"
    echo "   2. Set BOT_TOKEN environment variable"
    echo "   3. Optionally set Google Sheets variables"
    echo "   4. Deploy automatically starts"
else
    echo "❌ Failed to push to GitHub"
    exit 1
fi

# Cleanup
cd ..
rm -rf "$DEPLOY_DIR"
echo "🧹 Cleaned up deployment directory"

echo "✅ Deployment complete! Bot ready for Railway."
