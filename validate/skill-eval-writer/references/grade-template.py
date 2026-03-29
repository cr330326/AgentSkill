#!/usr/bin/env python3
from __future__ import annotations

"""
{skill_name} 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 response.md（模型输出）或其他生成的文件。

也可以传入单个 eval 目录:
    python grade.py output_dir/eval-1

脚本自动检测输出，执行可程序化验证的断言。
最终输出 grading.json 到 output_dir/ 下。
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────
# 加载 evals.json
# ─────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
EVALS_PATH = SCRIPT_DIR / "evals.json"


def load_evals() -> dict:
    with open(EVALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ═════════════════════════════════════════════
# 文件收集工具 — 二选一
# ═════════════════════════════════════════════
#
# 根据目标 skill 的输出类型选择：
# - 文本输出型 skill（审查报告、对话式回复）→ collect_output()
# - 文件生成型 skill（生成 SKILL.md + references/）→ collect_output_files()
#
# 对应地，grade_eval_N() 的签名也不同：
# - 文本型：grade_eval_N(content: str) -> list[dict]
# - 文件型：grade_eval_N(files: dict[str, str]) -> list[dict]


def collect_output(eval_dir: Path) -> str:
    """收集 eval 目录下的所有文本内容，拼接为一个字符串。
    适用于文本输出型 skill。"""
    texts = []
    for fpath in sorted(eval_dir.rglob("*")):
        if fpath.is_file():
            try:
                texts.append(fpath.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, PermissionError):
                pass
    return "\n".join(texts)


def collect_output_files(eval_dir: Path) -> dict[str, str]:
    """递归收集 eval 目录下所有文件内容，返回 {相对路径: 内容}。
    适用于文件生成型 skill。"""
    files = {}
    for fpath in eval_dir.rglob("*"):
        if fpath.is_file():
            rel = str(fpath.relative_to(eval_dir))
            try:
                files[rel] = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                files[rel] = "<binary or unreadable>"
    return files


# ═════════════════════════════════════════════
# 通用检查函数
# ═════════════════════════════════════════════
#
# 所有检查函数返回 tuple[bool, str]：
#   (passed, evidence)
# evidence 是人类可读的证据字符串，用于调试。
#
# 从 references/check-functions-catalog.md 中选取你需要的函数，
# 并根据目标 skill 的特点编写领域专用的新函数。


def check_keywords(
    content: str, keywords: list[str], min_hits: int
) -> tuple[bool, str]:
    """检查内容是否包含足够数量的关键词（不区分大小写）。

    用法：验证输出是否提到了关键概念。
    注意：避免使用过宽的关键词（如"使用"、"建议"），优先选择领域特有词汇。
    """
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= min_hits
    evidence = f"命中 {len(found)}/{len(keywords)} 个关键词: {found}"
    return passed, evidence


def check_section_content(
    content: str, section_heading: str, keywords: list[str], min_hits: int = 1
) -> tuple[bool, str]:
    """提取指定 ## 标题下的内容段落，检查其中是否包含关键词。

    注意：使用 (?=\\n## [^#]|\\Z) 避免 ### 子标题中断匹配。
    """
    pattern = rf"## {re.escape(section_heading)}(.*?)(?=\n## [^#]|\Z)"
    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not m:
        return False, f"未找到 '## {section_heading}' 段落"
    section = m.group(1)
    found = [kw for kw in keywords if kw.lower() in section.lower()]
    passed = len(found) >= min_hits
    evidence = f"'{section_heading}' 段中命中 {len(found)}/{len(keywords)}: {found}"
    return passed, evidence


def check_proximity(
    content: str, word_a: str, word_b: str, max_distance: int = 30
) -> tuple[bool, str]:
    """检查两个关键词是否在指定字符距离内共现（近邻匹配）。

    用法：验证"SQL 注入"和"参数化查询"是否在同一段落中一起出现，
    比分别检查各自存在更有区分度。
    """
    pattern = rf"({re.escape(word_a)}).{{0,{max_distance}}}({re.escape(word_b)})"
    m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if m:
        return True, f"找到近邻匹配: '{m.group()}'"
    # 反方向
    pattern = rf"({re.escape(word_b)}).{{0,{max_distance}}}({re.escape(word_a)})"
    m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if m:
        return True, f"找到近邻匹配（反向）: '{m.group()}'"
    return False, f"'{word_a}' 和 '{word_b}' 未在 {max_distance} 字符内共现"


def check_count_summary(content: str) -> tuple[bool, str]:
    """检查是否有数量统计（如"共发现 12 个问题"）。

    注意：数字可能被 **bold** 包裹，用 \\*{0,2} 匹配。
    """
    patterns = [
        r"共\s*\*{0,2}\d+\*{0,2}\s*个",
        r"发现了?\s*\*{0,2}\d+\*{0,2}\s*个",
        r"\d+\s*个(问题|规则|条目|步骤|阶段)",
        r"Total.*\d+",
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.extend(matches[:2])
    passed = len(found) > 0
    evidence = f"找到统计: {found[:3]}" if found else "未找到数量统计"
    return passed, evidence


def check_specific_id(content: str, target_id: str) -> tuple[bool, str]:
    """检查是否引用了某个具体编号（如 PY-24、SEC-09）。"""
    found = target_id.upper() in content.upper()
    evidence = f"{'找到' if found else '未找到'} {target_id}"
    return found, evidence


def check_specific_ids_any(content: str, target_ids: list[str]) -> tuple[bool, str]:
    """检查是否引用了目标编号中的至少一个。"""
    found = [tid for tid in target_ids if tid.upper() in content.upper()]
    passed = len(found) > 0
    evidence = f"找到: {found}" if found else f"未找到 {target_ids} 中的任何一个"
    return passed, evidence


def check_checklist_ids(
    content: str, prefix: str, min_count: int
) -> tuple[bool, int, str]:
    """检查是否引用了指定前缀的编号（如 PY-01, SEC-09, DOC-06）。
    返回 (passed, count, evidence)。
    """
    pattern = rf"{prefix}-\d{{1,2}}"
    matches = list(set(re.findall(pattern, content, re.IGNORECASE)))
    count = len(matches)
    passed = count >= min_count
    evidence = f"找到 {count} 个 {prefix}-xx 编号: {matches[:10]}"
    return passed, count, evidence


# ── 文件生成型 skill 专用 ──


def find_file_by_name(files: dict[str, str], name: str) -> tuple[str, str]:
    """在 files dict 中查找文件名匹配的文件（不区分目录层级）。
    返回 (path, content) 或 (None, None)。

    注意：返回类型用 tuple[str, str] 而非 str | None，兼容 Python 3.9。
    调用方需要处理 None 的情况。
    """
    for path, content in files.items():
        if Path(path).name.lower() == name.lower():
            return path, content
    return None, None


def find_files_in_dir(files: dict[str, str], dirname: str) -> dict[str, str]:
    """查找某个目录下的所有文件。"""
    result = {}
    for path, content in files.items():
        parts = Path(path).parts
        if dirname in parts:
            result[path] = content
    return result


def check_yaml_frontmatter(content: str) -> tuple[bool, str]:
    """检查文件是否有合法的 YAML frontmatter（--- 包裹，含 name 和 description）。"""
    if not content.strip().startswith("---"):
        return False, "文件不以 --- 开头，缺少 YAML frontmatter"
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, "YAML frontmatter 未正确闭合"
    fm = parts[1]
    has_name = bool(re.search(r"^name\s*:", fm, re.MULTILINE))
    has_desc = bool(re.search(r"^description\s*:", fm, re.MULTILINE))
    if not has_name:
        return False, "frontmatter 缺少 name 字段"
    if not has_desc:
        return False, "frontmatter 缺少 description 字段"
    return True, "YAML frontmatter 结构正确"


# ═════════════════════════════════════════════
# 每个 eval 的专属检查逻辑
# ═════════════════════════════════════════════
#
# 根据输出类型选择参数签名：
#   def grade_eval_N(content: str) -> list[dict]:   # 文本型
#   def grade_eval_N(files: dict[str, str]) -> list[dict]:  # 文件型
#
# 每个函数返回 list[dict]，每个 dict 的结构：
# {
#     "id": "A1-01",        # 与 evals.json 中的 assertion id 对应
#     "text": "断言描述",    # 人类可读
#     "passed": True/False,  # 是否通过
#     "evidence": "证据"     # 调试用
# }


def grade_eval_1(content: str) -> list[dict]:
    """eval-1 的描述：基本路径

    TODO: 根据 evals.json 中 eval-1 的 assertions 实现检查逻辑。
    """
    results = []

    # A1-01: 示例断言 — 替换为实际断言
    passed, evidence = check_keywords(content, ["关键词1", "关键词2"], 1)
    results.append(
        {
            "id": "A1-01",
            "text": "断言描述",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-02: ...
    # 继续添加断言

    return results


def grade_eval_2(content: str) -> list[dict]:
    """eval-2 的描述：领域变体

    TODO: 实现检查逻辑。
    """
    results = []
    # ...
    return results


def grade_eval_3(content: str) -> list[dict]:
    """eval-3 的描述：领域跨越

    TODO: 实现检查逻辑。
    """
    results = []
    # ...
    return results


def grade_eval_4(content: str) -> list[dict]:
    """eval-4 的描述：模糊/自动检测

    TODO: 实现检查逻辑。
    """
    results = []
    # ...
    return results


def grade_eval_5(content: str) -> list[dict]:
    """eval-5 的描述：边界/降级

    TODO: 实现检查逻辑。
    """
    results = []
    # ...
    return results


# ═════════════════════════════════════════════
# 主评分流程 — 以下部分通常不需要修改
# ═════════════════════════════════════════════

GRADERS = {
    1: grade_eval_1,
    2: grade_eval_2,
    3: grade_eval_3,
    4: grade_eval_4,
    5: grade_eval_5,
}


def compute_score(eval_id: int, grading_results: list[dict], evals_data: dict) -> dict:
    """根据 grading 结果和 evals.json 中的分值计算得分。

    此函数通常不需要修改。它从 evals.json 中读取每个 assertion 的
    points 值，对照 grading_results 中的 passed 状态计算得分。
    """
    eval_def = None
    for e in evals_data["evals"]:
        if e["id"] == eval_id:
            eval_def = e
            break
    if not eval_def:
        return {"earned": 0, "possible": 0, "percentage": 0}

    assertion_points = {a["id"]: a["points"] for a in eval_def["assertions"]}
    earned = 0
    possible = 0
    for result in grading_results:
        aid = result["id"]
        pts = assertion_points.get(aid, 0)
        possible += pts
        if result["passed"]:
            earned += pts

    return {
        "earned": earned,
        "possible": possible,
        "percentage": round(earned / possible * 100, 1) if possible > 0 else 0,
    }


def grade_single_eval(eval_dir: Path, eval_id: int, evals_data: dict) -> dict:
    """评分单个 eval 目录。

    对于文件生成型 skill，将 collect_output() 替换为 collect_output_files()，
    并将 grader(content) 改为 grader(files)。
    """
    content = collect_output(eval_dir)
    if not content.strip():
        return {
            "eval_id": eval_id,
            "status": "error",
            "message": f"目录为空或无可读文件: {eval_dir}",
            "results": [],
            "score": {"earned": 0, "possible": 0, "percentage": 0},
        }

    grader = GRADERS.get(eval_id)
    if not grader:
        return {
            "eval_id": eval_id,
            "status": "error",
            "message": f"未找到 eval_id={eval_id} 的评分函数",
            "results": [],
            "score": {"earned": 0, "possible": 0, "percentage": 0},
        }

    results = grader(content)
    score = compute_score(eval_id, results, evals_data)

    return {
        "eval_id": eval_id,
        "eval_name": next(
            (e["name"] for e in evals_data["evals"] if e["id"] == eval_id),
            f"eval-{eval_id}",
        ),
        "status": "graded",
        "results": results,
        "score": score,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])
    evals_data = load_evals()

    if not target.exists():
        print(f"错误: 路径不存在: {target}")
        sys.exit(1)

    all_gradings = []

    # 判断是单个 eval 目录还是包含多个 eval 的父目录
    eval_dirs = []

    has_content = any(target.rglob("*.md")) or any(target.rglob("*.txt"))
    match = re.search(r"eval-?(\d+)", target.name)
    if match and has_content:
        eval_dirs = [(target, int(match.group(1)))]
    else:
        for subdir in sorted(target.iterdir()):
            if subdir.is_dir():
                match = re.search(r"eval-?(\d+)", subdir.name)
                if match:
                    eval_dirs.append((subdir, int(match.group(1))))

    if not eval_dirs:
        print(f"错误: 未在 {target} 下找到可评分的目录")
        print("目录结构应为 eval-1/, eval-2/, ... 包含 response.md 或其他输出文件")
        sys.exit(1)

    for eval_dir, eval_id in eval_dirs:
        print(f"\n{'=' * 60}")
        print(f"评分: eval-{eval_id} ({eval_dir.name})")
        print(f"{'=' * 60}")

        result = grade_single_eval(eval_dir, eval_id, evals_data)
        all_gradings.append(result)

        for r in result["results"]:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] {r['id']}: {r['text']}")
            print(f"         {r['evidence']}")
        print(
            f"\n  得分: {result['score']['earned']}/{result['score']['possible']}"
            f" ({result['score']['percentage']}%)"
        )

    # 计算总分
    total_earned = sum(g["score"]["earned"] for g in all_gradings)
    total_possible = sum(g["score"]["possible"] for g in all_gradings)
    total_pct = (
        round(total_earned / total_possible * 100, 1) if total_possible > 0 else 0
    )

    summary = {
        "skill_name": "{skill_name}",  # TODO: 替换为实际 skill 名称
        "total_score": {
            "earned": total_earned,
            "possible": total_possible,
            "percentage": total_pct,
        },
        "per_eval": all_gradings,
    }

    print(f"\n{'=' * 60}")
    print(f"总分: {total_earned}/{total_possible} ({total_pct}%)")
    print(f"{'=' * 60}")

    # 写入 grading.json
    output_path = target / "grading.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n评分结果已保存到: {output_path}")

    return summary


if __name__ == "__main__":
    main()
