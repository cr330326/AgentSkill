#!/usr/bin/env python3
from __future__ import annotations

"""
skill-reviewer 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 response.md（模型输出的审查报告）。

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


def check_checklist_loaded(content: str, checklist_name: str) -> tuple[bool, str]:
    """检查是否提到了加载某个审查清单"""
    indicators = [
        checklist_name.lower(),
        checklist_name.replace("-", " ").lower(),
        checklist_name.replace("-checklist", "").lower(),
    ]
    found = [ind for ind in indicators if ind in content.lower()]
    passed = len(found) > 0
    evidence = (
        f"找到清单引用: {found}" if found else f"未找到 {checklist_name} 相关引用"
    )
    return passed, evidence


def check_checklist_ids(
    content: str, prefix: str, min_count: int
) -> tuple[bool, int, str]:
    """检查是否引用了指定前缀的清单编号（如 PY-01, SEC-09, DOC-06）"""
    pattern = rf"{prefix}-\d{{1,2}}"
    matches = list(set(re.findall(pattern, content, re.IGNORECASE)))
    count = len(matches)
    passed = count >= min_count
    evidence = f"找到 {count} 个 {prefix}-xx 编号: {matches[:10]}"
    return passed, count, evidence


def check_specific_id(content: str, target_id: str) -> tuple[bool, str]:
    """检查是否引用了某个具体的清单编号"""
    found = target_id.upper() in content.upper()
    evidence = f"{'找到' if found else '未找到'} {target_id}"
    return found, evidence


def check_specific_ids_any(content: str, target_ids: list[str]) -> tuple[bool, str]:
    """检查是否引用了目标编号中的至少一个"""
    found = [tid for tid in target_ids if tid.upper() in content.upper()]
    passed = len(found) > 0
    evidence = f"找到: {found}" if found else f"未找到 {target_ids} 中的任何一个"
    return passed, evidence


def check_severity_groups(content: str) -> tuple[bool, int, str]:
    """检查报告是否按严重程度分组"""
    groups = {
        "严重": ["严重", "critical", "必须修复", "严重问题"],
        "警告": ["警告", "warning", "建议修复", "警告问题"],
        "建议": ["建议", "suggestion", "可选改进", "优化建议", "优化"],
    }
    found_groups = []
    for group_name, keywords in groups.items():
        if any(kw.lower() in content.lower() for kw in keywords):
            found_groups.append(group_name)
    passed = len(found_groups) >= 2
    evidence = f"找到 {len(found_groups)} 个严重程度分组: {found_groups}"
    return passed, len(found_groups), evidence


def check_report_header(content: str) -> tuple[bool, str]:
    """检查是否有审查报告的标题和基本结构"""
    header_keywords = ["审查报告", "审查类型", "总览", "review report"]
    found = [kw for kw in header_keywords if kw.lower() in content.lower()]
    passed = len(found) >= 2
    evidence = f"报告头部元素: {found}"
    return passed, evidence


def check_issue_count_summary(content: str) -> tuple[bool, str]:
    """检查是否有问题数量统计"""
    patterns = [
        r"共发现\s*\*{0,2}\d+\*{0,2}\s*个问题",
        r"发现了?\s*\*{0,2}\d+\*{0,2}\s*个问题",
        r"\d+\s*个问题",
        r"严重\s*\*{0,2}\d+\*{0,2}\s*个",
        r"问题总数",
        r"Total.*\d+.*issue",
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.extend(matches[:2])
    passed = len(found) > 0
    evidence = f"找到统计: {found[:3]}" if found else "未找到问题数量统计"
    return passed, evidence


def check_fix_suggestions(content: str) -> tuple[bool, str]:
    """检查问题是否包含修复建议"""
    fix_keywords = [
        "修复建议",
        "修复方案",
        "建议修改",
        "修改为",
        "改为",
        "应该改成",
        "可以改为",
        "替换为",
        "使用",
        "fix",
        "修复",
        "改进建议",
    ]
    found = [kw for kw in fix_keywords if kw.lower() in content.lower()]
    # 也检查是否有修改后的代码示例
    has_code = "```" in content
    passed = len(found) >= 2 or (len(found) >= 1 and has_code)
    evidence = f"修复建议关键词: {found[:5]}; 含代码示例: {has_code}"
    return passed, evidence


def check_review_type_label(
    content: str, expected_types: list[str]
) -> tuple[bool, str]:
    """检查审查类型标注"""
    found = [t for t in expected_types if t.lower() in content.lower()]
    passed = len(found) > 0
    evidence = (
        f"审查类型标注: {found}"
        if found
        else f"未找到预期的审查类型标注: {expected_types}"
    )
    return passed, evidence


# ─────────────────────────────────────────────
# 每个 eval 的专属检查逻辑
# ─────────────────────────────────────────────


def grade_eval_1(content: str) -> list[dict]:
    """python-code-review-basic: Python 代码审查基本能力"""
    results = []

    # A1-01: 加载了 python-review-checklist.md
    passed, evidence = check_checklist_loaded(content, "python-review-checklist")
    results.append(
        {
            "id": "A1-01",
            "text": "加载了 python-review-checklist.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-02: 报告模板结构
    passed, evidence = check_report_header(content)
    results.append(
        {
            "id": "A1-02",
            "text": "包含报告模板结构",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-03: 发现硬编码 API_KEY 并引用 PY-26 (或 PY-23~PY-28 范围)
    has_apikey_issue = any(
        kw in content.lower()
        for kw in ["api_key", "硬编码", "api key", "密钥", "sk-1234"]
    )
    passed_id, evidence_id = check_specific_ids_any(
        content, ["PY-26", "PY-23", "PY-25"]
    )
    passed = has_apikey_issue and passed_id
    if has_apikey_issue and not passed_id:
        # 发现了问题但未引用编号 — 给半分（在 compute_score 中需处理）
        passed = has_apikey_issue  # 至少发现了问题
    evidence = f"API_KEY 问题: {has_apikey_issue}; 编号引用: {evidence_id}"
    results.append(
        {
            "id": "A1-03",
            "text": "发现硬编码 API_KEY 问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-04: 发现 SQL 注入
    has_sqli = any(
        kw in content.lower()
        for kw in ["sql 注入", "sql注入", "sql injection", "字符串拼接 sql", "拼接sql"]
    )
    passed_id, evidence_id = check_specific_id(content, "PY-24")
    passed = has_sqli and passed_id
    if has_sqli and not passed_id:
        passed = has_sqli
    evidence = f"SQL 注入: {has_sqli}; PY-24: {evidence_id}"
    results.append(
        {
            "id": "A1-04",
            "text": "发现 SQL 注入问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-05: 发现裸 except / 吞掉异常
    has_except = any(
        kw in content.lower()
        for kw in [
            "裸 except",
            "except:",
            "bare except",
            "吞掉异常",
            "except pass",
            "空的 except",
            "吞掉了异常",
            "pass",
        ]
    )
    passed_id, evidence_id = check_specific_ids_any(content, ["PY-11", "PY-13"])
    passed = has_except and passed_id
    if has_except and not passed_id:
        passed = has_except
    evidence = f"异常处理问题: {has_except}; 编号: {evidence_id}"
    results.append(
        {
            "id": "A1-05",
            "text": "发现裸 except 或吞掉异常问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-06: 文件未用 with
    has_with_issue = any(
        kw in content.lower()
        for kw in ["with", "资源", "文件", "open(", "close", "finally"]
    )
    passed_id, evidence_id = check_specific_id(content, "PY-15")
    passed = has_with_issue and passed_id
    if has_with_issue and not passed_id:
        passed = has_with_issue
    evidence = f"文件管理问题: {has_with_issue}; PY-15: {evidence_id}"
    results.append(
        {
            "id": "A1-06",
            "text": "发现文件未用 with 管理",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-07: 按严重程度分组
    passed, _, evidence = check_severity_groups(content)
    results.append(
        {
            "id": "A1-07",
            "text": "按严重程度分组",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-08: 每个问题有修复建议
    passed, evidence = check_fix_suggestions(content)
    results.append(
        {"id": "A1-08", "text": "包含修复建议", "passed": passed, "evidence": evidence}
    )

    # A1-09: 总览有问题数量统计
    passed, evidence = check_issue_count_summary(content)
    results.append(
        {
            "id": "A1-09",
            "text": "总览有问题数量统计",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-10: SQL 注入和 API_KEY 被标为严重
    # 检查这些问题是否出现在"严重"分组下
    # 使用 \n## [^#] 来匹配下一个二级标题（避免匹配 ###）
    severe_section = ""
    severe_patterns = [
        r"严重问题.*?(?=\n## [^#]|\Z)",
        r"必须修复.*?(?=\n## [^#]|\Z)",
        r"Critical.*?(?=\n## [^#]|\Z)",
    ]
    for pat in severe_patterns:
        m = re.search(pat, content, re.DOTALL | re.IGNORECASE)
        if m:
            severe_section += m.group()
    if severe_section:
        has_sql_severe = any(
            kw in severe_section.lower() for kw in ["sql", "注入", "injection"]
        )
        has_key_severe = any(
            kw in severe_section.lower()
            for kw in ["api_key", "api key", "硬编码", "密钥"]
        )
        passed = has_sql_severe or has_key_severe
        evidence = f"严重分组中: SQL={has_sql_severe}, API_KEY={has_key_severe}"
    else:
        # 没有明确的严重分组，但可能用其他方式标注
        passed = any(kw in content.lower() for kw in ["严重", "critical"])
        evidence = "未找到明确的'严重问题'分组，仅检查关键词"
    results.append(
        {
            "id": "A1-10",
            "text": "SQL 注入和 API_KEY 被标为严重",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_2(content: str) -> list[dict]:
    """security-audit-api: 安全审计"""
    results = []

    # A2-01: 加载了 owasp-checklist.md
    passed, evidence = check_checklist_loaded(content, "owasp-checklist")
    results.append(
        {
            "id": "A2-01",
            "text": "加载了 owasp-checklist.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-02: SQL 注入 + SEC-09
    has_sqli = any(
        kw in content.lower() for kw in ["sql 注入", "sql注入", "sql injection"]
    )
    passed_id, evidence_id = check_specific_id(content, "SEC-09")
    passed = has_sqli and passed_id
    if has_sqli and not passed_id:
        passed = has_sqli
    evidence = f"SQL 注入: {has_sqli}; SEC-09: {evidence_id}"
    results.append(
        {"id": "A2-02", "text": "发现 SQL 注入", "passed": passed, "evidence": evidence}
    )

    # A2-03: 命令注入 + SEC-10
    has_cmdi = any(
        kw in content.lower()
        for kw in [
            "命令注入",
            "command injection",
            "shell=true",
            "subprocess",
            "os.system",
        ]
    )
    passed_id, evidence_id = check_specific_id(content, "SEC-10")
    passed = has_cmdi and passed_id
    if has_cmdi and not passed_id:
        passed = has_cmdi
    evidence = f"命令注入: {has_cmdi}; SEC-10: {evidence_id}"
    results.append(
        {"id": "A2-03", "text": "发现命令注入", "passed": passed, "evidence": evidence}
    )

    # A2-04: pickle 反序列化 + SEC-13 / SEC-29
    has_pickle = any(
        kw in content.lower() for kw in ["pickle", "反序列化", "deserialization"]
    )
    passed_id, evidence_id = check_specific_ids_any(content, ["SEC-13", "SEC-29"])
    passed = has_pickle and passed_id
    if has_pickle and not passed_id:
        passed = has_pickle
    evidence = f"Pickle 问题: {has_pickle}; 编号: {evidence_id}"
    results.append(
        {
            "id": "A2-04",
            "text": "发现 pickle 反序列化问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-05: 路径遍历 + SEC-12
    has_path = any(
        kw in content.lower()
        for kw in ["路径遍历", "path traversal", "目录遍历", "../", "文件读取"]
    )
    passed_id, evidence_id = check_specific_id(content, "SEC-12")
    passed = has_path and passed_id
    if has_path and not passed_id:
        passed = has_path
    evidence = f"路径遍历: {has_path}; SEC-12: {evidence_id}"
    results.append(
        {
            "id": "A2-05",
            "text": "发现路径遍历问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-06: debug 模式 / 信息泄露 + SEC-16~SEC-20
    has_debug = any(
        kw in content.lower()
        for kw in ["debug", "调试模式", "信息泄露", "错误信息", "泄露"]
    )
    passed_id, evidence_id = check_specific_ids_any(
        content, ["SEC-16", "SEC-17", "SEC-18", "SEC-19", "SEC-20"]
    )
    passed = has_debug and passed_id
    if has_debug and not passed_id:
        passed = has_debug
    evidence = f"Debug/泄露: {has_debug}; 编号: {evidence_id}"
    results.append(
        {
            "id": "A2-06",
            "text": "发现 debug 模式或信息泄露",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-07: 严重程度分组
    passed, _, evidence = check_severity_groups(content)
    results.append(
        {"id": "A2-07", "text": "严重程度分组", "passed": passed, "evidence": evidence}
    )

    # A2-08: 审查类型标注
    passed, evidence = check_review_type_label(
        content,
        ["安全审计", "安全审查", "安全检查", "security audit", "security review"],
    )
    results.append(
        {
            "id": "A2-08",
            "text": "审查类型标注为安全审计",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-09: 修复建议含代码
    passed, evidence = check_fix_suggestions(content)
    results.append(
        {
            "id": "A2-09",
            "text": "修复建议含代码",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-10: SQL 注入和命令注入标为严重
    severe_section = ""
    severe_patterns = [
        r"严重问题.*?(?=\n## [^#]|\Z)",
        r"必须修复.*?(?=\n## [^#]|\Z)",
        r"Critical.*?(?=\n## [^#]|\Z)",
    ]
    for pat in severe_patterns:
        m = re.search(pat, content, re.DOTALL | re.IGNORECASE)
        if m:
            severe_section += m.group()
    if severe_section:
        has_sql_s = any(kw in severe_section.lower() for kw in ["sql", "注入"])
        has_cmd_s = any(
            kw in severe_section.lower() for kw in ["命令", "command", "subprocess"]
        )
        passed = has_sql_s or has_cmd_s
        evidence = f"严重分组: SQL={has_sql_s}, 命令注入={has_cmd_s}"
    else:
        passed = any(kw in content.lower() for kw in ["严重", "critical"])
        evidence = "未找到明确分组，仅检查关键词"
    results.append(
        {
            "id": "A2-10",
            "text": "SQL/命令注入标为严重",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_3(content: str) -> list[dict]:
    """doc-quality-review: 文档质量审查"""
    results = []

    # A3-01: 加载了 doc-quality-checklist.md
    passed, evidence = check_checklist_loaded(content, "doc-quality-checklist")
    results.append(
        {
            "id": "A3-01",
            "text": "加载了 doc-quality-checklist.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-02: 缺少概述 + DOC-06
    has_overview = any(
        kw in content.lower()
        for kw in ["概述", "目标读者", "读者", "目的", "涵盖范围", "缺少介绍"]
    )
    passed_id, evidence_id = check_specific_id(content, "DOC-06")
    passed = has_overview and passed_id
    if has_overview and not passed_id:
        passed = has_overview
    evidence = f"概述问题: {has_overview}; DOC-06: {evidence_id}"
    results.append(
        {
            "id": "A3-02",
            "text": "发现缺少概述/读者",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-03: 缺少示例 + DOC-09
    has_example = any(
        kw in content.lower() for kw in ["示例", "example", "代码示例", "用法示例"]
    )
    passed_id, evidence_id = check_specific_id(content, "DOC-09")
    passed = has_example and passed_id
    if has_example and not passed_id:
        passed = has_example
    evidence = f"示例问题: {has_example}; DOC-09: {evidence_id}"
    results.append(
        {"id": "A3-03", "text": "发现缺少示例", "passed": passed, "evidence": evidence}
    )

    # A3-04: 链接失效 + DOC-18
    has_link = any(
        kw in content.lower()
        for kw in ["链接", "link", "失效", "dead link", "404", "已失效", "无效"]
    )
    passed_id, evidence_id = check_specific_id(content, "DOC-18")
    passed = has_link and passed_id
    if has_link and not passed_id:
        passed = has_link
    evidence = f"链接问题: {has_link}; DOC-18: {evidence_id}"
    results.append(
        {
            "id": "A3-04",
            "text": "发现链接失效问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-05: API 文档过于简略
    has_api = any(
        kw in content.lower()
        for kw in ["api", "参数", "说明", "简略", "过于简单", "缺少参数", "未说明"]
    )
    passed = has_api
    evidence = f"API 文档简略问题: {has_api}"
    results.append(
        {
            "id": "A3-05",
            "text": "发现 API 文档过于简略",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-06: 严重程度分组
    passed, _, evidence = check_severity_groups(content)
    results.append(
        {"id": "A3-06", "text": "严重程度分组", "passed": passed, "evidence": evidence}
    )

    # A3-07: 审查类型标注
    passed, evidence = check_review_type_label(
        content, ["文档质量", "文档审查", "文档检查", "doc quality", "document review"]
    )
    results.append(
        {
            "id": "A3-07",
            "text": "审查类型标注为文档审查",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-08: 修复建议
    passed, evidence = check_fix_suggestions(content)
    results.append(
        {"id": "A3-08", "text": "含修复建议", "passed": passed, "evidence": evidence}
    )

    # A3-09: 总览有问题统计
    passed, evidence = check_issue_count_summary(content)
    results.append(
        {
            "id": "A3-09",
            "text": "总览有问题统计",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-10: 引用了至少 4 个不同的 DOC-xx 编号
    passed, count, evidence = check_checklist_ids(content, "DOC", 4)
    results.append(
        {
            "id": "A3-10",
            "text": "引用了 >=4 个 DOC-xx",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_4(content: str) -> list[dict]:
    """auto-detect-review-type: 自动识别审查类型（Python + 安全）"""
    results = []

    # A4-01: 自动加载了 python-review-checklist.md
    passed, evidence = check_checklist_loaded(content, "python-review-checklist")
    results.append(
        {
            "id": "A4-01",
            "text": "加载了 python-review-checklist",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-02: 也加载了安全审查 (owasp) 或引用了 SEC-xx
    passed_owasp, evidence_owasp = check_checklist_loaded(content, "owasp-checklist")
    passed_sec, _, evidence_sec = check_checklist_ids(content, "SEC", 1)
    passed = passed_owasp or passed_sec
    evidence = f"OWASP 清单: {evidence_owasp}; SEC 编号: {evidence_sec}"
    results.append(
        {
            "id": "A4-02",
            "text": "识别出也需要安全审查",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-03: 发现 MD5 弱哈希
    has_md5 = any(
        kw in content.lower()
        for kw in [
            "md5",
            "弱哈希",
            "weak hash",
            "不安全的哈希",
            "bcrypt",
            "scrypt",
            "argon2",
        ]
    )
    passed = has_md5
    evidence = f"MD5 弱哈希问题: {has_md5}"
    results.append(
        {
            "id": "A4-03",
            "text": "发现 MD5 弱哈希问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-04: SQL 注入 + PY-24 / SEC-09
    has_sqli = any(
        kw in content.lower()
        for kw in ["sql 注入", "sql注入", "sql injection", "拼接sql", "字符串拼接"]
    )
    passed_id, evidence_id = check_specific_ids_any(content, ["PY-24", "SEC-09"])
    passed = has_sqli and passed_id
    if has_sqli and not passed_id:
        passed = has_sqli
    evidence = f"SQL 注入: {has_sqli}; 编号: {evidence_id}"
    results.append(
        {"id": "A4-04", "text": "发现 SQL 注入", "passed": passed, "evidence": evidence}
    )

    # A4-05: 明文密码写入日志
    has_log = any(
        kw in content.lower()
        for kw in [
            "明文密码",
            "密码写入日志",
            "password.*log",
            "日志.*密码",
            "敏感信息.*日志",
            "日志.*敏感",
            "密码.*明文",
        ]
    )
    # 也用正则检查
    if not has_log:
        has_log = bool(
            re.search(r"(密码|password).{0,20}(日志|log)", content, re.IGNORECASE)
        )
        if not has_log:
            has_log = bool(
                re.search(r"(日志|log).{0,20}(密码|password)", content, re.IGNORECASE)
            )
    passed = has_log
    evidence = f"明文密码写日志: {has_log}"
    results.append(
        {
            "id": "A4-05",
            "text": "发现明文密码写入日志",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-06: 文件未用 with + PY-15
    has_with = any(
        kw in content.lower() for kw in ["with", "open(", "资源", "文件", "close"]
    )
    passed_id, evidence_id = check_specific_id(content, "PY-15")
    passed = has_with and passed_id
    if has_with and not passed_id:
        passed = has_with
    evidence = f"文件管理: {has_with}; PY-15: {evidence_id}"
    results.append(
        {
            "id": "A4-06",
            "text": "发现文件未用 with",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-07: 严重程度分组
    passed, _, evidence = check_severity_groups(content)
    results.append(
        {"id": "A4-07", "text": "严重程度分组", "passed": passed, "evidence": evidence}
    )

    # A4-08: 修复建议
    passed, evidence = check_fix_suggestions(content)
    results.append(
        {"id": "A4-08", "text": "含修复建议", "passed": passed, "evidence": evidence}
    )

    # A4-09: 至少 3 个不同清单编号
    _, count_py, _ = check_checklist_ids(content, "PY", 0)
    _, count_sec, _ = check_checklist_ids(content, "SEC", 0)
    total_ids = count_py + count_sec
    passed = total_ids >= 3
    evidence = f"PY-xx: {count_py} 个, SEC-xx: {count_sec} 个, 总计: {total_ids}"
    results.append(
        {
            "id": "A4-09",
            "text": "引用 >=3 个清单编号",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_5(content: str) -> list[dict]:
    """unsupported-review-type: 不支持的语言审查"""
    results = []

    # A5-01: 告知没有 Rust 清单
    has_no_rust = any(
        kw in content.lower()
        for kw in [
            "没有 rust",
            "不支持 rust",
            "暂无 rust",
            "没有.*rust.*清单",
            "未找到.*rust",
            "rust.*清单.*不存在",
            "当前不支持",
            "尚未支持",
            "没有.*专用",
            "没有对应",
            "未包含 rust",
            "暂不支持",
        ]
    )
    if not has_no_rust:
        has_no_rust = bool(
            re.search(
                r"(没有|暂无|不支持|未找到).{0,15}(rust|Rust)", content, re.IGNORECASE
            )
        )
        if not has_no_rust:
            has_no_rust = bool(
                re.search(
                    r"(rust|Rust).{0,20}(没有|暂无|清单|不支持|不存在)",
                    content,
                    re.IGNORECASE,
                )
            )
    passed = has_no_rust
    evidence = f"告知无 Rust 清单: {has_no_rust}"
    results.append(
        {
            "id": "A5-01",
            "text": "告知无 Rust 清单",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-02: 列出当前支持的类型
    supported_types = ["python", "安全", "owasp", "文档", "doc"]
    found = [t for t in supported_types if t.lower() in content.lower()]
    passed = len(found) >= 2
    evidence = f"提到的支持类型: {found}"
    results.append(
        {
            "id": "A5-02",
            "text": "列出当前支持的类型",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-03: 建议创建 Rust 清单
    has_suggest = any(
        kw in content.lower()
        for kw in [
            "创建",
            "新建",
            "添加",
            "编写",
            "create",
            "references/",
            "增加.*清单",
            "新.*清单",
            "扩展",
        ]
    )
    passed = has_suggest
    evidence = f"建议创建清单: {has_suggest}"
    results.append(
        {
            "id": "A5-03",
            "text": "建议创建 Rust 清单",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-04: 从通用角度给出建议（如 unwrap）
    generic_advice = [
        "unwrap",
        "panic",
        "错误处理",
        "error handling",
        "expect",
        "Result",
        "Option",
        "?",
        "handle error",
    ]
    found = [kw for kw in generic_advice if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"通用建议关键词: {found}"
    results.append(
        {
            "id": "A5-04",
            "text": "给出通用代码建议",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-05: 建议有深度
    # 检查是否有具体解释而非一句话敷衍
    depth_indicators = len(content) > 300 and len(found) >= 1
    passed = depth_indicators
    evidence = f"内容长度: {len(content)} 字符; 通用建议词: {len(found)}"
    results.append(
        {"id": "A5-05", "text": "建议有深度", "passed": passed, "evidence": evidence}
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
            f"\n  得分: {result['score']['earned']}/{result['score']['possible']} ({result['score']['percentage']}%)"
        )

    # 计算总分
    total_earned = sum(g["score"]["earned"] for g in all_gradings)
    total_possible = sum(g["score"]["possible"] for g in all_gradings)
    total_pct = (
        round(total_earned / total_possible * 100, 1) if total_possible > 0 else 0
    )

    summary = {
        "skill_name": "skill-reviewer",
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
