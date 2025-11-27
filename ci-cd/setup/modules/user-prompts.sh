#!/bin/bash
# User prompts module
# Reusable prompt functions for user input

# Prompt for yes/no with default
# Usage: prompt_yes_no "Question?" "Y"
prompt_yes_no() {
    local question="$1"
    local default="${2:-N}"
    local response
    
    if [ "$default" = "Y" ] || [ "$default" = "y" ]; then
        read -p "$question (Y/n): " response
        response="${response:-Y}"
    else
        read -p "$question (y/N): " response
        response="${response:-N}"
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

# Prompt for text input with default
# Usage: result=$(prompt_text "Enter value" "default")
prompt_text() {
    local prompt_msg="$1"
    local default="$2"
    local response
    
    if [ -n "$default" ]; then
        read -p "$prompt_msg [$default]: " response
        echo "${response:-$default}"
    else
        read -p "$prompt_msg: " response
        echo "$response"
    fi
}

# Prompt for selection from numbered list
# Usage: result=$(prompt_selection "Choose option" "Option 1" "Option 2" "Option 3")
prompt_selection() {
    local prompt_msg="$1"
    shift
    local options=("$@")
    local choice
    
    echo "$prompt_msg" >&2
    for i in "${!options[@]}"; do
        echo "$((i+1))) ${options[$i]}" >&2
    done
    echo "" >&2
    
    while true; do
        read -p "Your choice (1-${#options[@]}): " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            echo "$((choice-1))"
            return 0
        else
            echo "Invalid choice. Please enter a number between 1 and ${#options[@]}." >&2
        fi
    done
}

# Prompt for multiple selections from numbered list
# Usage: result=$(prompt_multi_selection "Choose options" "Option 1" "Option 2" "Option 3")
# Returns: space-separated indices (e.g., "0 2" for options 1 and 3)
prompt_multi_selection() {
    local prompt_msg="$1"
    shift
    local options=("$@")
    local input
    local selections=()
    
    echo "$prompt_msg" >&2
    for i in "${!options[@]}"; do
        echo "$((i+1))) ${options[$i]}" >&2
    done
    echo "" >&2
    echo "Enter numbers separated by spaces (e.g., '1 3' for options 1 and 3)" >&2
    echo "Or press Enter to select all" >&2
    echo "" >&2
    
    read -p "Your choices: " input
    
    # If empty, select all
    if [ -z "$input" ]; then
        for i in "${!options[@]}"; do
            selections+=("$i")
        done
    else
        # Parse input
        for num in $input; do
            if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#options[@]}" ]; then
                selections+=("$((num-1))")
            else
                echo "Warning: Ignoring invalid choice: $num" >&2
            fi
        done
    fi
    
    # Return space-separated indices
    echo "${selections[@]}"
}

# Wait for user to press Enter
# Usage: wait_for_enter "Press Enter to continue..."
wait_for_enter() {
    local msg="${1:-Press Enter to continue...}"
    read -p "$msg"
}

# Display a section header
# Usage: section_header "Step 1: Configuration"
section_header() {
    local title="$1"
    local line=$(printf '=%.0s' {1..60})
    
    echo "" >&2
    echo "📋 $title" >&2
    echo "$line" >&2
    echo "" >&2
}

# Display a success message
# Usage: success_message "Configuration complete"
success_message() {
    echo "✅ $1" >&2
}

# Display a warning message
# Usage: warning_message "This will overwrite existing files"
warning_message() {
    echo "⚠️  $1" >&2
}

# Display an error message
# Usage: error_message "Failed to connect"
error_message() {
    echo "❌ $1" >&2
}

# Display an info message
# Usage: info_message "Loading configuration..."
info_message() {
    echo "ℹ️  $1" >&2
}
