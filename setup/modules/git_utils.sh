#!/bin/bash
# -----------------------------------------------------------------------------
# Script: git_utils.sh
# Description: Git utilities for detecting and handling repository corruption
# Usage: Source this file in other scripts
# -----------------------------------------------------------------------------

# Function to check if output indicates git corruption
check_git_corruption_in_output() {
    local output="$1"
    if echo "$output" | grep -qE "(far too short to be a packfile|invalid object|Error building trees|broken link|missing blob|missing tree|fatal: unable to read tree|unable to read)"; then
        return 0  # Corruption detected
    fi
    return 1  # No corruption
}

# Function to detect git repository corruption
detect_git_corruption() {
    # Check pack files for obvious corruption (too small)
    local pack_dir=".git/objects/pack"
    if [ -d "$pack_dir" ]; then
        for pack in "$pack_dir"/*.pack; do
            if [ -f "$pack" ]; then
                local size=$(wc -c < "$pack" 2>/dev/null | tr -d ' ')
                if [ -n "$size" ] && [ "$size" -lt 1000 ]; then
                    return 0  # Corruption detected
                fi
            fi
        done
    fi
    
    # Check submodule pack files
    if [ -d ".git/modules" ]; then
        for submod_pack_dir in .git/modules/*/objects/pack; do
            if [ -d "$submod_pack_dir" ]; then
                for pack in "$submod_pack_dir"/*.pack; do
                    if [ -f "$pack" ]; then
                        local size=$(wc -c < "$pack" 2>/dev/null | tr -d ' ')
                        if [ -n "$size" ] && [ "$size" -lt 1000 ]; then
                            return 0  # Corruption detected
                        fi
                    fi
                done
            fi
        done
    fi
    
    # Try to run git fsck
    local fsck_output
    fsck_output=$(git fsck --quick 2>&1)
    if check_git_corruption_in_output "$fsck_output"; then
        return 0  # Corruption detected
    fi
    
    return 1  # No corruption
}

# Function to show git corruption error message and repair instructions
show_git_corruption_message() {
    echo ""
    echo "⚠️  Git repository corruption detected!"
    echo ""
    echo "This error typically occurs when pack files in your .git directory are corrupted."
    echo ""
    echo "To repair this repository, you can run:"
    echo "  dev-tools --repair"
    echo "  or: dev-tools -f"
    echo ""
    echo "Or manually:"
    echo "  1. Backup your uncommitted changes"
    echo "  2. Remove corrupted pack files from .git/objects/pack/"
    echo "  3. Run: git fetch --all"
    echo "  4. Run: git gc --prune=now"
    echo ""
}

# Function to offer to run dev-tools repair
offer_devtools_repair() {
    echo ""
    read -r -p "🔧 Would you like to attempt automatic repair using dev-tools? [Y/n]: " repair_confirm
    if [[ ! "$repair_confirm" =~ ^[Nn]$ ]]; then
        if command -v dev-tools >/dev/null 2>&1; then
            echo ""
            echo "Running: dev-tools --repair"
            dev-tools --repair
            return $?
        else
            echo ""
            echo "❌ dev-tools command not found in PATH."
            show_git_corruption_message
            return 1
        fi
    fi
    return 1
}

# Function to check for git corruption and offer repair
# Usage: check_and_offer_git_repair
# Returns: 0 if healthy or repaired, 1 if still corrupted
check_and_offer_git_repair() {
    if detect_git_corruption; then
        show_git_corruption_message
        offer_devtools_repair
        
        # Check again after repair attempt
        if detect_git_corruption; then
            echo ""
            echo "❌ Repository still appears to be corrupted."
            echo "   Please try manual repair or clone fresh."
            return 1
        else
            echo ""
            echo "✅ Repository appears to be healthy now."
            return 0
        fi
    fi
    return 0
}

# Function to handle command output for git corruption
# Usage: handle_git_error_in_output "$output" "$operation_name"
handle_git_error_in_output() {
    local output="$1"
    local operation_name="${2:-Operation}"
    
    if check_git_corruption_in_output "$output"; then
        echo ""
        echo "❌ $operation_name encountered git repository corruption."
        show_git_corruption_message
        offer_devtools_repair
        return 1
    fi
    return 0
}
