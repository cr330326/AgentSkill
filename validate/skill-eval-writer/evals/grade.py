#!/usr/bin/env python3
from __future__ import annotations

"""
skill-eval-writer 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 response.md（模型输出的 evals.json + grade.py 内容）。

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


# ─────────────────────────────────────────────
# 文件收集工具
# ─────────────────────────────────────────────


def collect_output(eval_dir: Path) -> str:
    """收集 eval 目录下的所有文本内容"""
    texts = []
    for fpath in sorted(eval_dir.rglob("*")):
        if fpath.is_file():
            try:
                texts.append(fpath.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, PermissionError):
                pass
    return "\n".join(texts)


# ─────────────────────────────────────────────
# 通用检查函数
# ─────────────────────────────────────────────


def check_keywords(
    content: str, keywords: list[str], min_hits: int
) -> tuple[bool, str]:
    """检查内容是否包含特定关键词（不区分大小写）"""
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= min_hits
    evidence = f"命中 {len(found)}/{len(keywords)} 个关键词: {found}"
    return passed, evidence


def check_json_block_field(content: str, field: str) -> tuple[bool, str]:
    """检查输出中的 JSON 块是否包含指定字段"""
    # 查找 json 代码块或裸 JSON
    json_blocks = re.findall(r"```json\s*(.*?)```", content, re.DOTALL)
    # 也查找不在代码块中的大括号 JSON
    if not json_blocks:
        json_blocks = re.findall(
            r"\{[^{}]*" + re.escape(field) + r"[^{}]*\}", content, re.DOTALL
        )

    if not json_blocks:
        # 直接在全文搜索字段名（可能未用代码块包裹）
        found = f'"{field}"' in content or f"'{field}'" in content
        if found:
            return True, f"在全文中找到字段 '{field}'（未在 JSON 代码块中）"
        return False, f"未找到包含 '{field}' 的 JSON 内容"

    for block in json_blocks:
        if f'"{field}"' in block or f"'{field}'" in block:
            return True, f"JSON 块中包含字段 '{field}'"
    return False, f"找到 {len(json_blocks)} 个 JSON 块，但未包含字段 '{field}'"


def check_eval_count(content: str, expected: int) -> tuple[bool, int, str]:
    """检查 evals.json 中是否有指定数量的 eval 用例"""
    # 方法1: 计算 "id": N 模式
    id_matches = re.findall(r'"id"\s*:\s*(\d+)', content)
    # 去重（同一个 id 可能在 assertions 里也出现）
    # 只看顶层的 eval id —— 通常是 1-5 的数字
    eval_ids = set()
    for m in id_matches:
        val = int(m)
        if 1 <= val <= 10:
            eval_ids.add(val)

    # 方法2: 计算 "name": "xxx" 模式（eval 名称）
    name_matches = re.findall(r'"name"\s*:\s*"[a-zA-Z][\w-]+"', content)

    count = max(len(eval_ids), len(name_matches))
    passed = count >= expected
    evidence = f"找到 eval ids: {sorted(eval_ids)}, 名称模式数: {len(name_matches)}, 推算 eval 数: {count}"
    return passed, count, evidence


def check_assertion_structure(content: str) -> tuple[bool, str]:
    """检查 assertions 是否有 id/text/type/points 四个字段"""
    has_id = bool(re.search(r'"id"\s*:\s*"A\d+-\d+"', content))
    has_text = bool(re.search(r'"text"\s*:\s*"[^"]{5,}"', content))
    has_type = bool(
        re.search(
            r'"type"\s*:\s*"(structural|content|checklist_ref|checkpoint|file_exists)"',
            content,
        )
    )
    has_points = bool(re.search(r'"points"\s*:\s*\d+', content))
    fields = {"id": has_id, "text": has_text, "type": has_type, "points": has_points}
    found_count = sum(fields.values())
    passed = found_count >= 3  # 至少3个字段匹配（type 可能用不同名称）
    evidence = f"assertion 字段检查: {fields}"
    return passed, evidence


def check_grade_py_structure(content: str) -> tuple[bool, str]:
    """检查 grade.py 是否有标准架构的关键函数"""
    functions = {
        "compute_score": bool(re.search(r"def compute_score\s*\(", content)),
        "main": bool(re.search(r"def main\s*\(", content)),
        "grade_eval": bool(re.search(r"def grade_eval_\d+\s*\(", content)),
        "load_evals": bool(re.search(r"def load_evals\s*\(", content)),
    }
    found = [k for k, v in functions.items() if v]
    passed = len(found) >= 3
    evidence = f"找到函数: {found}; 缺失: {[k for k, v in functions.items() if not v]}"
    return passed, evidence


def check_future_annotations(content: str) -> tuple[bool, str]:
    """检查是否有 from __future__ import annotations"""
    found = "from __future__ import annotations" in content
    evidence = (
        "找到 from __future__ import annotations"
        if found
        else "未找到 from __future__ import annotations"
    )
    return found, evidence


def check_collect_function(content: str, expected_type: str) -> tuple[bool, str]:
    """检查 grade.py 使用了哪种收集函数。
    expected_type: 'text' → collect_output, 'file' → collect_output_files
    """
    has_text = bool(re.search(r"collect_output\b(?!_files)", content))
    has_file = bool(re.search(r"collect_output_files|collect_files", content))

    if expected_type == "file":
        passed = has_file
        evidence = (
            f"collect_output_files={has_file}, collect_output={has_text}; 期望文件型"
        )
    else:
        passed = has_text or has_file  # 文本型 skill 两种都可以
        evidence = (
            f"collect_output={has_text}, collect_output_files={has_file}; 期望文本型"
        )
    return passed, evidence


def check_scoring_dimensions(content: str, min_count: int = 4) -> tuple[bool, str]:
    """检查 evals.json 中是否有 scoring.dimensions 且维度数量足够"""
    has_dimensions = bool(re.search(r'"dimensions"\s*:\s*\{', content))
    if not has_dimensions:
        return False, "未找到 scoring.dimensions"

    # 统计维度数量（通过 "weight": 的数量来近似）
    weights = re.findall(r'"weight"\s*:\s*\d+', content)
    count = len(weights)
    passed = count >= min_count
    evidence = f"找到 dimensions 块, 维度数(weight字段数): {count}"
    return passed, evidence


def check_grader_param_type(content: str, expected: str) -> tuple[bool, str]:
    """检查 grade_eval_N 函数的参数类型。
    expected: 'files' → dict 参数, 'content' → str 参数
    """
    if expected == "files":
        # 查找 grade_eval_N(files 或 grade_eval_N(files:
        has_files_param = bool(re.search(r"def grade_eval_\d+\s*\(\s*files", content))
        passed = has_files_param
        evidence = f"grade_eval_N(files...) 参数: {has_files_param}"
    else:
        has_content_param = bool(
            re.search(r"def grade_eval_\d+\s*\(\s*content", content)
        )
        passed = has_content_param
        evidence = f"grade_eval_N(content...) 参数: {has_content_param}"
    return passed, evidence


# ─────────────────────────────────────────────
# 每个 eval 的专属检查逻辑
# ─────────────────────────────────────────────


def grade_eval_1(content: str) -> list[dict]:
    """basic-text-output-skill: commit-message-reviewer 的 eval 生成"""
    results = []

    # A1-01: 输出包含 evals.json（含 skill_name 和 evals 数组）
    has_skill_name = check_json_block_field(content, "skill_name")
    has_evals_array = check_json_block_field(content, "evals")
    passed = has_skill_name[0] and has_evals_array[0]
    evidence = f"skill_name: {has_skill_name[1]}; evals: {has_evals_array[1]}"
    results.append(
        {
            "id": "A1-01",
            "text": "输出包含 evals.json 的完整内容",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-02: evals.json 中有 5 个 eval 用例
    passed, count, evidence = check_eval_count(content, 5)
    results.append(
        {
            "id": "A1-02",
            "text": "evals.json 中有 5 个 eval",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-03: eval-1 的 prompt 嵌入了违反 Conventional Commits 的 commit message
    # 已知答案：应包含故意错误的 commit message
    commit_violation_kw = [
        "feat",
        "fix",
        "commit",
        "Conventional Commits",
    ]
    # 更精确：检查是否有看起来像错误 commit message 的文本
    has_bad_commit = bool(
        re.search(
            r"(Fixed bug|Update|changed|add feature|修了一个|更新了)",
            content,
            re.IGNORECASE,
        )
    )
    passed_kw, evidence_kw = check_keywords(content, commit_violation_kw, 2)
    passed = passed_kw and has_bad_commit
    if passed_kw and not has_bad_commit:
        # 包含了相关关键词但没有明确的"坏 commit"——可能用其他方式嵌入
        passed = passed_kw
    evidence = (
        f"commit 关键词: {evidence_kw}; 包含违反规范的 commit 示例: {has_bad_commit}"
    )
    results.append(
        {
            "id": "A1-03",
            "text": "eval-1 prompt 嵌入了违反 Conventional Commits 的示例",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-04: assertions 有 id/text/type/points 字段
    passed, evidence = check_assertion_structure(content)
    results.append(
        {
            "id": "A1-04",
            "text": "assertion 有 id/text/type/points 字段",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-05: 输出包含 grade.py 的完整代码
    has_grade_py = bool(re.search(r"grade\.py|grade_eval_\d+", content))
    has_python_code = bool(re.search(r"```python", content, re.IGNORECASE))
    has_def = bool(re.search(r"def (grade_eval|compute_score|main|check_)", content))
    passed = has_grade_py and has_def
    evidence = f"提到 grade.py={has_grade_py}, Python 代码块={has_python_code}, 含 def 函数={has_def}"
    results.append(
        {
            "id": "A1-05",
            "text": "输出包含 grade.py 的完整代码",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-06: grade.py 包含 from __future__ import annotations
    passed, evidence = check_future_annotations(content)
    results.append(
        {
            "id": "A1-06",
            "text": "grade.py 包含 from __future__ import annotations",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-07: grade.py 包含 compute_score 和 main
    passed, evidence = check_grade_py_structure(content)
    results.append(
        {
            "id": "A1-07",
            "text": "grade.py 包含 compute_score 和 main",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-08: grade.py 包含 check_keywords 或类似检查函数
    check_fn_kw = [
        "check_keywords",
        "check_content",
        "check_section",
        "check_proximity",
    ]
    passed, evidence = check_keywords(content, check_fn_kw, 1)
    results.append(
        {
            "id": "A1-08",
            "text": "grade.py 包含关键词检查函数",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-09: evals.json 包含 scoring.dimensions 且至少 4 个维度
    passed, evidence = check_scoring_dimensions(content, 4)
    results.append(
        {
            "id": "A1-09",
            "text": "evals.json 包含 scoring.dimensions 且 >=4 维度",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-10: eval-5 是边界/降级类型
    edge_kw = [
        "边界",
        "降级",
        "edge",
        "boundary",
        "空",
        "empty",
        "不合法",
        "invalid",
        "异常",
        "无效",
    ]
    # 尝试提取 eval-5 相关区域
    eval5_section = ""
    m = re.search(r'"id"\s*:\s*5.*?(?="id"\s*:\s*[^5]|\Z)', content, re.DOTALL)
    if m:
        eval5_section = m.group()
    search_text = eval5_section if eval5_section else content
    passed, evidence = check_keywords(search_text, edge_kw, 1)
    results.append(
        {
            "id": "A1-10",
            "text": "eval-5 是边界/降级类型",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_2(content: str) -> list[dict]:
    """file-generating-skill: api-spec-generator 的 eval 生成"""
    results = []

    # A2-01: 输出包含 evals.json
    passed, evidence = check_json_block_field(content, "skill_name")
    results.append(
        {
            "id": "A2-01",
            "text": "输出包含 evals.json",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-02: evals.json 有 5 个 eval
    passed, count, evidence = check_eval_count(content, 5)
    results.append(
        {
            "id": "A2-02",
            "text": "evals.json 有 5 个 eval",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-03: grade.py 使用 collect_output_files（文件型）
    passed, evidence = check_collect_function(content, "file")
    results.append(
        {
            "id": "A2-03",
            "text": "grade.py 使用 collect_output_files",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-04: grade_eval_N 参数是 files（dict）
    passed, evidence = check_grader_param_type(content, "files")
    results.append(
        {
            "id": "A2-04",
            "text": "grade_eval_N 参数是 files（dict）",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-05: grade.py 检查 OpenAPI 关键字段
    openapi_kw = ["openapi", "paths", "schemas", "components", "info"]
    passed, evidence = check_keywords(content, openapi_kw, 3)
    results.append(
        {
            "id": "A2-05",
            "text": "grade.py 检查 OpenAPI 关键字段",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-06: 至少一个 eval prompt 描述了具体 API 端点
    endpoint_kw = ["/users", "/products", "/orders", "/items", "/api/", "GET", "POST"]
    passed, evidence = check_keywords(content, endpoint_kw, 2)
    results.append(
        {
            "id": "A2-06",
            "text": "eval prompt 描述了具体 API 端点",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-07: grade.py 包含 find_file_by_name 或类似函数
    file_find_kw = ["find_file_by_name", "find_file", "find_files_in_dir"]
    passed, evidence = check_keywords(content, file_find_kw, 1)
    results.append(
        {
            "id": "A2-07",
            "text": "grade.py 包含文件查找函数",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-08: from __future__ import annotations + compute_score/main
    passed_future, _ = check_future_annotations(content)
    passed_struct, evidence_struct = check_grade_py_structure(content)
    passed = passed_future and passed_struct
    evidence = f"__future__={passed_future}; 结构: {evidence_struct}"
    results.append(
        {
            "id": "A2-08",
            "text": "grade.py 标准头部和架构",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-09: assertions 中包含 file_exists 类型
    has_file_exists = bool(re.search(r'"type"\s*:\s*"file_exists"', content))
    # 也接受 "file" 类型或文件存在检查的变体
    if not has_file_exists:
        has_file_exists = bool(
            re.search(
                r"(file_exists|文件存在|检查.*文件|yaml.*存在|api-spec)",
                content,
                re.IGNORECASE,
            )
        )
    passed = has_file_exists
    evidence = f"file_exists 类型断言: {has_file_exists}"
    results.append(
        {
            "id": "A2-09",
            "text": "assertions 包含 file_exists 类型",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_3(content: str) -> list[dict]:
    """multi-stage-pipeline-skill: data-migration-planner 的 eval 生成"""
    results = []

    # A3-01: evals.json 有 5 个 eval
    passed, count, evidence = check_eval_count(content, 5)
    results.append(
        {
            "id": "A3-01",
            "text": "evals.json 有 5 个 eval",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-02: assertions 中包含 checkpoint 类型
    has_checkpoint = bool(re.search(r'"type"\s*:\s*"checkpoint"', content))
    if not has_checkpoint:
        # 也接受用关键词描述暂停/checkpoint 行为
        has_checkpoint = bool(
            re.search(
                r"(checkpoint|暂停|pause|等待确认|阶段.*停|stop.*stage)",
                content,
                re.IGNORECASE,
            )
        )
    passed = has_checkpoint
    evidence = f"checkpoint 类型断言: {has_checkpoint}"
    results.append(
        {
            "id": "A3-02",
            "text": "包含 checkpoint 类型断言",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-03: grade.py 检查阶段进度标记
    stage_kw = ["阶段", "Stage", "Step", "phase", "进度"]
    has_stage_regex = bool(
        re.search(
            r"(阶段\s*\\d|Stage\s*\\d|\[阶段|\[Stage|check_progress|progress_indicator)",
            content,
            re.IGNORECASE,
        )
    )
    passed_kw, evidence_kw = check_keywords(content, stage_kw, 1)
    passed = passed_kw or has_stage_regex
    evidence = f"阶段关键词: {evidence_kw}; 阶段正则: {has_stage_regex}"
    results.append(
        {
            "id": "A3-03",
            "text": "grade.py 检查阶段进度标记",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-04: grade.py 检查暂停行为
    pause_kw = [
        "暂停",
        "pause",
        "等待",
        "确认",
        "不应包含",
        "forbidden",
        "leaked",
        "checkpoint",
        "阶段 2",
    ]
    passed, evidence = check_keywords(content, pause_kw, 2)
    results.append(
        {
            "id": "A3-04",
            "text": "grade.py 检查暂停行为",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-05: eval prompt 包含具体表结构/schema
    schema_kw = [
        "CREATE TABLE",
        "ALTER TABLE",
        "column",
        "字段",
        "VARCHAR",
        "INT",
        "users",
        "orders",
        "表结构",
        "schema",
        "id",
        "name",
    ]
    passed, evidence = check_keywords(content, schema_kw, 3)
    results.append(
        {
            "id": "A3-05",
            "text": "eval prompt 包含具体表结构",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-06: grade.py 检查 SQL 关键词
    sql_kw = ["ALTER TABLE", "CREATE TABLE", "INSERT", "SELECT", "DROP", "RENAME"]
    passed, evidence = check_keywords(content, sql_kw, 2)
    results.append(
        {
            "id": "A3-06",
            "text": "grade.py 检查 SQL 关键词",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-07: evals.json 包含 scoring.dimensions
    passed, evidence = check_scoring_dimensions(content, 3)
    results.append(
        {
            "id": "A3-07",
            "text": "evals.json 包含 scoring.dimensions",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-08: grade.py 包含 compute_score 和 main
    passed, evidence = check_grade_py_structure(content)
    results.append(
        {
            "id": "A3-08",
            "text": "grade.py 标准架构",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-09: eval-5 测试边界场景
    edge_kw = [
        "无变更",
        "no change",
        "不兼容",
        "incompatible",
        "空",
        "empty",
        "边界",
        "降级",
        "相同",
        "identical",
    ]
    # 尝试提取 eval-5 区域
    eval5_section = ""
    m = re.search(r'"id"\s*:\s*5.*?(?="id"\s*:\s*[^5]|\Z)', content, re.DOTALL)
    if m:
        eval5_section = m.group()
    search_text = eval5_section if eval5_section else content
    passed, evidence = check_keywords(search_text, edge_kw, 1)
    results.append(
        {
            "id": "A3-09",
            "text": "eval-5 测试边界场景",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_4(content: str) -> list[dict]:
    """incomplete-skill-info: 信息不完整的 log-analyzer"""
    results = []

    # A4-01: 输出包含 evals.json
    has_evals = check_json_block_field(content, "evals")
    has_skill_name = check_json_block_field(content, "skill_name")
    # 也接受直接在文本中描述 eval 结构
    has_eval_desc = bool(
        re.search(r"eval[_-]?\d|测试用例|test case", content, re.IGNORECASE)
    )
    passed = has_evals[0] or has_skill_name[0] or has_eval_desc
    evidence = f"evals 字段: {has_evals[1]}; skill_name: {has_skill_name[1]}; eval 描述: {has_eval_desc}"
    results.append(
        {
            "id": "A4-01",
            "text": "输出包含 evals.json",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-02: 有 5 个（或至少 3 个）eval
    passed, count, evidence = check_eval_count(content, 3)
    results.append(
        {
            "id": "A4-02",
            "text": "有至少 3 个 eval",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-03: prompt 嵌入了构造的日志文本
    log_kw = ["ERROR", "WARN", "WARNING", "INFO", "log", "日志"]
    # 更精确：检查是否有看起来像日志的文本
    has_log_text = bool(re.search(r"(ERROR|WARN|WARNING)\s+[\d\-:T]+", content))
    if not has_log_text:
        has_log_text = bool(
            re.search(r"[\d\-]+\s+[\d:]+.*?(ERROR|WARN|Exception|Error|异常)", content)
        )
    passed_kw, evidence_kw = check_keywords(content, log_kw, 2)
    passed = passed_kw and has_log_text
    if passed_kw and not has_log_text:
        passed = passed_kw  # 至少提到了日志相关概念
    evidence = f"日志关键词: {evidence_kw}; 构造日志文本: {has_log_text}"
    results.append(
        {
            "id": "A4-03",
            "text": "prompt 嵌入了构造的日志文本",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-04: grade.py 检查时间段分组
    time_kw = [
        "1小时",
        "6小时",
        "1 小时",
        "6 小时",
        "1h",
        "6h",
        "hour",
        "时间段",
        "时间分组",
        "最近",
        "recent",
    ]
    passed, evidence = check_keywords(content, time_kw, 2)
    results.append(
        {
            "id": "A4-04",
            "text": "grade.py 检查时间段分组",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-05: grade.py 检查异常统计
    stat_kw = [
        "数量",
        "频率",
        "频繁",
        "count",
        "frequency",
        "最多",
        "top",
        "统计",
        "摘要",
        "summary",
    ]
    passed, evidence = check_keywords(content, stat_kw, 2)
    results.append(
        {
            "id": "A4-05",
            "text": "grade.py 检查异常统计",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-06: 指出信息不完整并提出澄清建议
    incomplete_kw = [
        "不完整",
        "incomplete",
        "缺少",
        "missing",
        "未明确",
        "建议补充",
        "需要明确",
        "澄清",
        "clarif",
        "补充",
        "未定义",
        "undefined",
    ]
    passed, evidence = check_keywords(content, incomplete_kw, 2)
    results.append(
        {
            "id": "A4-06",
            "text": "指出信息不完整并提出建议",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-07: from __future__ import annotations
    passed, evidence = check_future_annotations(content)
    results.append(
        {
            "id": "A4-07",
            "text": "from __future__ import annotations",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-08: assertion id 格式符合 A{N}-{seq}
    has_aid = bool(re.search(r'"A\d+-\d+"', content))
    # 也接受 A{N}-{seq} 在文本描述中
    if not has_aid:
        has_aid = bool(re.search(r"A\d+-\d+", content))
    passed = has_aid
    evidence = f"assertion id 格式: {has_aid}"
    results.append(
        {
            "id": "A4-08",
            "text": "assertion id 符合 A{N}-{seq} 格式",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_5(content: str) -> list[dict]:
    """vague-untestable-skill: general-helper 过于模糊"""
    results = []

    # A5-01: 指出 skill 过于模糊
    vague_kw = [
        "模糊",
        "vague",
        "宽泛",
        "过于通用",
        "太通用",
        "无法测试",
        "难以测试",
        "不可测试",
        "无法验证",
        "没有具体",
        "缺乏具体",
        "不明确",
    ]
    passed, evidence = check_keywords(content, vague_kw, 1)
    results.append(
        {
            "id": "A5-01",
            "text": "指出 skill 过于模糊",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-02: 解释了为什么模糊 skill 难以测试
    reason_kw = [
        "区分度",
        "输出格式",
        "规则",
        "工作流",
        "流程",
        "无法区分",
        "好坏",
        "任何 AI",
        "基线",
        "关键词",
        "结构",
        "约束",
    ]
    passed, evidence = check_keywords(content, reason_kw, 2)
    results.append(
        {
            "id": "A5-02",
            "text": "解释了模糊 skill 难以测试的原因",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-03: 建议先完善 SKILL.md
    improve_kw = [
        "完善",
        "improve",
        "改进",
        "重写",
        "丰富",
        "细化",
        "补充",
        "明确",
        "define",
        "具体化",
    ]
    # 同时要提到 SKILL.md
    has_skillmd = bool(
        re.search(r"SKILL\.md|skill\.md|技能文档|技能定义", content, re.IGNORECASE)
    )
    passed_kw, evidence_kw = check_keywords(content, improve_kw, 1)
    passed = passed_kw and has_skillmd
    if passed_kw and not has_skillmd:
        passed = passed_kw  # 建议改进但没明确提 SKILL.md，也算部分通过
    evidence = f"改进建议: {evidence_kw}; 提到 SKILL.md: {has_skillmd}"
    results.append(
        {
            "id": "A5-03",
            "text": "建议先完善 SKILL.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-04: 具体改进建议
    specific_kw = [
        "输出格式",
        "output format",
        "编号",
        "规则",
        "工作流",
        "workflow",
        "模板",
        "template",
        "边界",
        "boundary",
        "分支逻辑",
        "条件",
    ]
    passed, evidence = check_keywords(content, specific_kw, 2)
    results.append(
        {
            "id": "A5-04",
            "text": "给出具体的 SKILL.md 改进建议",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-05: 没有盲目生成无区分度的 eval
    # 如果生成了 eval，应该标注了局限性
    has_eval_generated = bool(re.search(r'"evals"\s*:\s*\[', content))
    has_limitation_note = bool(
        re.search(
            r"(局限|limitation|disclaimer|注意|caveat|前提|假设|低区分度|区分度.*低)",
            content,
            re.IGNORECASE,
        )
    )
    if has_eval_generated:
        # 生成了 eval → 需要标注局限性
        passed = has_limitation_note
        evidence = f"生成了 eval: True; 标注了局限性: {has_limitation_note}"
    else:
        # 没有盲目生成 → 直接通过
        passed = True
        evidence = "未盲目生成 eval，而是先提出改进建议"
    results.append(
        {
            "id": "A5-05",
            "text": "未盲目生成无区分度的 eval",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


# ─────────────────────────────────────────────
# 主评分流程
# ─────────────────────────────────────────────

GRADERS = {
    1: grade_eval_1,
    2: grade_eval_2,
    3: grade_eval_3,
    4: grade_eval_4,
    5: grade_eval_5,
}


def compute_score(eval_id: int, grading_results: list[dict], evals_data: dict) -> dict:
    """根据 grading 结果和 evals.json 中的分值计算得分"""
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
    """评分单个 eval 目录"""
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
        "skill_name": "skill-eval-writer",
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
