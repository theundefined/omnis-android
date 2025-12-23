#!/bin/bash
set -e

# Check for release type argument
if [ -z "$1" ]; then
    echo "Usage: ./release.sh [patch|minor|major]"
    exit 1
fi

# Check if git-cliff is installed
if ! command -v git-cliff &> /dev/null
then
    echo "git-cliff could not be found. Please install it:"
    echo "https://github.com/orhun/git-cliff#installation"
    exit 1
fi

git fetch --tags

# Get the latest tag safely
LATEST_TAG=$(git tag -l --sort=-v:refname "v*.*.*" | head -n 1)

if [ -z "$LATEST_TAG" ]; then
    echo "No existing tags found. Starting with v0.1.0."
    NEW_VERSION="v0.1.0"
else
    echo "Latest tag: $LATEST_TAG"
    VERSION=${LATEST_TAG#v}
    IFS='.' read -ra VERSION_BITS <<< "$VERSION"
    MAJOR=${VERSION_BITS[0]}
    MINOR=${VERSION_BITS[1]}
    PATCH=${VERSION_BITS[2]}

    case "$1" in
        patch) PATCH=$((PATCH + 1));;
        minor) MINOR=$((MINOR + 1)); PATCH=0;;
        major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0;;
        *) echo "Invalid release type."; exit 1;;
    esac
    NEW_VERSION="v$MAJOR.$MINOR.$PATCH"
fi

echo "Bumping version to $NEW_VERSION"

# Generate changelog for the new version
git-cliff --tag "$NEW_VERSION" --prepend ./CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore(release): update changelog for $NEW_VERSION"

# Create and push the new git tag
git tag -a "$NEW_VERSION" -m "Release $NEW_VERSION"
echo "Pushing changes and tag to origin..."
git push && git push origin "$NEW_VERSION"

echo "Release process initiated with tag $NEW_VERSION. Check GitHub Actions for build status here: https://github.com/TheUndefined/omnis-android/actions?query=workflow%3A%22Build+Android+APK%22"
