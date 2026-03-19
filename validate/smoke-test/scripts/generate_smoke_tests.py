from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SAFE_METHODS = {"get", "head", "options"}
HEALTH_HINTS = ("health", "ready", "live", "status", "ping")
KEYWORD_PATTERN = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]{2,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate smoke tests from OpenAPI/Swagger.")
    parser.add_argument("--swagger-path", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--spec-path")
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


def extract_keywords(spec_path: Path | None) -> list[str]:
    if spec_path is None or not spec_path.exists():
        return []
    text = spec_path.read_text(encoding="utf-8")
    seen: set[str] = set()
    ordered: list[str] = []
    for token in KEYWORD_PATTERN.findall(text.lower()):
        if len(token) < 3:
            continue
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered[:30]


def normalize_summary(operation: dict[str, Any]) -> str:
    summary = operation.get("summary") or operation.get("operationId") or ""
    return str(summary)


def requires_auth(operation: dict[str, Any], root_security: Any) -> bool:
    if operation.get("security"):
        return True
    return bool(root_security)


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


def build_operation_records(document: dict[str, Any], keywords: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise RuntimeError("OpenAPI document does not contain a valid 'paths' object")

    root_security = document.get("security")
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            lowered_method = str(method).lower()
            if lowered_method not in {"get", "head", "options", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue

            summary = normalize_summary(operation)
            has_path_params = "{" in str(path) and "}" in str(path)
            auth_required = requires_auth(operation, root_security)
            record = {
                "method": lowered_method.upper(),
                "path": str(path),
                "summary": summary,
                "score": score_operation(lowered_method, str(path), summary, has_path_params, auth_required, keywords),
            }

            if lowered_method not in SAFE_METHODS:
                skipped.append({**record, "reason": "write_operation"})
                continue
            if has_path_params:
                skipped.append({**record, "reason": "path_params"})
                continue
            if auth_required:
                skipped.append({**record, "reason": "auth_required"})
                continue

            selected.append(record)

    selected.sort(key=lambda item: (-item["score"], item["path"], item["method"]))
    skipped.sort(key=lambda item: (-item["score"], item["path"], item["method"]))
    return selected, skipped


def escape_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_tests(base_url_placeholder: str, operations: list[dict[str, Any]], timeout_seconds: int, warnings: list[str]) -> str:
    lines: list[str] = [
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
        "def request_status(base_url, method, path):",
        "    request = urllib.request.Request(base_url + path, method=method)",
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
        test_name = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{operation['method'].lower()}_{operation['path'].strip('/') or 'root'}").strip("_")
        lines.extend(
            [
                "",
                f"def test_smoke_{index}_{test_name}(base_url):",
                f"    status_code = request_status(base_url, {escape_string(operation['method'])}, {escape_string(operation['path'])})",
                "    assert 200 <= status_code < 400, f'unexpected status code: {status_code}'",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    swagger_path = Path(args.swagger_path).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    spec_path = Path(args.spec_path).expanduser().resolve() if args.spec_path else None

    if not swagger_path.exists():
        raise SystemExit(json.dumps({"status": "failed", "error": f"swagger_path not found: {swagger_path}"}, ensure_ascii=False))

    skill_workspace = workspace / "smoke-test"
    tests_dir = skill_workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if spec_path and not spec_path.exists():
        warnings.append(f"spec_path not found: {spec_path}")
        spec_path = None

    document = load_openapi_document(swagger_path)
    keywords = extract_keywords(spec_path)
    selected, skipped = build_operation_records(document, keywords)
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
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())