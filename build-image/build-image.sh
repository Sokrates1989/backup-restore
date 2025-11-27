#!/bin/bash
#
# build-image.sh
#
# Docker-based script to build and optionally push production Docker images
# This script runs inside a Docker container to ensure consistency across platforms

set -e

echo "🏗️  Production Image Builder"
echo "============================"
echo ""

# Check if running in Docker
if [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
    echo "⚠️  This script should be run via docker-compose"
    echo "Please use: docker compose -f build-image/docker-compose.build.yml up"
    exit 1
fi

# Load environment variables
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env from config/.env.template first"
    exit 1
fi

# Source .env file (filter out comments and empty lines)
set -a
while IFS= read -r line; do
    # Skip empty lines
    [[ -z "$line" ]] && continue
    # Skip comment lines (lines starting with #, possibly with leading whitespace)
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    # Skip lines that don't contain =
    [[ ! "$line" =~ = ]] && continue
    
    # Extract key and value
    key=$(echo "$line" | cut -d= -f1 | xargs)
    value=$(echo "$line" | cut -d= -f2- | sed 's/#.*//' | xargs)
    
    # Skip if key is empty or contains spaces
    [[ -z "$key" || "$key" =~ [[:space:]] ]] && continue
    
    # Export the variable
    export "$key=$value"
done < .env
set +a

# Check if we're in an interactive terminal
if [ -t 0 ]; then
    INTERACTIVE=true
else
    INTERACTIVE=false
fi

# Check and prompt for IMAGE_NAME if needed
if [ -z "$IMAGE_NAME" ]; then
    if [ "$INTERACTIVE" = true ]; then
        echo "Current IMAGE_NAME: not set"
        echo ""
        read -p "Enter Docker image name (e.g., sokrates1989/python-api-template, ghcr.io/user/api): " NEW_IMAGE_NAME
        
        if [ -z "$NEW_IMAGE_NAME" ]; then
            echo "❌ IMAGE_NAME cannot be empty"
            exit 1
        fi
        
        IMAGE_NAME="$NEW_IMAGE_NAME"
        
        # Update .env file
        if grep -q "^IMAGE_NAME=" .env; then
            sed -i "s|^IMAGE_NAME=.*|IMAGE_NAME=$IMAGE_NAME|" .env
        else
            echo "IMAGE_NAME=$IMAGE_NAME" >> .env
        fi
        
        echo "✅ Updated IMAGE_NAME to $IMAGE_NAME in .env"
        echo ""
    else
        echo "❌ IMAGE_NAME not set in .env and not in interactive mode"
        echo "Please add IMAGE_NAME to your .env file (e.g., IMAGE_NAME=sokrates1989/python-api-template)"
        exit 1
    fi
else
    if [ "$INTERACTIVE" = true ]; then
        echo "Current IMAGE_NAME: $IMAGE_NAME"
        echo ""
        read -p "Enter new IMAGE_NAME or press Enter to keep [$IMAGE_NAME]: " NEW_IMAGE_NAME
        
        if [ -n "$NEW_IMAGE_NAME" ]; then
            IMAGE_NAME="$NEW_IMAGE_NAME"
            
            # Update .env file
            if grep -q "^IMAGE_NAME=" .env; then
                sed -i "s|^IMAGE_NAME=.*|IMAGE_NAME=$IMAGE_NAME|" .env
            else
                echo "IMAGE_NAME=$IMAGE_NAME" >> .env
            fi
            
            echo "✅ Updated IMAGE_NAME to $IMAGE_NAME in .env"
            echo ""
        else
            echo "✅ Keeping current IMAGE_NAME: $IMAGE_NAME"
            echo ""
        fi
    else
        echo "ℹ️  Using IMAGE_NAME from .env: $IMAGE_NAME"
    fi
fi

# Prompt for image version if not set or if UPDATE_VERSION is true
if [ -z "$IMAGE_VERSION" ]; then
    if [ "$INTERACTIVE" = true ]; then
        echo "Current IMAGE_VERSION: not set"
        echo ""
        read -p "Enter new IMAGE_VERSION (e.g., 0.0.1, 1.0.0, v1.2.3): " NEW_VERSION
        
        if [ -z "$NEW_VERSION" ]; then
            echo "❌ IMAGE_VERSION cannot be empty"
            exit 1
        fi
        
        IMAGE_VERSION="$NEW_VERSION"
    else
        echo "❌ IMAGE_VERSION not set in .env and not in interactive mode"
        exit 1
    fi
elif [ "$UPDATE_VERSION" = "true" ]; then
    if [ "$INTERACTIVE" = true ]; then
        echo "Current IMAGE_VERSION: $IMAGE_VERSION"
        echo ""
        read -p "Enter new IMAGE_VERSION or press Enter to keep [$IMAGE_VERSION]: " NEW_VERSION
        
        if [ -n "$NEW_VERSION" ]; then
            IMAGE_VERSION="$NEW_VERSION"
        else
            echo "✅ Keeping current version: $IMAGE_VERSION"
        fi
    else
        echo "ℹ️  Using IMAGE_VERSION from .env: $IMAGE_VERSION"
    fi
fi

# Update .env file with version if changed
if [ -n "$NEW_VERSION" ]; then
    if grep -q "^IMAGE_VERSION=" .env; then
        sed -i "s/^IMAGE_VERSION=.*/IMAGE_VERSION=$IMAGE_VERSION/" .env
    else
        echo "IMAGE_VERSION=$IMAGE_VERSION" >> .env
    fi
    echo "✅ Updated IMAGE_VERSION to $IMAGE_VERSION in .env"
    echo ""
fi

# Get Python version from .env (default to 3.13)
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"

echo "📋 Build Configuration:"
echo "   Image Name:     $IMAGE_NAME"
echo "   Image Version:  $IMAGE_VERSION"
echo "   Python Version: $PYTHON_VERSION"
echo ""

# Ask if user wants to push to registry (only in interactive mode)
if [ "$INTERACTIVE" = true ]; then
    read -p "Push image to Docker registry after build? (y/N): " PUSH_IMAGE
else
    # In non-interactive mode, check for PUSH_IMAGE env var (default to no)
    PUSH_IMAGE="${PUSH_IMAGE:-n}"
fi

# Build the image
echo "🔨 Building Docker image..."
echo "   Tag: $IMAGE_NAME:$IMAGE_VERSION"
echo ""

docker buildx build \
    --build-arg PYTHON_VERSION="${PYTHON_VERSION}" \
    --build-arg IMAGE_TAG="$IMAGE_VERSION" \
    -t "$IMAGE_NAME:$IMAGE_VERSION" \
    -t "$IMAGE_NAME:latest" \
    -f Dockerfile \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Image built successfully!"
    echo "   $IMAGE_NAME:$IMAGE_VERSION"
    echo "   $IMAGE_NAME:latest"
else
    echo ""
    echo "❌ Image build failed!"
    exit 1
fi

# Push to registry if requested
if [[ "$PUSH_IMAGE" =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Pushing image to registry..."
    
    # Check if logged in to Docker registry
    if ! docker info | grep -q "Username"; then
        echo "⚠️  Not logged in to Docker registry"
        read -p "Docker registry username: " DOCKER_USERNAME
        read -sp "Docker registry password: " DOCKER_PASSWORD
        echo ""
        
        echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
        
        if [ $? -ne 0 ]; then
            echo "❌ Docker login failed!"
            exit 1
        fi
    fi
    
    docker push "$IMAGE_NAME:$IMAGE_VERSION"
    docker push "$IMAGE_NAME:latest"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Image pushed successfully!"
        echo "   $IMAGE_NAME:$IMAGE_VERSION"
        echo "   $IMAGE_NAME:latest"
    else
        echo ""
        echo "❌ Image push failed!"
        exit 1
    fi
else
    echo ""
    echo "ℹ️  Image not pushed to registry"
    echo "   To push later, run:"
    echo "   docker push $IMAGE_NAME:$IMAGE_VERSION"
    echo "   docker push $IMAGE_NAME:latest"
fi

echo ""
echo "🎉 Build process complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Test the image locally:"
echo "      docker run -p 8000:8000 --env-file .env $IMAGE_NAME:$IMAGE_VERSION"
echo ""
echo "   2. Use in production docker-compose.yml:"
echo "      services:"
echo "        app:"
echo "          image: $IMAGE_NAME:$IMAGE_VERSION"
echo "          ports:"
echo "            - \"8000:8000\""
echo ""
