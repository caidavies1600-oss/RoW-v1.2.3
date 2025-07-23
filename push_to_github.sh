#!/bin/bash

set -e  # Stop if any command fails

REPO_URL="https://github.com/caidavies1600-oss/RoW-v1.2.3.git"
GIT_USER="caidavies1600-oss"
EMAIL="ci@replitpush.com"  # You can change this

# File that stores version info
VERSION_FILE="version.txt"

# Get current version
if [ ! -f "$VERSION_FILE" ]; then
    echo "v1.0.0" > "$VERSION_FILE"
fi

CURRENT_VERSION=$(cat "$VERSION_FILE")
IFS='.' read -r MAJOR MINOR PATCH <<< "${CURRENT_VERSION#v}"

# Bump patch version
PATCH=$((PATCH + 1))
NEW_VERSION="v$MAJOR.$MINOR.$PATCH"
echo "$NEW_VERSION" > "$VERSION_FILE"

echo "🔧 Bumping version: $CURRENT_VERSION → $NEW_VERSION"

# Git setup
git config --global user.email "$EMAIL"
git config --global user.name "$GIT_USER"

# Initialize and stage everything
git init
git add .
git commit -m "Automated push: $NEW_VERSION - $(date -u)"

# Add GitHub remote using token from secrets
git remote remove origin 2>/dev/null || true
git remote add origin https://"$GH_TOKEN"@github.com/caidavies1600-oss/RoW-v1.2.3.git

# Create versioned branch and push
git checkout -b "$NEW_VERSION" || git checkout "$NEW_VERSION"
git push origin "$NEW_VERSION" --force

echo "✅ Code pushed to branch: $NEW_VERSION"
