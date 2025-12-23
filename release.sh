#!/bin/bash
set -e

# Check for release type argument
if [ -z "$1" ]; then
    echo "Usage: ./release.sh [patch|minor|major]"
    exit 1
fi

# Fetch latest tags to get the current version
git fetch --tags

# Get the latest tag
LATEST_TAG=$(git describe --tags `git rev-list --tags --max-count=1`)

# If no tags, default to v0.0.0
if [ -z "$LATEST_TAG" ]; then
    LATEST_TAG="v0.0.0"
fi

echo "Latest tag: $LATEST_TAG"

# Remove 'v' prefix
VERSION=${LATEST_TAG#v}

# Split version into components
IFS='.' read -ra VERSION_BITS <<< "$VERSION"
MAJOR=${VERSION_BITS[0]}
MINOR=${VERSION_BITS[1]}
PATCH=${VERSION_BITS[2]}

# Increment version based on argument
case "$1" in
    patch)
        PATCH=$((PATCH + 1))
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    *)
        echo "Invalid release type. Use 'patch', 'minor', or 'major'."
        exit 1
        ;;
esac

NEW_VERSION="v$MAJOR.$MINOR.$PATCH"
echo "Bumping version to $NEW_VERSION"

# Create a new git tag
echo "Creating git tag: $NEW_VERSION"
git tag -a "$NEW_VERSION" -m "Release $NEW_VERSION"

# Push the tag to origin
echo "Pushing tag to origin..."
git push origin "$NEW_VERSION"

echo "Release process initiated with tag $NEW_VERSION. Check GitHub Actions for build status here: https://github.com/TheUndefined/omnis-android/actions?query=workflow%3A%22Build+Android+APK%22"
