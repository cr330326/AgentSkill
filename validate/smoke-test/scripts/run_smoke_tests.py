from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run generated smoke tests with pytest.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--service-url")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--pytest-arg", action="append", default=[])
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def has_pytest() -> bool:
    return importlib.util.find_spec("pytest") is not None


def build_base_result(skill_workspace: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "generated",
        "executed": False,
        "workspace": str(skill_workspace),
        "test_file": manifest.get("test_file"),
        "manifest_file": manifest.get("manifest_file"),
        "result_file": str(skill_workspace / "smoke_result.json"),
        "selected_operations": manifest.get("selected_operations", []),
        "skipped_operations": manifest.get("skipped_operations", []),
        "warnings": list(manifest.get("warnings", [])),
        "next_steps": [],
    }


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    skill_workspace = workspace / "smoke-test"
    manifest_file = skill_workspace / "smoke_manifest.json"
    result_file = skill_workspace / "smoke_result.json"
    log_file = skill_workspace / "pytest.log"

    if not manifest_file.exists():
        raise SystemExit(json.dumps({"status": "failed", "error": f"manifest_file not found: {manifest_file}"}, ensure_ascii=False))

    manifest = load_manifest(manifest_file)
    result = build_base_result(skill_workspace, manifest)

    if not args.execute:
        result["warnings"].append("Execution not requested; returning generated artifacts only")
        result["next_steps"] = ["Re-run with --execute after confirming the target service URL"]
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.service_url:
        result["warnings"].append("service_url missing; execution skipped")
        result["next_steps"] = ["Provide --service-url to execute the generated smoke tests"]
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not has_pytest():
        result["warnings"].append("pytest is not installed in the current environment")
        result["next_steps"] = ["Install pytest in the active environment, then retry with --execute"]
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    test_file = Path(str(manifest["test_file"]))
    env = os.environ.copy()
    env["SERVICE_URL"] = args.service_url

    command = [sys.executable, "-m", "pytest", str(test_file), "-v", *args.pytest_arg]
    completed = subprocess.run(command, capture_output=True, text=True, env=env)
    log_file.write_text((completed.stdout or "") + "\n" + (completed.stderr or ""), encoding="utf-8")

    result.update(
        {
            "status": "executed" if completed.returncode == 0 else "failed",
            "executed": True,
            "service_url": args.service_url,
            "pytest_exit_code": completed.returncode,
            "stdout_tail": (completed.stdout or "")[-4000:],
            "stderr_tail": (completed.stderr or "")[-4000:],
            "log_file": str(log_file),
            "next_steps": [
                "Review skipped operations in the manifest to decide whether auth-aware smoke coverage is needed",
                "If failures are expected on protected endpoints, add explicit auth fixtures instead of loosening the filter",
            ],
        }
    )

    result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if completed.returncode == 0 else completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())