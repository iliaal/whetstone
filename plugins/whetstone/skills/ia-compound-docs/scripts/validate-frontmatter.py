#!/usr/bin/env python3
"""Validate solution-document frontmatter using Python 3 and PyYAML."""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("FAIL: PyYAML is required; install with python3 -m pip install PyYAML")


class FrontmatterLoader(yaml.SafeLoader):
    pass


FrontmatterLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in values if tag != "tag:yaml.org,2002:timestamp"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def unique_mapping(loader, node):
    keys = set()
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            continue
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in keys:
            raise ValueError("Frontmatter keys must be unique strings")
        keys.add(key)
    loader.flatten_mapping(node)
    return loader.construct_mapping(node)


FrontmatterLoader.add_constructor("tag:yaml.org,2002:map", unique_mapping)

ENUMS = {
    "problem_type": "build_error test_failure runtime_error performance_issue database_issue security_issue ui_bug integration_issue logic_error developer_experience workflow_issue best_practice documentation_gap",
    "component": "model controller view service_object background_job database frontend_component api_endpoint authentication payments development_workflow testing_framework documentation tooling",
    "root_cause": "missing_association missing_include missing_index wrong_api scope_issue thread_violation async_timing memory_leak config_error logic_error test_isolation missing_validation missing_permission missing_workflow_step inadequate_documentation missing_tooling incomplete_setup",
    "resolution_type": "code_fix migration config_change test_fix dependency_update environment_setup workflow_improvement documentation_update tooling_addition seed_data_update",
    "severity": "critical high medium low",
}


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: validate-frontmatter.sh <file.md>")
        lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != "---":
            raise ValueError("No YAML frontmatter found (expected opening ---)")
        try:
            end = lines.index("---", 1)
        except ValueError:
            raise ValueError("Missing closing --- delimiter") from None
        data = yaml.load("\n".join(lines[1:end]), Loader=FrontmatterLoader)
        if not isinstance(data, dict):
            raise ValueError("Frontmatter must be a YAML mapping")
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
        print(f"FAIL: {error}")
        return 1

    errors = []
    warnings = []
    for field in ("module", "date", *ENUMS):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field}: MISSING or not a non-empty string (required)")
        elif field in ENUMS and value not in ENUMS[field].split():
            errors.append(f"{field}: '{value}' not in allowed values [{ENUMS[field]}]")
    if isinstance(data.get("date"), str) and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", data["date"]):
        errors.append("date: does not match YYYY-MM-DD format")
    symptoms = data.get("symptoms")
    if not isinstance(symptoms, list) or not 1 <= len(symptoms) <= 5:
        errors.append("symptoms: required array with 1-5 items (empty array is invalid)")
    elif any(not isinstance(item, str) or not item.strip() for item in symptoms):
        errors.append("symptoms: each item must be a non-empty string")
    if "framework_version" in data and (not isinstance(data["framework_version"], str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", data["framework_version"])):
        warnings.append("framework_version: does not match X.Y.Z format")
    print(f"Validating: {sys.argv[1]}")
    if warnings:
        print("WARNINGS:\n" + "\n".join(f"  - {warning}" for warning in warnings))
    if errors:
        print("ERRORS:\n" + "\n".join(f"  - {error}" for error in errors))
        return 1
    print("PASS: All fields valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
