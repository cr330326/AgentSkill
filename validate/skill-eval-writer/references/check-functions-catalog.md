# 检查函数清单

grade.py 中可复用的检查函数模式。根据目标 skill 的输出特点选取合适的函数。

所有函数遵循统一契约：
- 返回 `tuple[bool, str]`（passed, evidence），或 `tuple[bool, int, str]`（含计数）
- 不区分大小写（`.lower()` 或 `re.IGNORECASE`）
- evidence 包含足够信息用于调试

---

## 1. 关键词检查

### check_keywords — 基础关键词命中

```python
def check_keywords(
    content: str, keywords: list[str], min_hits: int
) -> tuple[bool, str]:
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= min_hits
    evidence = f"命中 {len(found)}/{len(keywords)} 个关键词: {found}"
    return passed, evidence
```

适用场景：验证输出是否提到了核心概念。

注意事项：
- 避免使用过宽关键词（"使用"、"建议"、"pass"、"error"），这些几乎在任何输出中都会出现
- 优先用领域特定词汇（如 "SQL 注入" 而非 "注入"）
- `min_hits` 建议设为 `len(keywords) * 0.5` 以上，太低容易误判

---

### check_content_keywords — check_keywords 的别名

功能完全相同，仅名称不同。两种命名都可以使用。

---

## 2. 近邻匹配

### check_proximity — 两个关键词的近距离共现

```python
def check_proximity(
    content: str, word_a: str, word_b: str, max_distance: int = 30
) -> tuple[bool, str]:
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
```

适用场景：验证两个相关概念是否在同一上下文中被讨论（如"密码"和"日志"，"SQL"和"参数化"）。比分别 check_keywords 更有区分度。

注意事项：
- `max_distance` 默认 30 字符，中文约 30 个汉字，英文约 5-6 个单词
- 自动检查双向（A...B 和 B...A）

---

## 3. 段落提取

### check_section_content — 提取 ## 标题下的内容并检查关键词

```python
def check_section_content(
    content: str, section_heading: str, keywords: list[str], min_hits: int = 1
) -> tuple[bool, str]:
    pattern = rf"## {re.escape(section_heading)}(.*?)(?=\n## [^#]|\Z)"
    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not m:
        return False, f"未找到 '## {section_heading}' 段落"
    section = m.group(1)
    found = [kw for kw in keywords if kw.lower() in section.lower()]
    passed = len(found) >= min_hits
    evidence = f"'{section_heading}' 段中命中 {len(found)}/{len(keywords)}: {found}"
    return passed, evidence
```

适用场景：验证特定章节中是否包含预期内容（如"严重问题"章节中是否提到了 SQL 注入）。

**关键陷阱**：
- 必须用 `(?=\n## [^#]|\Z)` 而非 `(?=##|$)`，否则 `###` 子标题会中断匹配
- `\Z` 匹配字符串末尾，确保最后一个章节也能被提取

---

## 4. 编号检查

### check_specific_id — 精确检查某个编号

```python
def check_specific_id(content: str, target_id: str) -> tuple[bool, str]:
    found = target_id.upper() in content.upper()
    evidence = f"{'找到' if found else '未找到'} {target_id}"
    return found, evidence
```

### check_specific_ids_any — 检查一组编号中的至少一个

```python
def check_specific_ids_any(content: str, target_ids: list[str]) -> tuple[bool, str]:
    found = [tid for tid in target_ids if tid.upper() in content.upper()]
    passed = len(found) > 0
    evidence = f"找到: {found}" if found else f"未找到 {target_ids} 中的任何一个"
    return passed, evidence
```

### check_checklist_ids — 按前缀统计编号数量

```python
def check_checklist_ids(
    content: str, prefix: str, min_count: int
) -> tuple[bool, int, str]:
    pattern = rf"{prefix}-\d{{1,2}}"
    matches = list(set(re.findall(pattern, content, re.IGNORECASE)))
    count = len(matches)
    passed = count >= min_count
    evidence = f"找到 {count} 个 {prefix}-xx 编号: {matches[:10]}"
    return passed, count, evidence
```

适用场景：验证输出是否引用了 references/ 中清单的条目编号。

---

## 5. 结构检查

### check_yaml_frontmatter — YAML 前言格式

