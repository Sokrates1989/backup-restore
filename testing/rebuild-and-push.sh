#!/bin/bash
# Quick script to rebuild and push the Docker image with the migration fix

set -e  # Exit on error

echo "🔨 Rebuilding Docker Image with Migration Fix"
echo "=============================================="
echo ""

# Get the current version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "📦 Current version: $VERSION"
echo ""

# Ask for confirmation
read -p "Build and push sokrates1989/python-api-template:$VERSION? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

# Build the image
echo "🔨 Building Docker image..."
docker build -t sokrates1989/python-api-template:$VERSION .

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build successful"
echo ""

# Tag as latest
echo "🏷️  Tagging as latest..."
docker tag sokrates1989/python-api-template:$VERSION sokrates1989/python-api-template:latest

# Push to Docker Hub
echo "📤 Pushing to Docker Hub..."
docker push sokrates1989/python-api-template:$VERSION
docker push sokrates1989/python-api-template:latest

if [ $? -ne 0 ]; then
    echo "❌ Push failed"
    exit 1
fi

echo ""
echo "✅ Successfully built and pushed:"
echo "   - sokrates1989/python-api-template:$VERSION"
echo "   - sokrates1989/python-api-template:latest"
echo ""
echo "📝 Next Steps:"
echo "   1. Update your swarm deployment:"
echo "      docker service update --image sokrates1989/python-api-template:$VERSION python-api-template_api"
echo ""
echo "   2. Or use the quick-start script:"
echo "      ./quick-start.sh"
echo "      Choose option 4 (Update API image)"
echo ""
echo "   3. Verify migrations ran successfully:"
echo "      docker service logs python-api-template_api --tail 50"
echo ""
