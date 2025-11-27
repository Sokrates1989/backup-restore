#!/bin/bash
# Template builder module
# Builds CI/CD configuration files from templates

# Build .ci.env file with image and python versions
# Usage: build_ci_env "0.1.4" "3.13" "/path/to/project"
build_ci_env() {
    local image_version="$1"
    local python_version="$2"
    local project_root="$3"
    
    echo "⚙️  Building .ci.env..." >&2
    
    cat > "$project_root/.ci.env" << EOF
IMAGE_VERSION=$image_version
PYTHON_VERSION=$python_version
EOF
    
    success_message ".ci.env created with IMAGE_VERSION=$image_version"
}

# Build GitHub Actions workflow from template files
# Usage: build_github_workflow "linux-swarm" "main develop" "/path/to/project" "deploy_config"
build_github_workflow() {
    local deployment_target="$1"
    local branches="$2"
    local project_root="$3"
    local deploy_config="$4"

    section_header "STEP 4: Building CI/CD Configuration Files"

    echo "⚙️  Creating GitHub Actions workflow..." >&2

    local workflow_dir="$project_root/.github/workflows"
    mkdir -p "$workflow_dir"

    local template_path="$SCRIPT_DIR/../templates/github/build-deploy-linux.yml"
    if [ ! -f "$template_path" ]; then
        error_message "GitHub workflow template not found: $template_path"
        exit 1
    fi

    local branches_yaml=$(format_branches_github "$branches")

    local workflow_branch
    IFS=' ' read -r workflow_branch _ <<< "$branches"
    if [ -z "$workflow_branch" ]; then
        workflow_branch="main"
    fi

    local sanitized_branch=$(echo "$workflow_branch" | sed 's/[^A-Za-z0-9._-]/-/g')
    local workflow_file="$workflow_dir/${sanitized_branch}.yml"

    # Copy template and replace placeholder
    sed "s|__BRANCHES__|$branches_yaml|" "$template_path" > "$workflow_file"

    if [ "$deployment_target" = "build-only" ]; then
        # Remove deploy job block between markers
        local workflow_file_tmp="${workflow_file}.tmp"
        sed '/^# BEGIN_DEPLOY_SECTION/,/^# END_DEPLOY_SECTION/d' "$workflow_file" > "$workflow_file_tmp" && mv "$workflow_file_tmp" "$workflow_file"
    else
        # Remove marker comments only
        sed -i '/^# BEGIN_DEPLOY_SECTION/d;/^# END_DEPLOY_SECTION/d' "$workflow_file"
    fi

    success_message "GitHub Actions workflow created: .github/workflows/${sanitized_branch}.yml (branch: $workflow_branch)"
}

# Build GitLab CI configuration
# Usage: build_gitlab_ci "linux-swarm" "main develop" "sokrates1989/api" "/path/to/project" "deploy_config"
build_gitlab_ci() {
    local deployment_target="$1"
    local branches="$2"
    local image_name="$3"
    local project_root="$4"
    local deploy_config="$5"
    
    section_header "STEP 4: Building CI/CD Configuration Files"
    
    echo "⚙️  Creating GitLab CI configuration..." >&2
    
    # Format branches for GitLab
    local branches_yaml=$(format_branches_gitlab "$branches")
    
    # Create .gitlab-ci.yml
    cat > "$project_root/.gitlab-ci.yml" << EOF
# GitLab CI/CD Pipeline
# Placeholder for GitLab implementation
# TODO: Implement GitLab CI/CD template

stages:
  - build
  - deploy

variables:
  IMAGE_NAME: $image_name

build:
  stage: build
  only:$branches_yaml
  script:
    - echo "Build stage - TODO"

deploy:
  stage: deploy
  only:$branches_yaml
  script:
    - echo "Deploy stage - TODO"
EOF
    
    success_message "GitLab CI configuration created: .gitlab-ci.yml"
    warning_message "GitLab CI template needs full implementation"
}

# Update .env file IMAGE_VERSION
# Usage: update_env_image_version "/path/to/.env" "0.1.5"
update_env_image_version() {
    local env_file="$1"
    local new_version="$2"
    
    if [ -f "$env_file" ]; then
        if grep -q "^IMAGE_VERSION=" "$env_file"; then
            sed -i "s/^IMAGE_VERSION=.*/IMAGE_VERSION=$new_version/" "$env_file"
        else
            echo "IMAGE_VERSION=$new_version" >> "$env_file"
        fi
    fi
}
