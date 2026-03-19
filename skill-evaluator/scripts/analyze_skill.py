#!/usr/bin/env python3

"""Baseline analyzer for Skill quality.

Usage:
	python scripts/analyze_skill.py <path-to-skill-dir-or-skill-md>
	python scripts/analyze_skill.py <path> --json

This script performs deterministic checks only. It is designed to give a
repeatable baseline for the Skill Evaluator and should be paired with
qualitative review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


GENERIC_NAMES = {
	"file",
	"misc",
	"notes",
	"note",
	"temp",
	"tmp",
	"doc",
	"docs",
	"ref",
}

RESOURCE_DIRS = ["reference", "references", "templates", "assets", "scripts", "examples", "data"]
OUTPUT_RESOURCE_PREFIXES = ("templates/", "assets/")
RESOURCE_REF_RE = re.compile(
	r"`((?:reference|references|templates|assets|scripts|examples|data)/[^`]+)`"
)
ROUTE_LOAD_RE = re.compile(r"(?:->|→)\s*Load\s*`([^`]+)`")
TABLE_LINE_RE = re.compile(r"^\|.*\|\s*$")


def resolve_skill_paths(raw_path: str) -> tuple[Path, Path]:
	path = Path(raw_path).expanduser().resolve()
	if not path.exists():
		raise FileNotFoundError(f"Path does not exist: {path}")

	if path.is_dir():
		skill_md = path / "SKILL.md"
		if not skill_md.exists():
			raise FileNotFoundError(f"No SKILL.md found in directory: {path}")
		return path, skill_md

	if path.name != "SKILL.md":
		raise ValueError("Input path must be a Skill directory or a SKILL.md file")
	return path.parent, path


def read_text(path: Path) -> str:
	return path.read_text(encoding="utf-8")


def has_frontmatter(lines: list[str]) -> bool:
	return bool(lines) and lines[0].strip() == "---"


def find_frontmatter_end(lines: list[str]) -> int | None:
	for index, line in enumerate(lines[1:], start=1):
		if line.strip() == "---":
			return index
	return None


def is_list_item(line: str) -> bool:
	return bool(re.match(r"^\s*-\s+", line))


def append_frontmatter_list_item(frontmatter: dict[str, Any], key: str, line: str) -> None:
	frontmatter.setdefault(key, [])
	if not isinstance(frontmatter[key], list):
		frontmatter[key] = [frontmatter[key]]
	frontmatter[key].append(line.strip()[2:].strip())


def parse_frontmatter_assignment(line: str) -> tuple[str | None, Any]:
	if ":" not in line:
		return None, None
	key, value = line.split(":", 1)
	parsed_key = key.strip()
	parsed_value = value.strip()
	if not parsed_value:
		return parsed_key, []
	return parsed_key, parsed_value.strip('"').strip("'")


def parse_frontmatter_lines(frontmatter_lines: list[str]) -> dict[str, Any]:
	frontmatter: dict[str, Any] = {}
	current_key: str | None = None

	for line in frontmatter_lines:
		if not line.strip():
			continue
		if current_key and is_list_item(line):
			append_frontmatter_list_item(frontmatter, current_key, line)
			continue
		parsed_key, parsed_value = parse_frontmatter_assignment(line)
		if parsed_key is None:
			continue
		current_key = parsed_key
		frontmatter[current_key] = parsed_value

	return frontmatter


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
	lines = text.splitlines()
	if not has_frontmatter(lines):
		return {}, text

	end_index = find_frontmatter_end(lines)
	if end_index is None:
		return {}, text

	frontmatter = parse_frontmatter_lines(lines[1:end_index])
	body = "\n".join(lines[end_index + 1 :])
	return frontmatter, body


def find_referenced_resources(body: str) -> list[str]:
	found = RESOURCE_REF_RE.findall(body)
	return sorted(set(found))


def count_contract_references(body: str) -> int:
	return len(ROUTE_LOAD_RE.findall(body))


def detect_quick_reference(lines: list[str]) -> bool:
	for index, line in enumerate(lines):
		if "Quick Reference" not in line and "Quick Routing" not in line:
			continue
		window = lines[index : index + 10]
		table_lines = sum(1 for candidate in window if TABLE_LINE_RE.match(candidate))
		if table_lines >= 2:
			return True
	return False


def list_supporting_files(skill_root: Path) -> dict[str, list[str]]:
	results: dict[str, list[str]] = {}
	for directory_name in RESOURCE_DIRS:
		directory = skill_root / directory_name
		if not directory.exists() or not directory.is_dir():
			continue
		files = sorted(
			str(path.relative_to(skill_root))
			for path in directory.rglob("*")
			if path.is_file()
		)
		if files:
			results[directory_name] = files
	return results


def find_missing_references(skill_root: Path, references: list[str]) -> list[str]:
	return [relative_path for relative_path in references if not (skill_root / relative_path).exists()]


def find_generic_names(supporting_files: dict[str, list[str]]) -> list[str]:
	generic = []
	for files in supporting_files.values():
		for relative_path in files:
			stem = Path(relative_path).stem.lower()
			if stem in GENERIC_NAMES or re.fullmatch(r"ref\d+", stem):
				generic.append(relative_path)
	return generic


def classify_tools(frontmatter: dict[str, Any]) -> dict[str, Any]:
	tools = frontmatter.get("allowed-tools", [])
	if isinstance(tools, str):
		tools = [tools]
	tools = [tool.strip() for tool in tools]

	risky = []
	if any(tool.startswith("Write") or tool.startswith("Edit") for tool in tools):
		risky.append("contains mutating tools")
	if any((tool == "Bash") or (tool.startswith("Bash(") and "python" not in tool) for tool in tools):
		risky.append("contains broad shell access")

	return {
		"tools": tools,
		"tool_count": len(tools),
		"risky_notes": risky,
	}


def dedupe(items: list[str]) -> list[str]:
	seen = set()
	result = []
	for item in items:
		if item in seen:
			continue
		seen.add(item)
		result.append(item)
	return result


def score_structure_identity(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	score = 0
	strengths: list[str] = []
	recommendations: list[str] = []

	if metrics["has_frontmatter"]:
		score += 4
		strengths.append("SKILL.md has YAML frontmatter")
	else:
		recommendations.append("Add valid YAML frontmatter with at least name and description.")

	if metrics["has_name"]:
		score += 3
	else:
		recommendations.append("Add a name field to the frontmatter.")

	if metrics["has_description"]:
		score += 3
	else:
		recommendations.append("Add a description that states what the Skill does and when it should trigger.")

	return score, strengths, recommendations


def score_structure_layout(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	score = 0
	strengths: list[str] = []
	recommendations: list[str] = []

	body_line_count = metrics["body_line_count"]
	if body_line_count <= 500:
		score += 5
		strengths.append("SKILL.md stays within the 500-line guidance")
	elif body_line_count <= 650:
		score += 2
		recommendations.append("SKILL.md is drifting long; consider moving lower-frequency detail into supporting files.")
	else:
		recommendations.append("SKILL.md is too long for a routing document; split detailed content into reference files.")

	support_dir_count = metrics["support_dir_count"]
	if support_dir_count >= 2:
		score += 6
		strengths.append("The Skill uses multiple supporting resource directories")
	elif support_dir_count == 1:
		score += 3
		recommendations.append("Add supporting resource directories only where they materially improve routing or reuse.")
	else:
		recommendations.append("Consider adding supporting files only if the Skill scope needs them; right now everything depends on SKILL.md.")

	if metrics["generic_files"]:
		recommendations.append("Rename vague files such as ref1.md or misc.md to descriptive names.")
	else:
		score += 4

	if metrics["missing_references"]:
		recommendations.append("Fix broken references so every referenced file actually exists.")
	else:
		score += 5

	return score, strengths, recommendations


def score_structure(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	identity_score, identity_strengths, identity_recommendations = score_structure_identity(metrics)
	layout_score, layout_strengths, layout_recommendations = score_structure_layout(metrics)
	score = identity_score + layout_score
	strengths = identity_strengths + layout_strengths
	recommendations = identity_recommendations + layout_recommendations
	return min(score, 30), strengths, recommendations


def score_content_trigger(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	score = 0
	strengths: list[str] = []
	recommendations: list[str] = []

	description_length = metrics["description_length"]
	if metrics["has_description"] and 80 <= description_length <= 260:
		score += 6
		strengths.append("The description is reasonably compact")
	elif metrics["has_description"] and description_length > 0:
		score += 3
		recommendations.append("Tighten the description so it stays specific without overconsuming trigger budget.")

	if metrics["description_has_use_when"]:
		score += 4
	else:
		recommendations.append("Use a clear 'Use when ...' clause or equivalent trigger phrasing in the description.")

	return score, strengths, recommendations


def score_content_routing(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	score = 0
	strengths: list[str] = []
	recommendations: list[str] = []

	if metrics["has_quick_reference"]:
		score += 8
		strengths.append("A quick routing table is present near the top of the Skill")
	else:
		recommendations.append("Add a Quick Reference or Quick Routing table near the top of SKILL.md.")

	contract_reference_count = metrics["contract_reference_count"]
	if contract_reference_count >= 3:
		score += 12
		strengths.append("The Skill uses contract-style references for loading decisions")
	elif contract_reference_count >= 1:
		score += 6
		recommendations.append("Expand contract references so major resources have explicit load conditions and expected contents.")
	else:
		recommendations.append("Replace naked file mentions with contract references that say when to load the file and why.")

	references_count = metrics["references_count"]
	if references_count >= 3:
		score += 7
	elif references_count >= 1:
		score += 4
	else:
		recommendations.append("Reference supporting files only when they add real routing value.")

	return score, strengths, recommendations


def score_content_guidance(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	score = 0
	strengths: list[str] = []
	recommendations: list[str] = []

	if metrics["has_workflow_section"]:
		score += 6
	else:
		recommendations.append("Add an ordered workflow so the Skill executes predictably.")

	if metrics["has_output_guidelines"]:
		score += 4
	else:
		recommendations.append("Add output guidelines so evaluations are consistent and actionable.")

	if metrics["has_important_notes"]:
		score += 3
	else:
		recommendations.append("Add important notes or rules to clarify hard constraints and scoring policy.")

	return score, strengths, recommendations


def score_content(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	trigger_score, trigger_strengths, trigger_recommendations = score_content_trigger(metrics)
	routing_score, routing_strengths, routing_recommendations = score_content_routing(metrics)
	guidance_score, guidance_strengths, guidance_recommendations = score_content_guidance(metrics)
	score = trigger_score + routing_score + guidance_score
	strengths = trigger_strengths + routing_strengths + guidance_strengths
	recommendations = trigger_recommendations + routing_recommendations + guidance_recommendations
	return min(score, 40), strengths, recommendations


def score_progressive(metrics: dict[str, Any]) -> tuple[int, list[str], list[str]]:
	score = 0
	strengths: list[str] = []
	recommendations: list[str] = []

	body_line_count = metrics["body_line_count"]
	if body_line_count <= 500:
		score += 10
	elif body_line_count <= 650:
		score += 5

	has_dense_references = metrics["references_count"] >= 3 and metrics["contract_reference_count"] >= 3
	if has_dense_references:
		score += 10
		strengths.append("The Skill is set up for on-demand loading rather than inlining everything")
	elif metrics["references_count"] >= 1:
		score += 5
		recommendations.append("Strengthen progressive disclosure by pairing referenced files with explicit loading contracts.")
	else:
		recommendations.append("Add on-demand resources or simplify scope so the Skill remains efficient.")

	if metrics["has_script_reference"] and metrics["has_output_template_reference"]:
		score += 6
		strengths.append("Scripts and output templates are both part of the operating model")
	elif metrics["has_script_reference"] or metrics["has_output_template_reference"]:
		score += 3
		recommendations.append("Use both scripts and output templates when the task benefits from deterministic checks and standardized output.")
	else:
		recommendations.append("Consider whether scripts or output templates could remove deterministic or repetitive logic from SKILL.md.")

	if metrics["tool_risks"]:
		recommendations.append("Reduce allowed-tools to the minimum needed for the Skill's job.")
	else:
		score += 4

	return min(score, 30), strengths, recommendations


def compute_scores(metrics: dict[str, Any]) -> tuple[dict[str, int], list[str], list[str]]:
	structure_score, structure_strengths, structure_recommendations = score_structure(metrics)
	content_score, content_strengths, content_recommendations = score_content(metrics)
	progressive_score, progressive_strengths, progressive_recommendations = score_progressive(metrics)

	scores = {
		"structure_design": structure_score,
		"content_quality": content_score,
		"progressive_disclosure_operability": progressive_score,
	}
	strengths = structure_strengths + content_strengths + progressive_strengths
	recommendations = (
		structure_recommendations
		+ content_recommendations
		+ progressive_recommendations
	)
	return scores, dedupe(strengths), dedupe(recommendations)


def build_metrics(skill_root: Path, skill_md: Path) -> dict[str, Any]:
	text = read_text(skill_md)
	frontmatter, body = parse_frontmatter(text)
	body_lines = body.splitlines()
	references = find_referenced_resources(body)
	supporting_files = list_supporting_files(skill_root)
	tool_info = classify_tools(frontmatter)
	description = frontmatter.get("description", "") if frontmatter else ""

	return {
		"skill_root": str(skill_root),
		"skill_md": str(skill_md),
		"has_frontmatter": bool(frontmatter),
		"has_name": bool(frontmatter.get("name")) if frontmatter else False,
		"has_description": bool(description),
		"description_length": len(description),
		"description_has_use_when": "use when" in str(description).lower() or "什么时候" in str(description),
		"body_line_count": len(body_lines),
		"has_quick_reference": detect_quick_reference(body_lines),
		"has_workflow_section": "workflow" in body.lower() or "process" in body.lower(),
		"has_output_guidelines": "output guidelines" in body.lower(),
		"has_important_notes": "important notes" in body.lower() or "important rules" in body.lower(),
		"references": references,
		"references_count": len(references),
		"contract_reference_count": count_contract_references(body),
		"supporting_files": supporting_files,
		"support_dir_count": len(supporting_files),
		"missing_references": find_missing_references(skill_root, references),
		"generic_files": find_generic_names(supporting_files),
		"has_output_template_reference": any(ref.startswith(OUTPUT_RESOURCE_PREFIXES) for ref in references),
		"has_script_reference": any(ref.startswith("scripts/") for ref in references),
		"allowed_tools": tool_info["tools"],
		"tool_risks": tool_info["risky_notes"],
	}


def summarize_result(
	metrics: dict[str, Any],
	scores: dict[str, int],
	strengths: list[str],
	recommendations: list[str],
) -> dict[str, Any]:
	total = sum(scores.values())
	if total >= 90:
		verdict = "excellent"
	elif total >= 75:
		verdict = "strong"
	elif total >= 60:
		verdict = "acceptable"
	elif total >= 40:
		verdict = "weak"
	else:
		verdict = "needs redesign"

	return {
		"summary": {
			"total_score": total,
			"verdict": verdict,
		},
		"scores": scores,
		"metrics": metrics,
		"strengths": strengths,
		"recommendations": recommendations,
	}


def yes_no(value: bool) -> str:
	return "yes" if value else "no"


def print_text_report(result: dict[str, Any]) -> None:
	summary = result["summary"]
	scores = result["scores"]
	metrics = result["metrics"]

	print(f"Skill: {metrics['skill_root']}")
	print(f"Overall Score: {summary['total_score']}/100 ({summary['verdict']})")
	print()
	print("Scores:")
	print(f"- Structure Design: {scores['structure_design']}/30")
	print(f"- Content Quality: {scores['content_quality']}/40")
	print(f"- Progressive Disclosure & Operability: {scores['progressive_disclosure_operability']}/30")
	print()
	print("Key Metrics:")
	print(f"- Description length: {metrics['description_length']}")
	print(f"- SKILL.md body lines: {metrics['body_line_count']}")
	print(f"- Quick routing table present: {yes_no(metrics['has_quick_reference'])}")
	print(f"- Contract references: {metrics['contract_reference_count']}")
	print(f"- Referenced resources: {metrics['references_count']}")
	print(f"- Supporting directories with files: {metrics['support_dir_count']}")
	print(f"- Missing referenced files: {len(metrics['missing_references'])}")
	print()

	if result["strengths"]:
		print("Strengths:")
		for item in result["strengths"]:
			print(f"- {item}")
		print()

	if metrics["missing_references"] or metrics["generic_files"] or metrics["tool_risks"]:
		print("Warnings:")
		for item in metrics["missing_references"]:
			print(f"- Missing reference: {item}")
		for item in metrics["generic_files"]:
			print(f"- Generic file name: {item}")
		for item in metrics["tool_risks"]:
			print(f"- Tool risk: {item}")
		print()

	if result["recommendations"]:
		print("Recommendations:")
		for item in result["recommendations"]:
			print(f"- {item}")


def main() -> int:
	parser = argparse.ArgumentParser(description="Analyze a Skill directory or SKILL.md file")
	parser.add_argument("path", help="Path to a Skill directory or SKILL.md")
	parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
	args = parser.parse_args()

	try:
		skill_root, skill_md = resolve_skill_paths(args.path)
		metrics = build_metrics(skill_root, skill_md)
		scores, strengths, recommendations = compute_scores(metrics)
		result = summarize_result(metrics, scores, strengths, recommendations)
	except Exception as exc:  # noqa: BLE001
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	if args.json:
		print(json.dumps(result, indent=2, ensure_ascii=False))
	else:
		print_text_report(result)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
