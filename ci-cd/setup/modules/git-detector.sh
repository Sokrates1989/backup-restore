#!/bin/bash
# Git detector module
# Detects git repository information and builds platform URLs

# Detect git remote and extract repository information
# Returns: platform|owner|repo|remote_url
detect_git_info() {
    local remote_url
    
    # Get remote URL (try origin first, then any remote)
    remote_url=$(git remote get-url origin 2>/dev/null || git remote get-url $(git remote | head -n1) 2>/dev/null)
    
    if [ -z "$remote_url" ]; then
        echo "none||||"
        return 1
    fi
    
    local platform=""
    local owner=""
    local repo=""
    
    # Parse GitHub URLs
    if [[ "$remote_url" =~ github\.com[:/]([^/]+)/([^/\.]+) ]]; then
        platform="github"
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
    # Parse GitLab URLs
    elif [[ "$remote_url" =~ gitlab\.com[:/]([^/]+)/([^/\.]+) ]]; then
        platform="gitlab"
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
    else
        platform="unknown"
    fi
    
    echo "$platform|$owner|$repo|$remote_url"
}

# Build GitHub secrets URL
# Usage: build_github_secrets_url "owner" "repo"
build_github_secrets_url() {
    local owner="$1"
    local repo="$2"
    echo "https://github.com/$owner/$repo/settings/secrets/actions"
}

# Build GitLab CI/CD variables URL
# Usage: build_gitlab_variables_url "owner" "repo"
build_gitlab_variables_url() {
    local owner="$1"
    local repo="$2"
    echo "https://gitlab.com/$owner/$repo/-/settings/ci_cd"
}

# Display git repository information
# Usage: display_git_info "platform" "owner" "repo" "remote_url"
display_git_info() {
    local platform="$1"
    local owner="$2"
    local repo="$3"
    local remote_url="$4"
    
    echo "📦 Repository Information" >&2
    echo "------------------------" >&2
    
    if [ "$platform" = "none" ]; then
        echo "❌ No git remote detected" >&2
        echo "" >&2
        echo "This project doesn't appear to be connected to a remote repository." >&2
        echo "You'll need to manually configure repository secrets/variables." >&2
        return 1
    elif [ "$platform" = "unknown" ]; then
        echo "⚠️  Unknown git platform" >&2
        echo "Remote URL: $remote_url" >&2
        echo "" >&2
        echo "Detected a git remote, but it's not GitHub or GitLab." >&2
        echo "You'll need to manually configure repository secrets/variables." >&2
        return 1
    else
        echo "Platform: $platform" >&2
        echo "Owner: $owner" >&2
        echo "Repository: $repo" >&2
        echo "Remote URL: $remote_url" >&2
        echo "" >&2
        return 0
    fi
}

# Get list of remote branches
# Returns: newline-separated list of branch names
get_remote_branches() {
    # Fetch latest from remote
    git fetch --quiet 2>/dev/null || true
    
    # Get remote branches, strip 'origin/' prefix, exclude HEAD
    git branch -r | grep -v '\->' | sed 's/origin\///' | sed 's/^[[:space:]]*//' | sort -u
}

# Check if git repository exists
check_git_repository() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error_message "Not a git repository"
        echo "" >&2
        echo "This directory is not a git repository." >&2
        echo "Please initialize git and add a remote:" >&2
        echo "  git init" >&2
        echo "  git remote add origin <your-repo-url>" >&2
        return 1
    fi
    return 0
}
