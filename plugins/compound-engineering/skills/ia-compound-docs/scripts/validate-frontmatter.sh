#!/usr/bin/env bash
# validate-frontmatter.sh — Validate solution doc YAML frontmatter against schema
# Usage: bash validate-frontmatter.sh <file.md>
#
# Checks required fields, enum values, date format, and array constraints.
# Returns 0 on success, 1 on validation failure.

set -euo pipefail

FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "Usage: bash validate-frontmatter.sh <file.md>"
    echo "Error: File not found or not specified"
    exit 1
fi

# Extract frontmatter (between --- delimiters)
frontmatter=$(awk '/^---$/{if(n++)exit;next}n' "$FILE")
if [ -z "$frontmatter" ]; then
    echo "FAIL: No YAML frontmatter found (expected --- delimiters)"
    exit 1
fi

errors=()
warnings=()

# --- Helper: get field value (returns empty string if missing) ---
field_value() {
    local field="$1"
    echo "$frontmatter" | grep -E "^${field}:" | sed "s/^${field}:[[:space:]]*//" | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/" || true
}

# --- Helper: check enum ---
check_enum() {
    local field="$1"
    shift
    local allowed=("$@")
    local val
    val=$(field_value "$field")
    if [ -z "$val" ]; then
        errors+=("${field}: MISSING (required)")
        return
    fi
    local found=0
    for a in "${allowed[@]}"; do
        if [ "$val" = "$a" ]; then
            found=1
            break
        fi
    done
    if [ $found -eq 0 ]; then
        errors+=("${field}: '${val}' not in allowed values [${allowed[*]}]")
    fi
}

# --- Required string fields ---
for field in module; do
    val=$(field_value "$field")
    if [ -z "$val" ]; then
        errors+=("${field}: MISSING (required)")
    fi
done

# --- Date format ---
date_val=$(field_value "date")
if [ -z "$date_val" ]; then
    errors+=("date: MISSING (required)")
elif ! echo "$date_val" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
    errors+=("date: '${date_val}' does not match YYYY-MM-DD format")
fi

# --- Enum fields ---
check_enum "problem_type" \
    build_error test_failure runtime_error performance_issue \
    database_issue security_issue ui_bug integration_issue \
    logic_error developer_experience workflow_issue best_practice documentation_gap

check_enum "component" \
    model controller view service_object background_job database \
    frontend_component api_endpoint authentication payments \
    development_workflow testing_framework documentation tooling

check_enum "root_cause" \
    missing_association missing_include missing_index wrong_api \
    scope_issue thread_violation async_timing memory_leak \
    config_error logic_error test_isolation missing_validation \
    missing_permission missing_workflow_step inadequate_documentation \
    missing_tooling incomplete_setup

check_enum "resolution_type" \
    code_fix migration config_change test_fix dependency_update \
    environment_setup workflow_improvement documentation_update \
    tooling_addition seed_data_update

check_enum "severity" \
    critical high medium low

# --- Symptoms array (check at least 1 item) ---
symptom_count=$(echo "$frontmatter" | grep -cE '^  - ' || true)
if [ "$symptom_count" -eq 0 ]; then
    # Check for inline array format: symptoms: ["a", "b"]
    symptoms_line=$(echo "$frontmatter" | grep -E '^symptoms:' || true)
    if [ -z "$symptoms_line" ]; then
        errors+=("symptoms: MISSING (required, need 1-5 items)")
    elif echo "$symptoms_line" | grep -qE '\[.*\]'; then
        # Inline array — count commas + 1
        item_count=$(echo "$symptoms_line" | tr ',' '\n' | wc -l)
        if [ "$item_count" -gt 5 ]; then
            errors+=("symptoms: has ${item_count} items (max 5)")
        fi
    else
        errors+=("symptoms: no array items found (need 1-5)")
    fi
elif [ "$symptom_count" -gt 5 ]; then
    errors+=("symptoms: has ${symptom_count} items (max 5)")
fi

# --- Optional: framework_version format ---
fw_ver=$(field_value "framework_version")
if [ -n "$fw_ver" ] && ! echo "$fw_ver" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    warnings+=("framework_version: '${fw_ver}' does not match X.Y.Z format")
fi

# --- Report ---
echo "Validating: ${FILE}"
echo ""

if [ ${#errors[@]} -eq 0 ] && [ ${#warnings[@]} -eq 0 ]; then
    echo "PASS: All fields valid"
    exit 0
fi

if [ ${#errors[@]} -gt 0 ]; then
    echo "ERRORS (${#errors[@]}):"
    for e in "${errors[@]}"; do
        echo "  - ${e}"
    done
fi

if [ ${#warnings[@]} -gt 0 ]; then
    echo ""
    echo "WARNINGS (${#warnings[@]}):"
    for w in "${warnings[@]}"; do
        echo "  - ${w}"
    done
fi

if [ ${#errors[@]} -gt 0 ]; then
    exit 1
fi
exit 0
