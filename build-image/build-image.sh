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
        read -p "Enter Docker image name (e.g., sokrates1989/backup-restore, ghcr.io/user/api): " NEW_IMAGE_NAME
        
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
        echo "Please add IMAGE_NAME to your .env file (e.g., IMAGE_NAME=sokrates1989/backup-restore)"
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

# Determine target platform for buildx (default to linux/amd64 for Swarm nodes)
TARGET_PLATFORM="${TARGET_PLATFORM:-linux/amd64}"

# Which image(s) to build
# - all: build and push API + Web
# - api: build and push only the API image
# - web: build and push only the Web (nginx) image
BUILD_TARGET="${BUILD_TARGET:-all}"

BUILD_API=false
BUILD_WEB=false
case "$BUILD_TARGET" in
    all)
        BUILD_API=true
        BUILD_WEB=true
        ;;
    api)
        BUILD_API=true
        BUILD_WEB=false
        ;;
    web)
        BUILD_API=false
        BUILD_WEB=true
        ;;
    *)
        echo "❌ Invalid BUILD_TARGET: $BUILD_TARGET"
        echo "   Valid values: all, api, web"
        exit 1
        ;;
esac

WEB_IMAGE_NAME="${IMAGE_NAME}-web"

echo "📋 Build Configuration:"
echo "   Image Name:     $IMAGE_NAME"
echo "   Image Version:  $IMAGE_VERSION"
echo "   Web Image Name: $WEB_IMAGE_NAME"
echo "   Python Version: $PYTHON_VERSION"
echo "   Target platform: $TARGET_PLATFORM"
echo "   Build Target:   $BUILD_TARGET"
echo ""

API_BUILD_EXIT_CODE=0
WEB_BUILD_EXIT_CODE=0

if [ "$BUILD_API" = true ]; then
    echo "🔨 Building API Docker image..."
    echo "   Tag: $IMAGE_NAME:$IMAGE_VERSION"
    echo ""

    docker buildx build \
        --platform "$TARGET_PLATFORM" \
        --build-arg PYTHON_VERSION="${PYTHON_VERSION}" \
        --build-arg IMAGE_TAG="$IMAGE_VERSION" \
        --load \
        -t "$IMAGE_NAME:$IMAGE_VERSION" \
        -t "$IMAGE_NAME:latest" \
        -f Dockerfile \
        . || API_BUILD_EXIT_CODE=$?

    if [ $API_BUILD_EXIT_CODE -eq 0 ]; then
        echo ""
        echo "✅ API image built successfully!"
        echo "   $IMAGE_NAME:$IMAGE_VERSION"
        echo "   $IMAGE_NAME:latest"
    else
        echo ""
        echo "❌ API image build failed!"
        exit 1
    fi
fi

if [ "$BUILD_WEB" = true ]; then
    echo ""
    echo "🌐 Building Web UI Docker image (nginx)..."
    echo "   Tag: $WEB_IMAGE_NAME:$IMAGE_VERSION"
    echo ""

    docker buildx build \
        --platform "$TARGET_PLATFORM" \
        --build-arg IMAGE_TAG="$IMAGE_VERSION" \
        --load \
        -t "$WEB_IMAGE_NAME:$IMAGE_VERSION" \
        -t "$WEB_IMAGE_NAME:latest" \
        -f Dockerfile_web \
        . || WEB_BUILD_EXIT_CODE=$?

    if [ $WEB_BUILD_EXIT_CODE -eq 0 ]; then
        echo ""
        echo "✅ Web image built successfully!"
        echo "   $WEB_IMAGE_NAME:$IMAGE_VERSION"
        echo "   $WEB_IMAGE_NAME:latest"
    else
        echo ""
        echo "❌ Web image build failed!"
        exit 1
    fi
fi


