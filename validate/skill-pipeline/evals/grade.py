#!/usr/bin/env python3
from __future__ import annotations

"""
skill-pipeline 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 response.md（模型输出的文本）和可选的其他文件。

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


def collect_files(eval_dir: Path) -> dict[str, str]:
    """收集 eval 目录下的所有文件"""
    files = {}
    for fpath in eval_dir.rglob("*"):
        if fpath.is_file():
            rel = str(fpath.relative_to(eval_dir))
            try:
                files[rel] = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                files[rel] = "<binary>"
    return files


# ─────────────────────────────────────────────
# 通用检查函数
# ─────────────────────────────────────────────


def check_pipeline_loaded(content: str, pipeline_name: str) -> tuple[bool, str]:
    """检查是否加载了指定的流水线定义"""
    indicators = [
        pipeline_name.lower(),
        pipeline_name.replace("-", " ").lower(),
        pipeline_name.replace("-pipeline", "").lower(),
    ]
    found = [ind for ind in indicators if ind in content.lower()]
    passed = len(found) > 0
    evidence = (
        f"找到流水线引用: {found}" if found else f"未找到 {pipeline_name} 相关引用"
    )
    return passed, evidence


def check_progress_indicator(content: str) -> tuple[bool, str]:
    """检查是否有进度指示（如 [阶段 1/5]、[Stage 1/5]、第1步/共5步 等）"""
    patterns = [
        r"\[阶段\s*\d+\s*/\s*\d+\]",
        r"\[Stage\s*\d+\s*/\s*\d+\]",
        r"\[Step\s*\d+\s*/\s*\d+\]",
        r"第\s*\d+\s*[步阶段]",
        r"阶段\s*\d+",
        r"Stage\s*\d+",
        r"Step\s*\d+\s*[:/of]",
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.extend(matches[:3])
    passed = len(found) > 0
    evidence = f"找到进度指示: {found[:5]}" if found else "未找到进度指示"
    return passed, evidence


def check_checkpoint_pause(content: str) -> tuple[bool, str]:
    """检查是否在检查点暂停（有确认请求 + 未继续到后续阶段的内容）"""
    confirm_keywords = [
        "请确认",
        "确认后",
        "继续吗",
        "回复继续",
        "请回复",
        "下一步",
        "进入下一",
        "通过后",
        "确认无误",
        "please confirm",
        "proceed",
        "continue",
        "等待您",
        "等待确认",
        "请查看",
        "是否继续",
    ]
    found = [kw for kw in confirm_keywords if kw in content.lower()]
    passed = len(found) > 0
    evidence = f"找到确认请求词: {found}" if found else "未找到确认请求"
    return passed, evidence


def check_not_completed_all(
    content: str, final_keywords: list[str]
) -> tuple[bool, str]:
    """检查是否没有一次性完成所有阶段（应停在检查点）"""
    final_found = [kw for kw in final_keywords if kw.lower() in content.lower()]
    # 如果包含最终阶段的关键词，说明没有在检查点暂停
    passed = len(final_found) == 0
    if passed:
        evidence = "正确停在了检查点，未执行到最终阶段"
    else:
        evidence = f"可能跳过了检查点，找到最终阶段关键词: {final_found}"
    return passed, evidence


def check_content_keywords(
    content: str, keywords: list[str], min_hits: int
) -> tuple[bool, str]:
    """检查内容是否包含特定关键词"""
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= min_hits
    evidence = f"命中 {len(found)}/{len(keywords)} 个关键词: {found}"
    return passed, evidence


def check_stage_structure(content: str, expected_stages: list[str]) -> tuple[bool, str]:
    """检查是否包含预期的阶段"""
    found = [s for s in expected_stages if s.lower() in content.lower()]
    passed = len(found) >= len(expected_stages) * 0.6
    evidence = f"找到 {len(found)}/{len(expected_stages)} 个预期阶段: {found}"
    return passed, evidence


def check_file_exists(files: dict[str, str], pattern: str) -> tuple[bool, str]:
    """检查是否存在匹配模式的文件"""
    matches = [f for f in files if re.search(pattern, f, re.IGNORECASE)]
    passed = len(matches) > 0
    evidence = f"匹配的文件: {matches}" if matches else f"未找到匹配 '{pattern}' 的文件"
    return passed, evidence


def check_checkpoint_markers(content: str) -> tuple[bool, int, str]:
    """检查是否有 [CHECKPOINT] 标记"""
    matches = re.findall(r"\[CHECKPOINT\]", content, re.IGNORECASE)
    count = len(matches)
    passed = count >= 2
    evidence = f"找到 {count} 个 [CHECKPOINT] 标记"
    return passed, count, evidence


def check_stage_fields(content: str) -> tuple[bool, str]:
    """检查阶段定义是否有目标/操作/输出等字段"""
    fields = ["目标", "操作", "输出", "输入", "检查要点"]
    found = [
        f
        for f in fields
        if f"**{f}**" in content or f"- **{f}" in content or f"{f}:" in content
    ]
    passed = len(found) >= 3
    evidence = f"找到 {len(found)}/{len(fields)} 个阶段字段: {found}"
    return passed, evidence


# ─────────────────────────────────────────────
# 每个 eval 的专属检查逻辑
# ─────────────────────────────────────────────


def grade_eval_1(content: str, files: dict[str, str]) -> list[dict]:
    """doc-pipeline-basic: 文档生成流水线基本执行"""
    results = []

    # A1-01: 加载了 doc-pipeline.md
    passed, evidence = check_pipeline_loaded(content, "doc-pipeline")
    results.append(
        {
            "id": "A1-01",
            "text": "加载了 doc-pipeline.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-02: 进度指示
    passed, evidence = check_progress_indicator(content)
    results.append(
        {"id": "A1-02", "text": "包含进度指示", "passed": passed, "evidence": evidence}
    )

    # A1-03: 在阶段 1 后暂停
    passed, evidence = check_not_completed_all(
        content, ["内容撰写", "质量审查", "修订定稿", "定稿", "完整文档", "最终版本"]
    )
    results.append(
        {
            "id": "A1-03",
            "text": "在阶段 1 后暂停",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-04: 输出了需求理解摘要
    passed, evidence = check_content_keywords(
        content, ["文档类型", "受众", "技术设计", "权限系统", "读者", "格式"], 2
    )
    results.append(
        {
            "id": "A1-04",
            "text": "输出了需求理解摘要",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-05: 确认请求
    passed, evidence = check_checkpoint_pause(content)
    results.append(
        {"id": "A1-05", "text": "包含确认请求", "passed": passed, "evidence": evidence}
    )

    # A1-06: 没有一次性生成完整文档
    has_full_doc = any(
        kw in content
        for kw in [
            "## 架构设计",
            "## 详细设计",
            "## 部署指南",
            "```python\n",
            "```typescript\n",
        ]
    )
    # 这里指的是文档正文内容，不是流水线说明
    # 用一个更宽松的判断：如果同时出现大量代码和详细设计，说明已经进入了撰写阶段
    doc_sections = sum(
        1
        for kw in ["架构设计", "详细设计", "部署指南", "运维指南", "接口定义"]
        if kw in content
    )
    passed = doc_sections < 3
    evidence = f"文档正文章节数={doc_sections}。{'正确停在检查点' if passed else '可能已经开始撰写文档'}"
    results.append(
        {
            "id": "A1-06",
            "text": "没有一次性生成完整文档",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A1-07: 与用户权限系统相关
    passed, evidence = check_content_keywords(
        content, ["权限", "用户", "permission", "access", "RBAC", "角色", "认证"], 2
    )
    results.append(
        {
            "id": "A1-07",
            "text": "与用户权限系统相关",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_2(content: str, files: dict[str, str]) -> list[dict]:
    """release-pipeline-npm: npm 版本发布流水线"""
    results = []

    # A2-01: 加载了 release-pipeline.md
    passed, evidence = check_pipeline_loaded(content, "release-pipeline")
    results.append(
        {
            "id": "A2-01",
            "text": "加载了 release-pipeline.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-02: 没有直接执行 npm publish
    passed, evidence = check_not_completed_all(
        content, ["npm publish", "发布成功", "已发布到", "Published", "已推送"]
    )
    results.append(
        {
            "id": "A2-02",
            "text": "没有直接执行 npm publish",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-03: 输出了检查结果
    passed, evidence = check_content_keywords(
        content,
        ["分支", "branch", "测试", "test", "检查", "check", "git status", "lint"],
        2,
    )
    results.append(
        {
            "id": "A2-03",
            "text": "输出了检查结果",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-04: 进度指示
    passed, evidence = check_progress_indicator(content)
    results.append(
        {"id": "A2-04", "text": "包含进度指示", "passed": passed, "evidence": evidence}
    )

    # A2-05: 版本号建议
    passed, evidence = check_content_keywords(
        content, ["1.3.0", "minor", "新功能", "feature"], 1
    )
    results.append(
        {
            "id": "A2-05",
            "text": "提到版本号建议",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-06: npm 相关
    passed, evidence = check_content_keywords(
        content, ["npm", "package.json", "publish", "node"], 1
    )
    results.append(
        {
            "id": "A2-06",
            "text": "提及 npm 相关内容",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A2-07: 确认请求
    passed, evidence = check_checkpoint_pause(content)
    results.append(
        {"id": "A2-07", "text": "包含确认请求", "passed": passed, "evidence": evidence}
    )

    return results


def grade_eval_3(content: str, files: dict[str, str]) -> list[dict]:
    """data-pipeline-csv-cleaning: 数据清洗流水线"""
    results = []

    # A3-01: 加载了 data-pipeline.md
    passed, evidence = check_pipeline_loaded(content, "data-pipeline")
    results.append(
        {
            "id": "A3-01",
            "text": "加载了 data-pipeline.md",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-02: 先分析不是直接清洗
    # 如果直接包含清洗代码或pandas处理，说明跳过了分析
    analysis_kw = [
        "分析",
        "analysis",
        "概览",
        "overview",
        "字段",
        "记录数",
        "空值",
        "数据源",
    ]
    passed, evidence = check_content_keywords(content, analysis_kw, 3)
    results.append(
        {
            "id": "A3-02",
            "text": "先做数据源分析",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-03: 检查点暂停
    passed_pause, evidence_pause = check_checkpoint_pause(content)
    passed_stop, evidence_stop = check_not_completed_all(
        content, ["清洗完成", "处理完成", "输出交付", "处理汇总报告", "验证报告"]
    )
    passed = passed_pause and passed_stop
    evidence = f"暂停确认: {evidence_pause}; 停止状态: {evidence_stop}"
    results.append(
        {
            "id": "A3-03",
            "text": "在阶段 1 检查点暂停",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-04: 涉及三个问题
    passed, evidence = check_content_keywords(
        content, ["重复", "duplicate", "日期", "date", "邮箱", "email", "格式"], 3
    )
    results.append(
        {
            "id": "A3-04",
            "text": "分析涉及三个数据问题",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A3-05: 进度指示
    passed, evidence = check_progress_indicator(content)
    results.append(
        {"id": "A3-05", "text": "包含进度指示", "passed": passed, "evidence": evidence}
    )

    # A3-06: 提到备份
    passed, evidence = check_content_keywords(
        content, ["备份", "backup", "复制", "copy", "snapshot"], 1
    )
    results.append(
        {"id": "A3-06", "text": "提到备份建议", "passed": passed, "evidence": evidence}
    )

    # A3-07: 确认请求
    passed, evidence = check_checkpoint_pause(content)
    results.append(
        {"id": "A3-07", "text": "包含确认请求", "passed": passed, "evidence": evidence}
    )

    return results


def grade_eval_4(content: str, files: dict[str, str]) -> list[dict]:
    """custom-pipeline-creation: 创建自定义流水线"""
    results = []

    # A4-01: 生成了流水线定义文件
    passed, evidence = check_file_exists(files, r"pipeline\.md$")
    if not passed:
        # 也检查内容中是否有完整的流水线定义格式
        has_stages = content.count("### 阶段") >= 4
        if has_stages:
            passed = True
            evidence = "内容中包含完整的流水线定义格式（>= 4 个阶段定义）"
    results.append(
        {
            "id": "A4-01",
            "text": "生成了流水线定义文件",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-02: 包含 6 个阶段
    stages = ["合同", "账号", "权限", "数据", "培训", "上线"]
    passed, evidence = check_stage_structure(content, stages)
    results.append(
        {"id": "A4-02", "text": "包含 6 个阶段", "passed": passed, "evidence": evidence}
    )

    # A4-03: 合理的 CHECKPOINT 标记
    passed, count, evidence = check_checkpoint_markers(content)
    # 检查特定阶段是否有检查点
    contract_cp = bool(
        re.search(r"合同.*\[CHECKPOINT\]|签署.*\[CHECKPOINT\]", content, re.IGNORECASE)
    )
    launch_cp = bool(
        re.search(r"上线.*\[CHECKPOINT\]|正式.*\[CHECKPOINT\]", content, re.IGNORECASE)
    )
    passed = count >= 2 and (contract_cp or launch_cp)
    evidence += f"; 合同阶段检查点={contract_cp}, 上线阶段检查点={launch_cp}"
    results.append(
        {
            "id": "A4-03",
            "text": "合理标记了 CHECKPOINT",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-04: 阶段有完整字段
    passed, evidence = check_stage_fields(content)
    results.append(
        {
            "id": "A4-04",
            "text": "阶段有目标/操作/输出等字段",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-05: 适用场景
    passed, evidence = check_content_keywords(
        content, ["适用场景", "适用于", "使用场景", "场景", "客户上线", "onboarding"], 1
    )
    results.append(
        {
            "id": "A4-05",
            "text": "有适用场景说明",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A4-06: 检查要点字段
    passed, evidence = check_content_keywords(content, ["检查要点"], 1)
    results.append(
        {
            "id": "A4-06",
            "text": "检查点有检查要点字段",
            "passed": passed,
            "evidence": evidence,
        }
    )

    return results


def grade_eval_5(content: str, files: dict[str, str]) -> list[dict]:
    """ambiguous-needs-pipeline: 隐式流水线需求"""
    results = []

    # A5-01: 识别出流水线模式
    passed, evidence = check_content_keywords(
        content, ["流水线", "pipeline", "分阶段", "按步骤", "阶段"], 1
    )
    results.append(
        {
            "id": "A5-01",
            "text": "识别出流水线模式",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-02: 拆分为多个阶段
    stages = ["调研", "竞品", "需求", "PRD", "技术方案", "设计", "评审"]
    passed, evidence = check_stage_structure(content, stages)
    results.append(
        {
            "id": "A5-02",
            "text": "拆分为多个阶段",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-03: 第一阶段后暂停
    passed_pause, evidence_pause = check_checkpoint_pause(content)
    passed_stop, evidence_stop = check_not_completed_all(
        content, ["技术方案完成", "评审通过", "评审完成", "所有阶段完成"]
    )
    passed = passed_pause and passed_stop
    evidence = f"暂停确认: {evidence_pause}; 停止状态: {evidence_stop}"
    results.append(
        {
            "id": "A5-03",
            "text": "第一阶段后暂停",
            "passed": passed,
            "evidence": evidence,
        }
    )

    # A5-04: 进度指示
    passed, evidence = check_progress_indicator(content)
    results.append(
        {"id": "A5-04", "text": "包含进度指示", "passed": passed, "evidence": evidence}
    )

    # A5-05: 有实质性内容
    # 竞品调研应包含具体动作而非只是声明
    substantive_kw = [
        "产品",
        "功能",
        "市场",
        "分析",
        "对比",
        "特点",
        "优势",
        "feature",
        "compare",
    ]
    passed, evidence = check_content_keywords(content, substantive_kw, 2)
    results.append(
        {"id": "A5-05", "text": "有实质性内容", "passed": passed, "evidence": evidence}
    )

    # A5-06: 确认请求
    passed, evidence = check_checkpoint_pause(content)
    results.append(
        {"id": "A5-06", "text": "包含确认请求", "passed": passed, "evidence": evidence}
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
    files = collect_files(eval_dir)
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

    results = grader(content, files)
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

    # 检查是否是单个 eval 目录
    has_content = any(target.rglob("*.md")) or any(target.rglob("*.txt"))
    match = re.search(r"eval-?(\d+)", target.name)
    if match and has_content:
        eval_dirs = [(target, int(match.group(1)))]
    else:
        # 扫描子目录
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
        "skill_name": "skill-pipeline",
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