```python
def check_yaml_frontmatter(content: str) -> tuple[bool, str]:
    if not content.strip().startswith("---"):
        return False, "缺少 YAML frontmatter"
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
```

### check_severity_groups — 严重程度分组

```python
def check_severity_groups(content: str) -> tuple[bool, int, str]:
    groups = {
        "严重": ["严重", "critical", "必须修复"],
        "警告": ["警告", "warning", "建议修复"],
        "建议": ["建议", "suggestion", "可选改进", "优化"],
    }
    found_groups = []
    for group_name, keywords in groups.items():
        if any(kw.lower() in content.lower() for kw in keywords):
            found_groups.append(group_name)
    passed = len(found_groups) >= 2
    evidence = f"找到 {len(found_groups)} 个严重程度分组: {found_groups}"
    return passed, len(found_groups), evidence
```

### check_count_summary — 数量统计

```python
def check_count_summary(content: str) -> tuple[bool, str]:
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
```

注意：数字可能被 `**bold**` 包裹，正则中用 `\*{0,2}` 匹配。

---

## 6. 文件生成型 skill 专用

### find_file_by_name — 按文件名查找

```python
def find_file_by_name(
    files: dict[str, str], name: str
) -> tuple[str, str]:
    for path, content in files.items():
        if Path(path).name.lower() == name.lower():
            return path, content
    return None, None
```

### find_files_in_dir — 按目录查找

```python
def find_files_in_dir(files: dict[str, str], dirname: str) -> dict[str, str]:
    result = {}
    for path, content in files.items():
        parts = Path(path).parts
        if dirname in parts:
            result[path] = content
    return result
```

### check_numbered_rules — 编号前缀规则统计

```python
def check_numbered_rules(content: str) -> tuple[bool, int, str]:
    pattern = r"###?\s+[A-Z]+-\d+"
    matches = re.findall(pattern, content)
    count = len(matches)
    passed = count >= 5
    evidence = f"找到 {count} 条编号规则"
    return passed, count, evidence
```

### check_code_examples — 代码块统计

```python
def check_code_examples(
    content: str, lang: str = None
) -> tuple[bool, int, str]:
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
```

---

## 7. 行为控制检查

### check_checkpoint — 是否在指定阶段暂停

```python
def check_checkpoint(content: str, stop_keyword: str, forbidden_keywords: list[str]) -> tuple[bool, str]:
    """检查输出是否在指定点暂停，不包含后续阶段的内容。"""
    has_stop = stop_keyword.lower() in content.lower()
    leaked = [kw for kw in forbidden_keywords if kw.lower() in content.lower()]
    passed = has_stop and len(leaked) == 0
    evidence = f"暂停标记={has_stop}; 泄漏的后续内容: {leaked}" if leaked else f"暂停标记={has_stop}; 正确未包含后续内容"
    return passed, evidence
```

适用场景：验证分阶段执行的 skill 是否在正确的阶段暂停等待用户确认。

---

## 8. 进度指示器检查

### check_progress_indicator — 是否有阶段进度标记

```python
def check_progress_indicator(content: str) -> tuple[bool, str]:
    patterns = [
        r"\[阶段\s*\d+\s*/\s*\d+\]",
        r"\[Stage\s*\d+\s*/\s*\d+\]",
        r"\[Step\s*\d+\s*/\s*\d+\]",
        r"第\s*\d+\s*[步阶段]",
        r"阶段\s*\d+",
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.extend(matches[:3])
    passed = len(found) > 0
    evidence = f"进度标记: {found[:5]}" if found else "未找到进度标记"
    return passed, evidence
```

---

## 设计原则汇总

1. **返回 (passed, evidence)** — evidence 是字符串，用于调试和 grading.json 展示
2. **不区分大小写** — 所有匹配用 `.lower()` 或 `re.IGNORECASE`
3. **处理 Markdown 格式** — 数字可能被 `**bold**`，用 `\*{0,2}` 匹配
4. **正则段落提取** — 用 `(?=\n## [^#]|\Z)` 结尾，不用 `(?=##|$)`
5. **Python 3.9 兼容** — 文件开头加 `from __future__ import annotations`，不用 `str | None`
6. **领域特有关键词** — 优先用精确词汇，避免过宽匹配
7. **组合优于单一** — 两个弱断言组合比一个强断言更有区分度