# Registry helper functions for push with login retry
infer_registry() {
  local image="$1"
  local first="${image%%/*}"
  if [[ "$image" == */* && ( "$first" == *.* || "$first" == *:* ) ]]; then
    printf '%s' "$first"
    return 0
  fi
  return 1
}

registry_login_flow() {
  local registry="$1"
  local target=""
  if [ -n "$registry" ]; then
    target=" $registry"
  fi

  echo "Choose a login method:"
  echo "1) docker login${target}"
  echo "2) docker logout${target} && docker login${target} (switch account)"
  echo "3) Login with username + token (uses --password-stdin)"
  read -r -p "Your choice (1-3) [1]: " login_method
  login_method="${login_method:-1}"

  case "$login_method" in
    1)
      if [ -n "$registry" ]; then
        docker login "$registry"
      else
        docker login
      fi
      ;;
    2)
      if [ -n "$registry" ]; then
        docker logout "$registry" >/dev/null 2>&1 || true
        docker login "$registry"
      else
        docker logout >/dev/null 2>&1 || true
        docker login
      fi
      ;;
    3)
      read -r -p "Username: " login_user
      read -r -s -p "Token (will not echo): " login_token
      echo ""
      if [ -n "$registry" ]; then
        printf '%s' "$login_token" | docker login "$registry" -u "$login_user" --password-stdin
      else
        printf '%s' "$login_token" | docker login -u "$login_user" --password-stdin
      fi
      ;;
    *)
      echo "Invalid choice"
      return 1
      ;;
  esac
}

push_with_login_retry() {
  local image_ref="$1"
  local registry="$2"

  local push_output
  local push_status
  set +e
  push_output="$(docker push "$image_ref" 2>&1)"
  push_status=$?
  set -e

  if [ $push_status -eq 0 ]; then
    echo "$push_output"
    return 0
  fi

  echo "$push_output"
  echo "❌ Failed to push image: $image_ref"

  if echo "$push_output" | grep -qiE "insufficient_scope|unauthorized|authentication required|no basic auth credentials|requested access to the resource is denied"; then
    echo ""
    if [ -n "$registry" ]; then
      echo "🔐 Docker registry login required for: $registry"
    else
      echo "🔐 Docker registry login required"
    fi
    echo ""
    registry_login_flow "$registry" || return 1

    echo ""
    echo "🔁 Retrying push: $image_ref"

    local retry_output
    local retry_status
    set +e
    retry_output="$(docker push "$image_ref" 2>&1)"
    retry_status=$?
    set -e

    echo "$retry_output"
    if [ $retry_status -eq 0 ]; then
      return 0
    fi

    if echo "$retry_output" | grep -qiE "insufficient_scope|unauthorized|authentication required|no basic auth credentials|requested access to the resource is denied"; then
      echo ""
      echo "⚠ Push still failing after login."
      echo "   Ensure the token/user has permission to push to this registry."
    fi
    return 1
  fi

  echo "   Please run 'docker login' for your registry and re-run the script."
  return 1
}

echo ""
echo "🚀 Pushing image to registry..."
registry="$(infer_registry "$IMAGE_NAME" || true)"

if [ "$BUILD_API" = true ]; then
  push_with_login_retry "$IMAGE_NAME:$IMAGE_VERSION" "$registry" || exit 1
  push_with_login_retry "$IMAGE_NAME:latest" "$registry" || exit 1
fi

if [ "$BUILD_WEB" = true ]; then
  web_registry="$(infer_registry "$WEB_IMAGE_NAME" || true)"
  push_with_login_retry "$WEB_IMAGE_NAME:$IMAGE_VERSION" "$web_registry" || exit 1
  push_with_login_retry "$WEB_IMAGE_NAME:latest" "$web_registry" || exit 1
fi

echo ""
echo "✅ Image pushed successfully!"
if [ "$BUILD_API" = true ]; then
  echo "   $IMAGE_NAME:$IMAGE_VERSION"
  echo "   $IMAGE_NAME:latest"
fi
if [ "$BUILD_WEB" = true ]; then
  echo "   $WEB_IMAGE_NAME:$IMAGE_VERSION"
  echo "   $WEB_IMAGE_NAME:latest"
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
