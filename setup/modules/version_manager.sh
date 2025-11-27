#!/bin/bash
#
# version_manager.sh
#
# Module for managing Docker image versions and semantic versioning

bump_semver() {
    local version="$1"
    local level="$2"

    if [ -z "$version" ]; then
        version="0.0.0"
    fi

    local prefix=""
    if [[ "$version" =~ ^[vV] ]]; then
        prefix="${version:0:1}"
        version="${version:1}"
    fi

    local IFS='.'
    read -r major minor patch <<< "$version"
    major=${major:-0}
    minor=${minor:-0}
    patch=${patch:-0}

    if ! [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ && "$patch" =~ ^[0-9]+$ ]]; then
        echo ""
        return
    fi

    case "$level" in
        patch) patch=$((patch + 1)) ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        major) major=$((major + 1)); minor=0; patch=0 ;;
        *) echo ""; return ;;
    esac

    echo "${prefix}${major}.${minor}.${patch}"
}

update_image_version_in_file() {
    local file="$1"
    local new_version="$2"

    if [ ! -f "$file" ]; then
        echo "⚠️  $file nicht gefunden – übersprungen."
        return
    fi

    local tmp_file
    tmp_file=$(mktemp) || {
        echo "❌ Konnte temporäre Datei nicht erstellen."
        return
    }

    local replaced=0
    while IFS= read -r line || [ -n "$line" ]; do
        if [ $replaced -eq 0 ] && [[ $line == IMAGE_VERSION=* ]]; then
            echo "IMAGE_VERSION=$new_version" >> "$tmp_file"
            replaced=1
        else
            echo "$line" >> "$tmp_file"
        fi
    done < "$file"

    if [ $replaced -eq 0 ]; then
        echo "IMAGE_VERSION=$new_version" >> "$tmp_file"
    fi

    mv "$tmp_file" "$file"
    echo "✅  $file -> IMAGE_VERSION=$new_version"
}

get_remote_image_state() {
    local image_ref="$1"

    if [ -z "$image_ref" ]; then
        echo "unknown|"
        return
    }

    if ! command -v docker >/dev/null 2>&1; then
        echo "skipped|Docker CLI nicht verfügbar"
        return
    fi

    local output
    if output=$(docker manifest inspect "$image_ref" 2>&1); then
        echo "present|"
        return
    fi

    if echo "$output" | grep -Eqi 'not found|no such manifest'; then
        echo "missing|"
    elif echo "$output" | grep -Eqi 'denied|unauthorized'; then
        echo "unauthorized|Anmeldung erforderlich"
    else
        local detail
        detail=$(echo "$output" | head -n1)
        echo "error|$detail"
    fi
}

get_local_image_state() {
    local image_ref="$1"

    if [ -z "$image_ref" ]; then
        echo "unknown|"
        return
    fi

    if ! command -v docker >/dev/null 2>&1; then
        echo "skipped|Docker CLI nicht verfügbar"
        return
    fi

    if docker image inspect "$image_ref" >/dev/null 2>&1; then
        echo "present|"
    else
        echo "missing|"
    fi
}

describe_state_label() {
    local prefix="$1"
    local state="$2"
    local detail="$3"

    case "$state" in
        present)
            echo "$prefix: verfügbar"
            ;;
        missing)
            echo "$prefix: fehlt"
            ;;
        unauthorized)
            echo "$prefix: Zugriff verweigert"
            ;;
        error)
            if [ -n "$detail" ]; then
                echo "$prefix: Fehler - $detail"
            else
                echo "$prefix: Fehler"
            fi
            ;;
        skipped)
            if [ -n "$detail" ]; then
                echo "$prefix: nicht geprüft ($detail)"
            else
                echo "$prefix: nicht geprüft"
            fi
            ;;
        unknown)
            echo "$prefix: unbekannt"
            ;;
        *)
            echo "$prefix: unbekannt"
            ;;
    esac
}

build_version_annotation() {
    local image_name="$1"
    local version="$2"

    if [ -z "$image_name" ]; then
        echo " (Remote: nicht geprüft - IMAGE_NAME fehlt)"
        return
    fi

    if [ -z "$version" ]; then
        echo " (Remote: nicht geprüft - Version fehlt)"
        return
    fi

    local image_ref="${image_name}:${version}"

    local remote_state
    local remote_detail
    IFS='|' read -r remote_state remote_detail <<< "$(get_remote_image_state "$image_ref")"
    local annotation=" ($(describe_state_label "Remote" "$remote_state" "$remote_detail")"

    local local_state
    local local_detail
    IFS='|' read -r local_state local_detail <<< "$(get_local_image_state "$image_ref")"

    if [ "$local_state" != "$remote_state" ]; then
        annotation="$annotation, $(describe_state_label "Lokal" "$local_state" "$local_detail")"
    fi

    annotation="$annotation)"
    echo "$annotation"
}

