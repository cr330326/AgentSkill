# 审查报告

**审查类型**: 安全审计（Security Audit）
**审查清单**: `references/owasp-checklist.md`（OWASP Top 10 2021）
**审查对象**: Flask API 应用（用户提供的 Python 代码片段）

---

## 总览

共发现 **8 个问题**：严重 **6** 个，警告 **1** 个，建议 **1** 个。

该 API 存在多个致命安全漏洞，包括 SQL 注入、命令注入、不安全反序列化、路径遍历等。**在修复全部严重问题之前，该代码绝不应部署到任何可访问的环境中。**

---

## 严重问题（必须修复）

### [SEC-09] SQL 注入 — 字符串拼接构造 SQL 查询

- **位置**: `app.py:13`
- **问题**: `cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")`  直接将用户输入 `user_id` 通过 f-string 拼接进 SQL 语句。攻击者可通过构造恶意 `user_id`（如 `' OR '1'='1' --`）获取全部用户数据、修改或删除数据库内容。
- **修复建议**: 使用参数化查询，将用户输入作为绑定参数传递，而非拼接字符串。

```python
# 修复前（危险）
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")

# 修复后（安全）
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

---

### [SEC-10] 命令注入 — 直接执行用户提供的 shell 命令

- **位置**: `app.py:23-25`
- **问题**: `run_command` 端点接收用户提交的 JSON 字段 `command`，直接传递给 `subprocess.run(cmd, shell=True)` 执行。这等同于向任何调用者提供了完整的远程代码执行（RCE）能力。攻击者可执行任意系统命令，包括读取文件、安装后门、删除数据等。
- **修复建议**: **删除此端点**。如果确实需要执行特定系统命令，应使用白名单机制，并禁用 `shell=True`。

```python
# 修复方案：删除该端点，或改为严格白名单
ALLOWED_COMMANDS = {
    'disk_usage': ['df', '-h'],
    'uptime': ['uptime'],
}

@app.route('/api/run', methods=['POST'])
@require_admin_auth  # 必须加权限控制
def run_command():
    cmd_name = request.json.get('command')
    if cmd_name not in ALLOWED_COMMANDS:
        return jsonify({'error': 'Command not allowed'}), 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd_name], capture_output=True)
    return jsonify({'output': result.stdout.decode()})
```

---

### [SEC-13] 不安全反序列化 — pickle.loads() 处理不可信数据

- **位置**: `app.py:19-20`
- **问题**: `import_data` 端点直接对请求体调用 `pickle.loads(request.data)`。Python 的 `pickle` 协议允许在反序列化时执行任意代码。攻击者可构造恶意 pickle 载荷实现远程代码执行（RCE），这与命令注入同等危险。
- **修复建议**: **绝不使用 `pickle` 反序列化不可信输入**。改用 JSON 等安全的数据格式。

```python
# 修复前（危险）
data = pickle.loads(request.data)

# 修复后（安全）
import json

@app.route('/api/import', methods=['POST'])
def import_data():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a JSON array'}), 400
    return jsonify({'status': 'ok', 'items': len(data)})
```

---

### [SEC-12] 路径遍历 — 未验证的文件路径参数

- **位置**: `app.py:28-31`
- **问题**: `read_file` 端点直接使用用户提供的 `path` 查询参数打开文件，未做任何验证。攻击者可通过 `?path=../../../etc/passwd` 或 `?path=/etc/shadow` 读取服务器上的任意文件，导致敏感信息泄露。
- **修复建议**: 限制可读文件到指定目录，使用 `os.path.realpath()` 解析后校验是否在允许范围内。

```python
import os

ALLOWED_DIR = '/var/app/public_files'

@app.route('/api/file')
@require_auth  # 加权限控制
def read_file():
    path = request.args.get('path', '')
    # 解析真实路径，防止 ../ 绕过
    real_path = os.path.realpath(os.path.join(ALLOWED_DIR, path))
    if not real_path.startswith(os.path.realpath(ALLOWED_DIR)):
        return jsonify({'error': 'Access denied'}), 403
    if not os.path.isfile(real_path):
        return jsonify({'error': 'File not found'}), 404
    with open(real_path, 'r') as f:
        return f.read()
