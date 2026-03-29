#!/usr/bin/env python3
from __future__ import annotations

"""
skill-tool-wrapper 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 是某次测试运行的输出目录，结构如下:
    output_dir/
    ├── eval-1/          # 对应 evals.json 中 id=1 的测试用例
    │   ├── SKILL.md
    │   └── references/
    │       ├── conventions.md
    │       └── ...
    ├── eval-2/
    │   └── ...
    └── ...

也可以传入单个 eval 目录:
    python grade.py output_dir/eval-1

脚本会自动检测输出文件，执行可程序化验证的断言，
对需要人工判断的断言标记为 needs_review。

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


def collect_output_files(eval_dir: Path) -> dict[str, str]:
    """递归收集 eval 目录下所有文件内容，返回 {相对路径: 内容}"""
    files = {}
    for fpath in eval_dir.rglob("*"):
        if fpath.is_file():
            rel = str(fpath.relative_to(eval_dir))
            try:
                files[rel] = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                files[rel] = "<binary or unreadable>"
    return files


def find_file_by_name(
    files: dict[str, str], name: str
) -> tuple[str | None, str | None]:
    """在 files dict 中查找文件名匹配的文件（不区分目录层级）"""
    for path, content in files.items():
        if Path(path).name.lower() == name.lower():
            return path, content
    return None, None


def find_files_in_dir(files: dict[str, str], dirname: str) -> dict[str, str]:
    """查找某个目录下的所有文件"""
    result = {}
    for path, content in files.items():
        parts = Path(path).parts
        if dirname in parts:
            result[path] = content
    return result


# ─────────────────────────────────────────────
# 通用检查函数
# ─────────────────────────────────────────────


def check_yaml_frontmatter(content: str) -> tuple[bool, str]:
    """检查文件是否有合法的 YAML frontmatter"""
    if not content.strip().startswith("---"):
        return False, "文件不以 --- 开头，缺少 YAML frontmatter"
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, "YAML frontmatter 未正确闭合（缺少第二个 ---）"
    fm = parts[1]
    has_name = bool(re.search(r"^name\s*:", fm, re.MULTILINE))
    has_desc = bool(re.search(r"^description\s*:", fm, re.MULTILINE))
    if not has_name:
        return False, "frontmatter 缺少 name 字段"
    if not has_desc:
        return False, "frontmatter 缺少 description 字段"
    return True, "YAML frontmatter 结构正确，包含 name 和 description"


def check_trigger_words(content: str, words: list[str]) -> tuple[bool, str, list[str]]:
    """检查 description 中是否包含指定的触发词"""
    # 提取 frontmatter 中的 description
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, "无法提取 frontmatter", []
    fm = parts[1]
    found = []
    missing = []
    for w in words:
        if w.lower() in fm.lower():
            found.append(w)
        else:
            missing.append(w)
    passed = len(found) >= len(words) * 0.5  # 至少命中一半
    evidence = f"命中 {len(found)}/{len(words)} 个触发词。命中: {found}"
    if missing:
        evidence += f"；缺失: {missing}"
    return passed, evidence, found


def check_numbered_rules(content: str) -> tuple[bool, int, str]:
    """检查文件中是否有编号前缀的规则（如 FAPI-01、RC-01 等）"""
    pattern = r"###?\s+[A-Z]+-\d+"
    matches = re.findall(pattern, content)
    count = len(matches)
    passed = count >= 5
    evidence = f"找到 {count} 条编号规则"
    if matches[:5]:
        evidence += f"，示例: {[m.strip() for m in matches[:5]]}"
    return passed, count, evidence


def check_progressive_loading(content: str) -> tuple[bool, str]:
    """检查 SKILL.md 是否包含渐进式加载策略"""
    indicators = [
        r"\|\s*.*\s*\|\s*.*加载.*\|",  # 表格中有"加载"
        r"按需",
        r"渐进",
        r"progressive",
        r"场景.*加载",
        r"加载.*策略",
        r"when.*load",
    ]
    found = []
    for ind in indicators:
        if re.search(ind, content, re.IGNORECASE):
            found.append(ind)
    # 也检查是否有条件加载的表格
    has_table = bool(re.search(r"\|.*\|.*\|", content))
    passed = len(found) >= 2 or (len(found) >= 1 and has_table)
    evidence = f"找到 {len(found)} 个渐进加载指标"
    if found:
        evidence += f"，匹配模式: {found[:3]}"
    return passed, evidence


def check_min_rules_count(content: str, min_count: int) -> tuple[bool, int, str]:
    """检查文件中规则条数是否达到最低要求"""
    # 匹配 ### 开头的规则条目
    rules = re.findall(r"^###\s+.+", content, re.MULTILINE)
    count = len(rules)
    passed = count >= min_count
    evidence = f"找到 {count} 条规则（最低要求 {min_count}）"
    return passed, count, evidence


def check_code_examples(content: str, lang: str | None = None) -> tuple[bool, int, str]:
    """检查文件中是否有代码示例"""
    if lang:
        pattern = rf"```{lang}"
    else:
        pattern = r"```\w+"
    matches = re.findall(pattern, content)
    count = len(matches)
    passed = count >= 2
    evidence = f"找到 {count} 个代码块"
    if lang:
        evidence += f"（语言: {lang}）"
    return passed, count, evidence


def check_content_keywords(
    content: str, keywords: list[str], min_hits: int
) -> tuple[bool, str]:
    """检查内容是否包含特定领域关键词"""
    found = []
    for kw in keywords:
        if kw.lower() in content.lower():
            found.append(kw)
    passed = len(found) >= min_hits
    evidence = f"命中 {len(found)}/{len(keywords)} 个关键词: {found}"
    return passed, evidence


def check_custom_rules_present(
    content: str, rules: list[str]
) -> tuple[bool, str, list[str]]:
    """检查用户自定义规则是否被纳入"""
    found = []
    missing = []
    for rule in rules:
        if rule.lower() in content.lower():
            found.append(rule)
        else:
            missing.append(rule)
    passed = len(found) >= len(rules) * 0.75  # 至少命中 75%
    evidence = f"命中 {len(found)}/{len(rules)} 条自定义规则。命中: {found}"
    if missing:
        evidence += f"；缺失: {missing}"
    return passed, evidence, found


# ─────────────────────────────────────────────
# 每个 eval 的专属检查逻辑
# ─────────────────────────────────────────────


def grade_eval_1(files: dict[str, str]) -> list[dict]:
    """basic-create-react-wrapper"""
    results = []
    _, skill_md = find_file_by_name(files, "SKILL.md")
    ref_files = find_files_in_dir(files, "references")
    _, conv_md = find_file_by_name(files, "conventions.md")

    # A1-01: YAML frontmatter
    if skill_md:
        passed, evidence = check_yaml_frontmatter(skill_md)
    else:
        passed, evidence = False, "未找到 SKILL.md 文件"
    results.append(
        {
            "id": "A1-01",
            "text": "SKILL.md 有正确的 YAML frontmatter",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-02: React 触发词
    if skill_md:
        passed, evidence, _ = check_trigger_words(
            skill_md, ["React", "组件", "component", "前端", "TypeScript", "frontend"]
        )
    else:
        passed, evidence = False, "未找到 SKILL.md"
    results.append(
        {
            "id": "A1-02",
            "text": "description 包含 React 触发词",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-03: references/ 下至少有 conventions.md 和 best-practices.md
    has_conv = any("conventions" in p.lower() for p in ref_files)
    has_bp = any(
        "best-practices" in p.lower() or "best_practices" in p.lower()
        for p in ref_files
    )
    passed = has_conv and has_bp
    evidence = f"references/ 下文件: {list(ref_files.keys())}。conventions={has_conv}, best-practices={has_bp}"
    results.append(
        {
            "id": "A1-03",
            "text": "包含 conventions.md 和 best-practices.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-04: 编号前缀
    if conv_md:
        passed, count, evidence = check_numbered_rules(conv_md)
    else:
        # 尝试在所有 ref 文件中查找
        all_ref_content = "\n".join(ref_files.values())
        passed, count, evidence = check_numbered_rules(all_ref_content)
    results.append(
        {
            "id": "A1-04",
            "text": "规则有编号前缀",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-05: 至少 10 条规则
    if conv_md:
        passed, count, evidence = check_min_rules_count(conv_md, 10)
    else:
        passed, count, evidence = False, 0, "未找到 conventions.md"
    results.append(
        {
            "id": "A1-05",
            "text": "conventions.md 包含至少 10 条规则",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-06: 渐进式加载
    if skill_md:
        passed, evidence = check_progressive_loading(skill_md)
    else:
        passed, evidence = False, "未找到 SKILL.md"
    results.append(
        {
            "id": "A1-06",
            "text": "包含渐进式加载策略",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-07: React+TS 相关内容（needs_review 但可做初步检查）
    all_content = "\n".join(files.values())
    react_kw = [
        "useState",
        "useEffect",
        "component",
        "props",
        "JSX",
        "TSX",
        "interface",
        "React.FC",
    ]
    passed, evidence = check_content_keywords(all_content, react_kw, 3)
    results.append(
        {
            "id": "A1-07",
            "text": "内容与 React+TypeScript 相关",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-08: 正确/错误示例
    if conv_md:
        has_correct = (
            "正确" in conv_md
            or "correct" in conv_md.lower()
            or "good" in conv_md.lower()
            or "✅" in conv_md
        )
        has_wrong = (
            "错误" in conv_md
            or "wrong" in conv_md.lower()
            or "bad" in conv_md.lower()
            or "❌" in conv_md
            or "避免" in conv_md
        )
        _, code_count, _ = check_code_examples(conv_md)
        passed = (has_correct or has_wrong) and code_count >= 2
        evidence = (
            f"正确示例={has_correct}, 错误示例={has_wrong}, 代码块数={code_count}"
        )
    else:
        passed, evidence = False, "未找到 conventions.md"
    results.append(
        {
            "id": "A1-08",
            "text": "包含正确/错误代码示例",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_2(files: dict[str, str]) -> list[dict]:
    """complex-django-wrapper-with-team-rules"""
    results = []
    _, skill_md = find_file_by_name(files, "SKILL.md")
    ref_files = find_files_in_dir(files, "references")
    _, conv_md = find_file_by_name(files, "conventions.md")

    # A2-01: 4 条自定义团队规则
    search_content = (
        conv_md or "\n".join(ref_files.values()) or "\n".join(files.values())
    )
    custom_rules = ["ViewSet", "BaseSerializer", "permissions.py", "DefaultRouter"]
    passed, evidence, _ = check_custom_rules_present(search_content, custom_rules)
    results.append(
        {
            "id": "A2-01",
            "text": "包含 4 条自定义团队规则",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-02: 自定义规则被区分标记（needs_review 但做初步检查）
    if search_content:
        has_team = any(
            kw in search_content for kw in ["团队", "自定义", "team", "custom", "内部"]
        )
        passed = has_team
        evidence = f"找到团队/自定义标记: {has_team}"
    else:
        passed, evidence = False, "无内容可检查"
    results.append(
        {
            "id": "A2-02",
            "text": "自定义规则被区分标记",
            "passed": passed,
            "evidence": evidence + " (needs_review)",
        }
    )

    # A2-03: 触发词
    if skill_md:
        passed, evidence, _ = check_trigger_words(
            skill_md, ["Django", "DRF", "REST Framework", "django"]
        )
    else:
        passed, evidence = False, "未找到 SKILL.md"
    results.append(
        {
            "id": "A2-03",
            "text": "description 包含 Django/DRF 触发词",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-04: DRF 特有实践
    bp_files = {
        k: v
        for k, v in ref_files.items()
        if "best" in k.lower() or "practice" in k.lower()
    }
    bp_content = "\n".join(bp_files.values()) if bp_files else "\n".join(files.values())
    drf_kw = [
        "分页",
        "pagination",
        "throttl",
        "filter",
        "serializer",
        "permission",
        "viewset",
    ]
    passed, evidence = check_content_keywords(bp_content, drf_kw, 3)
    results.append(
        {
            "id": "A2-04",
            "text": "best-practices 包含 DRF 特有实践",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-05: 编号前缀
    all_ref = "\n".join(ref_files.values()) if ref_files else "\n".join(files.values())
    passed, count, evidence = check_numbered_rules(all_ref)
    results.append(
        {
            "id": "A2-05",
            "text": "规则有编号前缀",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-06: 渐进式加载
    if skill_md:
        passed, evidence = check_progressive_loading(skill_md)
    else:
        passed, evidence = False, "未找到 SKILL.md"
    results.append(
        {
            "id": "A2-06",
            "text": "包含渐进式加载策略",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-07: 自定义规则有代码示例
    if conv_md:
        has_viewset_code = "ViewSet" in conv_md and "```" in conv_md
        _, code_count, _ = check_code_examples(conv_md, "python")
        passed = has_viewset_code and code_count >= 2
        evidence = f"ViewSet+代码块={has_viewset_code}, python 代码块数={code_count}"
    else:
        passed, evidence = False, "未找到 conventions.md"
    results.append(
        {
            "id": "A2-07",
            "text": "自定义规则有代码示例",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-08: 目录结构
    has_skill = any(Path(p).name.lower() == "skill.md" for p in files)
    has_refs = bool(ref_files)
    passed = has_skill and has_refs and len(ref_files) >= 2
    evidence = f"SKILL.md={has_skill}, references/文件数={len(ref_files)}"
    results.append(
        {
            "id": "A2-08",
            "text": "目录结构符合模板",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_3(files: dict[str, str]) -> list[dict]:
    """non-code-tool-wrapper-terraform"""
    results = []
    _, skill_md = find_file_by_name(files, "SKILL.md")
    ref_files = find_files_in_dir(files, "references")
    _, conv_md = find_file_by_name(files, "conventions.md")
    all_content = "\n".join(files.values())

    # A3-01: 非编程语言适配
    tf_kw = [
        "terraform",
        "resource",
        "module",
        "provider",
        "variable",
        "output",
        "state",
        "backend",
        "hcl",
        ".tf",
    ]
    passed, evidence = check_content_keywords(all_content, tf_kw, 4)
    results.append(
        {
            "id": "A3-01",
            "text": "为 Terraform/HCL 正确创建 wrapper",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-02: 4 条自定义规则
    custom_rules = ["modules/", "description", "S3", "plan"]
    search = conv_md or all_content
    passed, evidence, _ = check_custom_rules_present(search, custom_rules)
    results.append(
        {
            "id": "A3-02",
            "text": "包含 4 条自定义规则",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-03: Terraform 特有实践
    bp_kw = [
        "module",
        "workspace",
        "drift",
        "lock",
        "版本",
        "version",
        "remote",
        "backend",
        "plan",
    ]
    bp_files = {
        k: v
        for k, v in ref_files.items()
        if "best" in k.lower() or "practice" in k.lower()
    }
    bp_content = "\n".join(bp_files.values()) if bp_files else all_content
    passed, evidence = check_content_keywords(bp_content, bp_kw, 3)
    results.append(
        {
            "id": "A3-03",
            "text": "best-practices 包含 Terraform 特有实践",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-04: 编号前缀
    ref_content = "\n".join(ref_files.values()) if ref_files else all_content
    passed, count, evidence = check_numbered_rules(ref_content)
    results.append(
        {
            "id": "A3-04",
            "text": "规则有编号前缀",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-05: 触发词
    if skill_md:
        passed, evidence, _ = check_trigger_words(
            skill_md, ["Terraform", "IaC", "基础设施", "terraform", "infrastructure"]
        )
    else:
        passed, evidence = False, "未找到 SKILL.md"
    results.append(
        {
            "id": "A3-05",
            "text": "description 包含 Terraform/IaC 触发词",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-06: HCL 代码示例
    _, hcl_count, _ = check_code_examples(all_content, "hcl")
    _, tf_count, _ = check_code_examples(all_content, "terraform")
    total = hcl_count + tf_count
    passed = total >= 2
    evidence = f"HCL 代码块={hcl_count}, terraform 代码块={tf_count}, 总计={total}"
    results.append(
        {
            "id": "A3-06",
            "text": "代码示例使用 HCL 语法",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-07: 渐进式加载
    if skill_md:
        passed, evidence = check_progressive_loading(skill_md)
    else:
        passed, evidence = False, "未找到 SKILL.md"
    results.append(
        {
            "id": "A3-07",
            "text": "包含渐进式加载策略",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-08: 目录结构
    has_skill = any(Path(p).name.lower() == "skill.md" for p in files)
    has_refs = bool(ref_files)
    passed = has_skill and has_refs
    evidence = f"SKILL.md={has_skill}, references/文件数={len(ref_files)}"
    results.append(
        {
            "id": "A3-08",
            "text": "目录结构符合模板",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_4(files: dict[str, str]) -> list[dict]:
    """ambiguous-request-no-explicit-wrapper"""
    results = []
    _, skill_md = find_file_by_name(files, "SKILL.md")
    ref_files = find_files_in_dir(files, "references")
    _, conv_md = find_file_by_name(files, "conventions.md")
    all_content = "\n".join(files.values())

    # A4-01: 推荐 tool-wrapper 模式（needs_review — 这个更多体现在对话中而非文件中）
    tw_kw = [
        "tool-wrapper",
        "tool wrapper",
        "封装",
        "wrapper",
        "skill 模式",
        "按需加载",
    ]
    passed, evidence = check_content_keywords(all_content, tw_kw, 1)
    results.append(
        {
            "id": "A4-01",
            "text": "识别需求并推荐 tool-wrapper 模式",
            "passed": passed,
            "evidence": evidence + " (needs_review: 需人工确认对话中是否有推荐)",
        }
    )

    # A4-02: 生成了 Go wrapper 结构
    has_skill = any(Path(p).name.lower() == "skill.md" for p in files)
    passed = has_skill
    evidence = f"找到 SKILL.md={has_skill}"
    results.append(
        {
            "id": "A4-02",
            "text": "生成了 Go wrapper 骨架",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-03: 4 条自定义规则
    custom_rules = ["pkg/errors", "zap", "ResponseWriter", "viper"]
    search = conv_md or all_content
    passed, evidence, _ = check_custom_rules_present(search, custom_rules)
    results.append(
        {
            "id": "A4-03",
            "text": "包含 4 条自定义规则",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-04: 编号前缀
    ref_content = "\n".join(ref_files.values()) if ref_files else all_content
    passed, count, evidence = check_numbered_rules(ref_content)
    results.append(
        {
            "id": "A4-04",
            "text": "规则有编号前缀",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-05: 解释 tool-wrapper 优势（needs_review）
    adv_kw = ["按需加载", "上下文", "context", ".cursorrules", "CLAUDE.md", "token"]
    passed, evidence = check_content_keywords(all_content, adv_kw, 2)
    results.append(
        {
            "id": "A4-05",
            "text": "解释了 tool-wrapper 模式优势",
            "passed": passed,
            "evidence": evidence + " (needs_review)",
        }
    )

    # A4-06: Go 代码语法正确（基础检查）
    _, go_count, _ = check_code_examples(all_content, "go")
    passed = go_count >= 2
    evidence = f"Go 代码块数={go_count}"
    results.append(
        {
            "id": "A4-06",
            "text": "Go 代码示例存在",
            "passed": passed,
            "evidence": evidence + " (needs_review: 语法正确性需人工确认)",
        }
    )

    return results


def grade_eval_5(files: dict[str, str]) -> list[dict]:
    """large-scope-split-guidance"""
    results = []
    _, skill_md = find_file_by_name(files, "SKILL.md")
    ref_files = find_files_in_dir(files, "references")
    all_content = "\n".join(files.values())

    # A5-01: 推荐拆分
    split_kw = [
        "拆分",
        "split",
        "按服务",
        "per service",
        "单独文件",
        "separate",
        "多个文件",
    ]
    passed, evidence = check_content_keywords(all_content, split_kw, 2)
    results.append(
        {"id": "A5-01", "text": "推荐拆分文件", "passed": passed, "evidence": evidence}
    )

    # A5-02: 具体拆分方案
    aws_services = [
        "vpc",
        "lambda",
        "dynamodb",
        "iam",
        "cloudfront",
        "s3",
        "step.function",
        "api.gateway",
    ]
    found_services = []
    for svc in aws_services:
        # 查找是否有以服务命名的文件或章节
        if (
            re.search(rf"conventions[-_]?{svc}", all_content, re.IGNORECASE)
            or re.search(rf"best[-_]?practices[-_]?{svc}", all_content, re.IGNORECASE)
            or re.search(rf"[-_]{svc}\.md", all_content, re.IGNORECASE)
        ):
            found_services.append(svc)
    passed = len(found_services) >= 3
    evidence = f"找到 {len(found_services)} 个服务的拆分文件/方案: {found_services}"
    results.append(
        {
            "id": "A5-02",
            "text": "给出具体文件拆分方案",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-03: 按需加载策略
    if skill_md:
        passed, evidence = check_progressive_loading(skill_md)
    else:
        passed, evidence = check_progressive_loading(all_content)
    results.append(
        {
            "id": "A5-03",
            "text": "加载策略为按需加载",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-04: 至少 2 个服务的示范内容
    service_content_count = 0
    for svc in aws_services:
        if re.search(rf"###?\s+.*{svc}", all_content, re.IGNORECASE):
            service_content_count += 1
    passed = service_content_count >= 2
    evidence = f"找到 {service_content_count} 个服务有实际规则内容"
    results.append(
        {
            "id": "A5-04",
            "text": "至少 2 个服务有示范内容",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-05: 触发词
    if skill_md:
        passed, evidence, _ = check_trigger_words(
            skill_md, ["AWS CDK", "CDK", "基础设施", "infrastructure", "AWS"]
        )
    else:
        passed, evidence, _ = check_trigger_words(
            all_content, ["AWS CDK", "CDK", "基础设施", "infrastructure", "AWS"]
        )
    results.append(
        {
            "id": "A5-05",
            "text": "description 包含 AWS CDK 触发词",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-06: 提到 300 行 / 目录索引
    has_300 = "300" in all_content
    has_toc = any(
        kw in all_content for kw in ["目录", "table of contents", "TOC", "索引"]
    )
    passed = has_300 or has_toc
    evidence = f"提到 300 行限制={has_300}, 提到目录/索引={has_toc}"
    results.append(
        {
            "id": "A5-06",
            "text": "提到大文件需要目录索引",
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
    files = collect_output_files(eval_dir)
    if not files:
        return {
            "eval_id": eval_id,
            "status": "error",
            "message": f"目录为空或不存在: {eval_dir}",
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

    results = grader(files)
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
    if (target / "SKILL.md").exists() or (target / "references").exists():
        # 单个 eval 目录，尝试从目录名提取 eval_id
        match = re.search(r"eval-?(\d+)", target.name)
        eval_id = int(match.group(1)) if match else 1
        eval_dirs = [(target, eval_id)]
    else:
        # 扫描子目录
        for subdir in sorted(target.iterdir()):
            if subdir.is_dir():
                match = re.search(r"eval-?(\d+)", subdir.name)
                if match:
                    eval_dirs.append((subdir, int(match.group(1))))

    if not eval_dirs:
        print(f"错误: 未在 {target} 下找到可评分的目录")
        print("目录结构应为 eval-1/, eval-2/, ... 或直接包含 SKILL.md 的目录")
        sys.exit(1)

    for eval_dir, eval_id in eval_dirs:
        print(f"\n{'=' * 60}")
        print(f"评分: eval-{eval_id} ({eval_dir.name})")
        print(f"{'=' * 60}")

        result = grade_single_eval(eval_dir, eval_id, evals_data)
        all_gradings.append(result)

        # 打印结果
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
        "skill_name": "skill-tool-wrapper",
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