remote_image_status() {
    local image_ref="$1"
    local context="$2"

    if [ -z "$image_ref" ]; then
        return
    fi

    local state detail
    IFS='|' read -r state detail <<< "$(get_remote_image_state "$image_ref")"

    case "$state" in
        present)
            echo "✅ $context: $image_ref ist auf der Registry vorhanden."
            ;;
        missing)
            echo "ℹ️ $context: $image_ref wurde auf der Registry nicht gefunden."
            ;;
        unauthorized)
            echo "⚠️  $context: Zugriff verweigert für $image_ref. Bitte bei der Registry anmelden."
            ;;
        skipped)
            if [ -n "$detail" ]; then
                echo "⚠️  $context: Remote-Check übersprungen ($detail)."
            else
                echo "⚠️  $context: Remote-Check übersprungen."
            fi
            ;;
        error)
            if [ -n "$detail" ]; then
                echo "⚠️  $context: Fehler beim Prüfen von $image_ref: $detail"
            else
                echo "⚠️  $context: Fehler beim Prüfen von $image_ref."
            fi
            ;;
        *)
            echo "⚠️  $context: Unbekannter Zustand für $image_ref."
            ;;
    esac
}

update_image_version() {
    local env_file=".env"
    local ci_env_file=".ci.env"

    local current_env_version
    current_env_version=$(grep '^IMAGE_VERSION=' "$env_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')

    local current_ci_version
    current_ci_version=$(grep '^IMAGE_VERSION=' "$ci_env_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')

    local base_version="$current_env_version"
    if [ -z "$base_version" ]; then
        base_version="$current_ci_version"
    fi
    if [ -z "$base_version" ]; then
        base_version="0.1.0"
    fi

    local image_name
    image_name=$(grep '^IMAGE_NAME=' "$env_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d ' "')

    local display_env=${current_env_version:-"<nicht gesetzt>"}
    local display_ci=${current_ci_version:-"<nicht gesetzt>"}

    echo ""
    local env_annotation
    env_annotation=$(build_version_annotation "$image_name" "$current_env_version")

    local ci_annotation
    ci_annotation=$(build_version_annotation "$image_name" "$current_ci_version")

    echo "📸 Aktuelle IMAGE_VERSION Werte:"
    echo "  • .env    : $display_env$env_annotation"
    echo "  • .ci.env : $display_ci$ci_annotation"
    echo ""

    if [ -n "$image_name" ] && [ -n "$base_version" ]; then
        remote_image_status "${image_name}:${base_version}" "Aktuelle Version auf Registry"
        echo ""
    elif [ -z "$image_name" ]; then
        echo "⚠️  IMAGE_NAME ist nicht gesetzt – Remote-Check übersprungen."
        echo ""
    fi

    echo "Wie möchtest du die Version aktualisieren?"
    echo "  1) Bugfix/Patch (+0.0.1)"
    echo "  2) Feature/Minor (+0.1.0)"
    echo "  3) Breaking/Major (+1.0.0)"
    echo "  oder gib direkt eine neue Version ein (z. B. 1.2.3)"

    local new_version=""
    while true; do
        read -r -p "Deine Wahl (1-3 oder SemVer): " version_choice
        version_choice=${version_choice//[[:space:]]/}

        case "$version_choice" in
            1)
                new_version=$(bump_semver "$base_version" "patch")
                ;;
            2)
                new_version=$(bump_semver "$base_version" "minor")
                ;;
            3)
                new_version=$(bump_semver "$base_version" "major")
                ;;
            "")
                echo "❌ Bitte eine Auswahl treffen oder Version angeben."
                continue
                ;;
            *)
                if [[ "$version_choice" =~ ^[vV]?[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                    new_version="$version_choice"
                else
                    echo "❌ Ungültige Eingabe. Bitte 1-3 wählen oder SemVer (z. B. 1.2.3) angeben."
                    continue
                fi
                ;;
        esac

        if [ -n "$new_version" ]; then
            break
        fi
    done

    if [ -z "$new_version" ]; then
        echo "❌ Konnte neue Version nicht bestimmen. Bitte erneut versuchen."
        return
    fi

    if [ -n "$image_name" ]; then
        echo ""
        remote_image_status "${image_name}:${new_version}" "Gewählte Version auf Registry"
    fi

    echo ""
    update_image_version_in_file "$env_file" "$new_version"
    update_image_version_in_file "$ci_env_file" "$new_version"
    echo ""
    echo "🎯 IMAGE_VERSION wurde auf $new_version gesetzt."
}
