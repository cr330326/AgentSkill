# 审查报告

| 项目 | 内容 |
|------|------|
| **审查类型** | Python 代码审查 + OWASP 安全审查（自动检测） |
| **审查清单** | `python-review-checklist.md`（PY-01~PY-37）、`owasp-checklist.md`（SEC-01~SEC-36） |
| **审查对象** | `register_user(username, password, email)` 函数 |

> **自动检测说明：** 用户未指定审查类型。代码为 `.py` Python 文件，自动加载 **python-review-checklist.md**；代码涉及密码处理、身份认证及 SQL 数据库操作，同时加载 **owasp-checklist.md** 进行安全审查。两份清单均已加载并逐项检查。

---

## 总览

| 严重程度 | 数量 |
|----------|------|
| 🔴 严重问题（必须修复） | 3 |
| 🟡 警告问题（建议修复） | 2 |
| 🟢 优化建议（可选改进） | 1 |

---

## 🔴 严重问题（必须修复）

### 1. SQL 注入漏洞

| 项目 | 内容 |
|------|------|
| **清单编号** | PY-24 / SEC-09 |
| **位置** | 第 6 行 `query = f"INSERT INTO users ..."` |
| **问题** | 使用 f-string 直接拼接用户输入（`username`、`email`）构造 SQL 语句，攻击者可通过恶意输入执行任意 SQL，导致数据泄露、篡改或删除。这是 OWASP Top 10 中 A03:2021 注入攻击的典型案例。 |
| **修复建议** | 使用参数化查询（prepared statement），将用户输入作为参数传递而非拼接到 SQL 字符串中。 |

```python
# 修复后
query = "INSERT INTO users (username, password, email, token) VALUES (%s, %s, %s, %s)"
db.execute(query, (username, password_hash, email, token))
```

---

### 2. 使用 MD5 存储密码（弱哈希算法）

| 项目 | 内容 |
|------|------|
| **清单编号** | SEC-06 |
| **位置** | 第 4 行 `hashlib.md5(password.encode()).hexdigest()` |
| **问题** | MD5 是一种已被密码学界淘汰的哈希算法，存在已知碰撞攻击，且计算速度极快，极易被彩虹表和暴力破解攻击还原明文密码。密码存储必须使用专用的慢哈希算法，并自动加盐。 |
| **修复建议** | 使用 `bcrypt`、`argon2` 或 `scrypt` 等专用密码哈希算法。推荐使用 `bcrypt`。 |

```python
# 修复后
import bcrypt

password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

---

### 3. 明文密码写入日志文件（敏感数据泄露）

| 项目 | 内容 |
|------|------|
| **清单编号** | PY-26 / SEC-32 |
| **位置** | 第 9 行 `log_file.write(f'... password: {password}, token: {token}\n')` |
| **问题** | 将用户的明文密码和认证 token 直接写入日志文件。任何能访问日志的人员或系统都可获得用户凭证，违反最小权限原则和数据保护要求。这同时违反了 PY-26（禁止在代码中暴露敏感信息）和 SEC-32（日志中不得包含密码等敏感数据）。 |
| **修复建议** | 日志中绝对不能包含密码、token 等敏感信息。仅记录脱敏后的必要信息。 |

```python
# 修复后
logger.info(f'New user registered: {username}')
# 不记录 password 和 token
```

---

## 🟡 警告问题（建议修复）

### 4. 文件未使用 `with` 语句管理

| 项目 | 内容 |
|------|------|
| **清单编号** | PY-15 |
| **位置** | 第 8 行 `log_file = open('/var/log/app.log', 'a')` |
| **问题** | 使用 `open()` 打开文件后未使用 `with` 上下文管理器，也未调用 `close()`。若后续代码抛出异常，文件句柄将不会被释放，可能导致资源泄漏和数据丢失（缓冲区未刷新）。 |
| **修复建议** | 使用 `with` 语句管理文件资源，确保在任何情况下文件都能被正确关闭。更好的方案是使用 `logging` 标准库。 |

```python
# 修复后（方案一：with 语句）
with open('/var/log/app.log', 'a') as log_file:
    log_file.write(f'New user registered: {username}\n')

# 修复后（方案二：推荐使用 logging 模块）
import logging
logger = logging.getLogger(__name__)
logger.info(f'New user registered: {username}')
```

---

### 5. 认证 token 长度不足

| 项目 | 内容 |
|------|------|
| **清单编号** | SEC-07 |
| **位置** | 第 5 行 `token = os.urandom(8).hex()` |
| **问题** | `os.urandom(8)` 生成 8 字节（64 位）的随机数据，作为认证 token 的熵值偏低。业界推荐 session/token 至少使用 32 字节（256 位）的随机数据以抵御暴力猜测攻击。 |
| **修复建议** | 使用 `secrets` 模块生成足够长度的 token。 |

```python
# 修复后
import secrets
token = secrets.token_hex(32)  # 32 字节 = 256 位
```

---

## 🟢 优化建议（可选改进）

### 6. 缺少函数类型注解和输入校验

| 项目 | 内容 |
|------|------|
| **清单编号** | PY-04 |
| **位置** | 第 3 行 `def register_user(username, password, email):` |
| **问题** | 函数参数和返回值缺少类型注解，且未对输入参数进行任何校验（如 `username` 长度、`email` 格式）。缺少类型注解会降低代码可读性和 IDE 辅助能力；缺少输入校验可能导致脏数据进入数据库。 |
| **修复建议** | 添加类型注解，并在入口处对输入进行基本校验。 |

```python
# 修复后
def register_user(username: str, password: str, email: str) -> dict[str, str]:
    if not username or len(username) > 64:
        raise ValueError("Invalid username")
    if not email or '@' not in email:
        raise ValueError("Invalid email")
    # ...
```

---

## 总结

该函数存在 **3 个严重安全漏洞**（SQL 注入、弱密码哈希、日志泄露明文密码），任意一个都可能导致用户数据大规模泄露，**必须在上线前全部修复**。建议参照以上修复方案逐项处理，并在修复后进行安全复审。

### 引用的清单项汇总

| 清单编号 | 来源 | 说明 |
|----------|------|------|
| PY-04 | python-review-checklist.md | 类型注解 |
| PY-15 | python-review-checklist.md | 资源管理使用 with |
| PY-24 | python-review-checklist.md | SQL 注入防护 |
| PY-26 | python-review-checklist.md | 敏感信息保护 |
| SEC-06 | owasp-checklist.md | 密码存储（bcrypt） |
| SEC-07 | owasp-checklist.md | 敏感数据存储安全 |
| SEC-09 | owasp-checklist.md | SQL 注入防护 |
| SEC-32 | owasp-checklist.md | 日志安全（不含密码） |
