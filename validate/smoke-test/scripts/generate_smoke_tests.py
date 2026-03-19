from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


SAFE_METHODS = {"get", "head", "options"}
SUPPORTED_METHODS = {"get", "head", "options", "post", "put", "patch", "delete"}
HEALTH_HINTS = ("health", "ready", "live", "status", "ping")
KEYWORD_PATTERN = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]{2,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate smoke tests from OpenAPI/Swagger.")
    parser.add_argument("--swagger-path", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--spec-path")
    parser.add_argument("--seed-path")
    parser.add_argument("--max-operations", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    return parser.parse_args()


def load_openapi_document(path: Path) -> dict[str, Any]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("YAML file detected but PyYAML is not installed") from exc
        loaded = yaml.safe_load(raw_text)
        if not isinstance(loaded, dict):
            raise RuntimeError("OpenAPI document must be a JSON/YAML object")
        return loaded


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except ImportError:
        pass
    except Exception:
        pass

    try:
        completed = subprocess.run(
            ["strings", "-a", "-n", "4", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout
    except Exception:
        return ""


def read_spec_text(spec_path: Path | None) -> tuple[str, list[str]]:
    if spec_path is None or not spec_path.exists():
        return "", []

    if spec_path.suffix.lower() == ".pdf":
        text = extract_pdf_text(spec_path)
        if not text.strip():
            return "", [f"Unable to extract usable text from PDF spec: {spec_path}"]
        return text, []

    try:
        return spec_path.read_text(encoding="utf-8"), []
    except UnicodeDecodeError:
        return "", [f"Unsupported spec encoding for keyword extraction: {spec_path}"]


def extract_keywords(spec_path: Path | None) -> tuple[list[str], list[str]]:
    text, warnings = read_spec_text(spec_path)
    if not text:
        return [], warnings
    seen: set[str] = set()
    ordered: list[str] = []
    for token in KEYWORD_PATTERN.findall(text.lower()):
        if len(token) < 3:
            continue
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered[:30], warnings


def normalize_summary(operation: dict[str, Any]) -> str:
    summary = operation.get("summary") or operation.get("operationId") or ""
    return str(summary)


def requires_auth(operation: dict[str, Any], root_security: Any) -> bool:
    if operation.get("security"):
        return True
    return bool(root_security)


def get_schema(parameter: dict[str, Any]) -> dict[str, Any]:
    schema = parameter.get("schema")
    return schema if isinstance(schema, dict) else {}


def extract_example_from_parameter(parameter: dict[str, Any] | None) -> Any:
    if not parameter:
        return None
    if "example" in parameter:
        return parameter["example"]
    schema = get_schema(parameter)
    for key in ("example", "default", "const"):
        if key in schema:
            return schema[key]
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]
    return None


def get_parameter_example(parameter: dict[str, Any], seed_parameter: dict[str, Any] | None = None) -> Any:
    return extract_example_from_parameter(parameter) or extract_example_from_parameter(seed_parameter)


def normalize_parameter_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def merge_parameters(path_item: dict[str, Any], operation: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for source in (path_item.get("parameters", []), operation.get("parameters", [])):
        if not isinstance(source, list):
            continue
        for parameter in source:
            if not isinstance(parameter, dict):
                continue
            name = str(parameter.get("name", ""))
            location = str(parameter.get("in", ""))
            if not name or not location:
                continue
            merged[(name, location)] = parameter
    return list(merged.values())


def find_matching_seed_operation(seed_document: dict[str, Any] | None, method: str, target_path: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not seed_document:
        return None
    seed_paths = seed_document.get("paths")
    if not isinstance(seed_paths, dict):
        return None

    exact_match = seed_paths.get(target_path)
    if isinstance(exact_match, dict):
        seed_operation = exact_match.get(method)
        if isinstance(seed_operation, dict):
            return exact_match, seed_operation

    for seed_path, seed_path_item in seed_paths.items():
        if not isinstance(seed_path_item, dict):
            continue
        if not (str(seed_path).endswith(target_path) or target_path.endswith(str(seed_path))):
            continue
        seed_operation = seed_path_item.get(method)
        if isinstance(seed_operation, dict):
            return seed_path_item, seed_operation

    return None


def build_seed_parameter_lookup(seed_document: dict[str, Any] | None, method: str, target_path: str) -> dict[tuple[str, str], dict[str, Any]]:
    matched = find_matching_seed_operation(seed_document, method, target_path)
    if matched is None:
        return {}
    seed_path_item, seed_operation = matched
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for parameter in merge_parameters(seed_path_item, seed_operation):
        if not isinstance(parameter, dict):
            continue
        lookup[(str(parameter.get("name", "")), str(parameter.get("in", "")))] = parameter
    return lookup


def build_request_target(path: str, query_values: list[tuple[str, str]]) -> str:
    if not query_values:
        return path
    return f"{path}?{urlencode(query_values, doseq=True)}"


def score_operation(method: str, path: str, summary: str, has_path_params: bool, auth_required: bool, keywords: list[str]) -> int:
    score = 0
    lowered_path = path.lower()
    lowered_summary = summary.lower()
    if any(hint in lowered_path for hint in HEALTH_HINTS):
        score += 100
    if method in SAFE_METHODS:
        score += 40
    if not has_path_params:
        score += 20
    if not auth_required:
        score += 20
    if any(keyword in lowered_path or keyword in lowered_summary for keyword in keywords):
        score += 15
    if method == "get":
        score += 10
    return score


def make_operation_record(path: str, method: str, summary: str, has_path_params: bool, auth_required: bool, keywords: list[str]) -> dict[str, Any]:
    return {
        "method": method.upper(),
        "path": path,
        "summary": summary,
        "score": score_operation(method, path, summary, has_path_params, auth_required, keywords),
    }


def get_skip_reason(method: str, has_path_params: bool, auth_required: bool, unsupported_required_parameters: list[dict[str, Any]]) -> str | None:
    if method not in SAFE_METHODS:
        return "write_operation"
    if has_path_params:
        return "path_params"
    if auth_required:
        return "auth_required"
    if unsupported_required_parameters:
        return "unsupported_required_parameters"
    return None


def build_required_parameter_values(required_parameters: list[dict[str, Any]], seed_lookup: dict[tuple[str, str], dict[str, Any]]) -> tuple[dict[str, str], bool]:
    values: dict[str, str] = {}
    for parameter in required_parameters:
        key = (str(parameter.get("name", "")), str(parameter.get("in", "")))
        example = get_parameter_example(parameter, seed_lookup.get(key))
        if example is None:
            return {}, True
        values[str(parameter["name"])] = ",".join(normalize_parameter_value(example))
    return values, False


def build_seed_only_required_headers(seed_lookup: dict[tuple[str, str], dict[str, Any]], known_parameters: list[dict[str, Any]]) -> tuple[dict[str, str], bool]:
    known_header_names = {
        str(parameter.get("name", ""))
        for parameter in known_parameters
        if str(parameter.get("in", "")) == "header"
    }
    seed_required_headers = [
        parameter
        for (name, location), parameter in seed_lookup.items()
        if location == "header" and parameter.get("required") and name not in known_header_names
    ]
    return build_required_parameter_values(seed_required_headers, seed_lookup)


def evaluate_operation(path: str, method: str, operation: dict[str, Any], path_item: dict[str, Any], root_security: Any, keywords: list[str], seed_document: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    summary = normalize_summary(operation)
    has_path_params = "{" in path and "}" in path
    auth_required = requires_auth(operation, root_security)
    parameters = merge_parameters(path_item, operation)
    seed_lookup = build_seed_parameter_lookup(seed_document, method, path)
    unsupported_required_parameters = [
        parameter
        for parameter in parameters
        if parameter.get("required") and str(parameter.get("in", "")) not in {"query", "header"}
    ]
    required_query_parameters = [
        parameter
        for parameter in parameters
        if parameter.get("required") and str(parameter.get("in", "")) == "query"
    ]
    required_header_parameters = [
        parameter
        for parameter in parameters
        if parameter.get("required") and str(parameter.get("in", "")) == "header"
    ]
    record = make_operation_record(path, method, summary, has_path_params, auth_required, keywords)

    skip_reason = get_skip_reason(method, has_path_params, auth_required, unsupported_required_parameters)
    if skip_reason:
        return None, {**record, "reason": skip_reason}

    query_values, missing_query_examples = build_required_parameter_values(required_query_parameters, seed_lookup)
    if missing_query_examples:
        return None, {**record, "reason": "required_query_params_without_examples"}

    header_values, missing_header_examples = build_required_parameter_values(required_header_parameters, seed_lookup)
    if missing_header_examples:
        return None, {**record, "reason": "required_header_params_without_examples"}

    seed_only_header_values, missing_seed_only_header_examples = build_seed_only_required_headers(seed_lookup, parameters)
    if missing_seed_only_header_examples:
        return None, {**record, "reason": "required_header_params_without_examples"}

    header_values.update(seed_only_header_values)

    query_pairs = [(name, value) for name, value in query_values.items()]
    return {**record, "request_target": build_request_target(path, query_pairs), "headers": header_values}, None


def iter_supported_operations(paths: dict[str, Any]) -> list[tuple[str, dict[str, Any], str, dict[str, Any]]]:
    operations: list[tuple[str, dict[str, Any], str, dict[str, Any]]] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            lowered_method = str(method).lower()
            if lowered_method not in SUPPORTED_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            operations.append((str(path), path_item, lowered_method, operation))
    return operations


def build_operation_records(document: dict[str, Any], keywords: list[str], seed_document: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise RuntimeError("OpenAPI document does not contain a valid 'paths' object")

    root_security = document.get("security")
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for path, path_item, lowered_method, operation in iter_supported_operations(paths):
        selected_record, skipped_record = evaluate_operation(path, lowered_method, operation, path_item, root_security, keywords, seed_document)
        if selected_record is not None:
            selected.append(selected_record)
        if skipped_record is not None:
            skipped.append(skipped_record)

    selected.sort(key=lambda item: (-item["score"], item["path"], item["method"]))
    skipped.sort(key=lambda item: (-item["score"], item["path"], item["method"]))
    return selected, skipped


def escape_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_tests(base_url_placeholder: str, operations: list[dict[str, Any]], timeout_seconds: int, warnings: list[str]) -> str:
    lines: list[str] = [
        "import json",
        "import os",
        "import urllib.error",
        "import urllib.request",
        "",
        "import pytest",
        "",
        f"DEFAULT_BASE_URL = {escape_string(base_url_placeholder)}",
        f"TIMEOUT_SECONDS = {timeout_seconds}",
        "",
        "",
        "@pytest.fixture(scope='session')",
        "def base_url():",
        "    url = os.environ.get('SERVICE_URL', DEFAULT_BASE_URL).strip()",
        "    if not url:",
        "        pytest.skip('SERVICE_URL is not configured')",
        "    return url.rstrip('/')",
        "",
        "",
        "def request_status(base_url, method, path, headers):",
        "    request = urllib.request.Request(base_url + path, method=method, headers=headers)",
        "    try:",
        "        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:",
        "            return response.getcode()",
        "    except urllib.error.HTTPError as exc:",
        "        return exc.code",
        "",
    ]

    for warning in warnings:
        lines.append(f"pytestmark = pytest.mark.filterwarnings({escape_string('ignore:' + warning)})")
        break

    if not operations:
        lines.extend(
            [
                "",
                "def test_no_safe_operations_generated():",
                "    pytest.skip('No safe OpenAPI operations were eligible for smoke execution')",
            ]
        )
        return "\n".join(lines) + "\n"

    for index, operation in enumerate(operations, start=1):
        test_name = re.sub(r"\W+", "_", f"{operation['method'].lower()}_{operation['path'].strip('/') or 'root'}").strip("_")
        lines.extend(
            [
                "",
                f"def test_smoke_{index}_{test_name}(base_url):",
                f"    headers = json.loads({escape_string(json.dumps(operation.get('headers', {}), ensure_ascii=False))})",
                f"    status_code = request_status(base_url, {escape_string(operation['method'])}, {escape_string(operation.get('request_target', operation['path']))}, headers)",
                "    assert 200 <= status_code < 400, f'unexpected status code: {status_code}'",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    swagger_path = Path(args.swagger_path).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    spec_path = Path(args.spec_path).expanduser().resolve() if args.spec_path else None
    seed_path = Path(args.seed_path).expanduser().resolve() if args.seed_path else None

    if not swagger_path.exists():
        raise SystemExit(json.dumps({"status": "failed", "error": f"swagger_path not found: {swagger_path}"}, ensure_ascii=False))

    skill_workspace = workspace / "smoke-test"
    tests_dir = skill_workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if spec_path and not spec_path.exists():
        warnings.append(f"spec_path not found: {spec_path}")
        spec_path = None
    if seed_path and not seed_path.exists():
        warnings.append(f"seed_path not found: {seed_path}")
        seed_path = None

    document = load_openapi_document(swagger_path)
    seed_document = load_openapi_document(seed_path) if seed_path else None
    keywords, keyword_warnings = extract_keywords(spec_path)
    warnings.extend(keyword_warnings)
    selected, skipped = build_operation_records(document, keywords, seed_document)
    selected = selected[: max(args.max_operations, 1)]

    if not keywords:
        warnings.append("SPEC not provided or no keywords extracted; route selection used OpenAPI only")
    if not selected:
        warnings.append("No safe operations selected for execution")

    test_file = tests_dir / "test_smoke_generated.py"
    manifest_file = skill_workspace / "smoke_manifest.json"
    generated_test = render_tests("", selected, args.timeout_seconds, warnings)
    test_file.write_text(generated_test, encoding="utf-8")

    manifest = {
        "status": "generated",
        "executed": False,
        "workspace": str(skill_workspace),
        "test_file": str(test_file),
        "manifest_file": str(manifest_file),
        "result_file": None,
        "selected_operations": selected,
        "skipped_operations": skipped,
        "warnings": warnings,
        "next_steps": [
            "Review the generated test file before execution",
            "Provide SERVICE_URL and explicit confirmation before running against a real service",
        ],
    }
    if seed_path:
        manifest["seed_file"] = str(seed_path)
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())