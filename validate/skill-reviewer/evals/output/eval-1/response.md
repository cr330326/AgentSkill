# 审查报告

**审查类型**: Python 代码审查
**审查清单**: `references/python-review-checklist.md`
**审查对象**: 用户提供的 Python 代码片段（3 个函数：`get_user_data`、`process`、`read_file`）

## 总览
共发现 **12** 个问题：严重 **5** 个，警告 **3** 个，建议 **4** 个。

---

## 严重问题（必须修复）

### [PY-24] SQL 注入漏洞
- **位置**: `get_user_data`:行 11
- **问题**: 使用字符串拼接构造 SQL 查询 `"SELECT * FROM users WHERE id = " + str(user_id)`，攻击者可以通过构造恶意 `user_id` 注入任意 SQL 语句，导致数据泄露或数据库被破坏。
- **修复建议**: 使用参数化查询：
  ```python
  query = "SELECT * FROM users WHERE id = ?"
  result = db_conn.execute(query, (user_id,))
  ```

### [PY-26] 敏感信息硬编码
- **位置**: 模块顶层:行 7
- **问题**: API Key `"sk-1234567890abcdef"` 直接硬编码在源码中。一旦代码提交到版本控制系统，密钥将永久暴露，即使后续删除也可从历史中恢复。
- **修复建议**: 通过环境变量或配置文件加载敏感信息：
  ```python
  API_KEY = os.environ.get("API_KEY")
  if not API_KEY:
      raise RuntimeError("环境变量 API_KEY 未设置")
  ```

### [PY-11] 禁止裸 except
- **位置**: `process`:行 18
- **问题**: 使用了裸 `except:` 子句，会捕获包括 `KeyboardInterrupt`、`SystemExit` 在内的所有异常，导致程序无法正常中断，且完全隐藏了错误原因。
- **修复建议**: 明确捕获预期的异常类型：
  ```python
  except (KeyError, TypeError) as e:
      logger.error("处理数据项失败: %s", e)
  ```

### [PY-13] 不要吞掉异常
- **位置**: `process`:行 19
- **问题**: `except: pass` 将所有异常静默吞掉，数据处理中的任何错误（键不存在、类型错误、索引越界等）都不会有任何反馈，导致问题极难排查。
- **修复建议**: 至少记录异常信息，根据业务需求决定是跳过还是中断：
  ```python
  except (KeyError, TypeError) as e:
      logger.warning("跳过无效数据项 %s: %s", item, e)
      continue
  ```

### [PY-15] 资源未使用 with 语句管理
- **位置**: `read_file`:行 22-24
- **问题**: 使用 `f = open(path, 'r')` 打开文件但没有使用 `with` 语句，也没有 `finally` 块关闭文件。如果 `f.read()` 抛出异常，文件句柄将泄漏。
- **修复建议**: 使用上下文管理器：
  ```python
  def read_file(path):
      with open(path, 'r') as f:
          return f.read()
  ```

---

## 警告问题（建议修复）

### [PY-05] 未使用的导入
- **位置**: 模块顶层:行 1-5
- **问题**: `os`、`json`、`datetime`、`sys` 四个模块被导入但在代码中从未使用，增加了不必要的依赖和阅读负担。
- **修复建议**: 删除未使用的导入，只保留实际使用的模块：
  ```python
  import requests
  ```

### [PY-19] 嵌套深度过深
- **位置**: `process`:行 13-17
- **问题**: `try` → `for` → `if` → `if` → `if`，嵌套达到 5 层，远超 3 层的建议上限，严重影响可读性。
- **修复建议**: 使用提前返回（guard clause）或提取子函数来减少嵌套：
  ```python
  def process(data):
      for item in data:
          if not _is_high_score_active(item):
              continue
          print('good')

  def _is_high_score_active(item):
      return (item['type'] == 'A'
              and item['status'] == 'active'
              and item['score'] > 80)
  ```

### [PY-01] 函数命名过于模糊
- **位置**: `process`:行 11
- **问题**: 函数名 `process` 没有传达任何业务语义，无法从名称理解函数的职责。此外，循环变量 `i` 仅用于索引取值，应改为直接迭代。
- **修复建议**: 用具体的业务动词命名函数，例如 `filter_high_score_items` 或 `evaluate_active_items`。循环改为：
  ```python
  for item in data:
  ```

---

## 优化建议（可选改进）

### [PY-02] 导入顺序不符合 PEP 8
- **位置**: 模块顶层:行 1-5
- **问题**: 标准库模块 `sys` 出现在第三方库 `requests` 之后。PEP 8 要求按 "标准库 → 第三方库 → 本地模块" 分组，组间空行分隔。
- **修复建议**:
  ```python
  import os
  import sys
  from datetime import datetime

  import requests
  ```

### [PY-06] 缺少函数签名类型标注
- **位置**: 所有函数:行 9, 11, 21
- **问题**: 三个函数均没有参数和返回值的类型标注，降低了 IDE 辅助能力和代码可维护性。
- **修复建议**: 添加类型标注，例如：
  ```python
  def get_user_data(user_id: int, db_conn: Connection) -> Any:
      ...

  def process(data: list[dict[str, Any]]) -> None:
      ...

  def read_file(path: str) -> str:
      ...
  ```

### [PY-08] 缺少 Docstring
- **位置**: 所有函数:行 9, 11, 21
- **问题**: 三个函数均没有 docstring，无法从文档层面了解函数的用途、参数含义和返回值。
- **修复建议**: 至少为公开函数添加一行 docstring：
  ```python
  def get_user_data(user_id: int, db_conn: Connection) -> Any:
      """根据用户 ID 从数据库查询用户信息。"""
  ```

### [PY-22] 魔法数字
- **位置**: `process`:行 17
- **问题**: 数字 `80` 直接出现在条件判断中，无法理解其业务含义（是及格线？优秀阈值？）。
- **修复建议**: 提取为命名常量：
  ```python
  HIGH_SCORE_THRESHOLD = 80

  if item['score'] > HIGH_SCORE_THRESHOLD:
  ```