```

---

### [SEC-01] 权限控制失效 — 全部 API 端点无认证/授权

- **位置**: 全局（所有路由：`/api/user/<user_id>`, `/api/import`, `/api/run`, `/api/file`）
- **问题**: 所有端点均无任何认证（Authentication）或授权（Authorization）机制。任何人可直接调用所有接口，包括执行命令和读取文件等高危操作。违反最小权限原则——默认应拒绝所有访问。
- **修复建议**: 为所有端点添加认证中间件，并根据端点敏感程度设置不同的授权级别。

```python
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ')
        if not token or not verify_token(token):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ')
        user = verify_token(token)
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated

# 使用示例
@app.route('/api/user/<user_id>')
@require_auth
def get_user(user_id):
    ...

@app.route('/api/run', methods=['POST'])
@require_admin
def run_command():
    ...
```

---

### [SEC-16] 错误处理信息泄露 — 生产环境开启 DEBUG 模式

- **位置**: `app.py:6`
- **问题**: `app.config['DEBUG'] = True` 硬编码开启了 Flask 的 debug 模式。在 debug 模式下，未捕获的异常会返回完整的 Python traceback（包含源码、文件路径、局部变量值），且 Flask 会启用交互式调试器（Werkzeug debugger），攻击者可通过调试器直接在服务器上执行任意 Python 代码。
- **修复建议**: 生产环境必须关闭 debug 模式，通过环境变量控制。

```python
import os

# 修复前（危险）
app.config['DEBUG'] = True

# 修复后（安全）
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
```

同时，错误响应中也泄露了内部信息（见 `app.py:15`）：

```python
# 修复前（泄露数据库路径）
return jsonify({'error': f'User {user_id} not found', 'db_path': 'app.db'}), 404

# 修复后（仅返回必要信息）
return jsonify({'error': 'User not found'}), 404
```

---

## 警告问题（建议修复）

### [SEC-02] 水平越权 — 用户可访问任意其他用户的数据

- **位置**: `app.py:10-16`
- **问题**: `/api/user/<user_id>` 接受任意 `user_id` 参数，不校验当前请求者是否有权查看该用户的信息。即使添加了认证，仍需验证请求者只能访问自己（或其授权范围内）的用户数据。
- **修复建议**: 在认证的基础上增加授权检查，确保用户只能访问自己的数据，或验证其具有管理员角色。

```python
@app.route('/api/user/<user_id>')
@require_auth
def get_user(user_id):
    current_user = get_current_user()  # 从 token 中解析
    if current_user['id'] != user_id and current_user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    # ... 继续正常查询
```

---

## 优化建议（可选改进）

### [SEC-14] 缺少速率限制 — API 无请求频率控制

- **位置**: 全局（所有路由）
- **问题**: 所有接口均未设置速率限制（Rate Limiting）。攻击者可对 `/api/user/<user_id>` 进行用户枚举（暴力遍历 ID），或对其他端点发起拒绝服务攻击。
- **修复建议**: 使用 `flask-limiter` 等库添加全局和针对性的速率限制。

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["100/hour"])

@app.route('/api/user/<user_id>')
@limiter.limit("30/minute")
@require_auth
def get_user(user_id):
    ...
```

---

## 修复优先级总结

| 优先级 | 编号 | 问题 | 影响 |
|--------|------|------|------|
| P0 立即修复 | SEC-10 | 命令注入（RCE） | 完全控制服务器 |
| P0 立即修复 | SEC-13 | pickle 反序列化（RCE） | 完全控制服务器 |
| P0 立即修复 | SEC-09 | SQL 注入 | 数据库泄露/篡改 |
| P0 立即修复 | SEC-12 | 路径遍历 | 任意文件读取 |
| P1 尽快修复 | SEC-01 | 无认证授权 | 所有端点暴露 |
| P1 尽快修复 | SEC-16 | DEBUG 模式 + 信息泄露 | 服务器 RCE（debugger） |
| P2 计划修复 | SEC-02 | 水平越权 | 数据泄露 |
| P3 持续改进 | SEC-14 | 无速率限制 | 暴力攻击/DoS |

> **结论**: 该代码存在至少 4 个可直接导致远程代码执行或数据泄露的致命漏洞，**不得在任何环境中上线**。建议按优先级表从上到下逐一修复并进行安全回归测试。
