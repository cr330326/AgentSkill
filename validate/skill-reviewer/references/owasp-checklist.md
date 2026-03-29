# OWASP 安全审查清单

基于 OWASP Top 10 (2021) 整理，适用于 Web 应用和 API 的安全审查。

## 目录
- [SEC-01 ~ SEC-04] A01 权限控制失效
- [SEC-05 ~ SEC-08] A02 加密机制失效
- [SEC-09 ~ SEC-13] A03 注入攻击
- [SEC-14 ~ SEC-16] A04 不安全的设计
- [SEC-17 ~ SEC-20] A05 安全配置错误
- [SEC-21 ~ SEC-23] A06 易受攻击和过时的组件
- [SEC-24 ~ SEC-27] A07 身份识别和认证失败
- [SEC-28 ~ SEC-30] A08 软件和数据完整性失败
- [SEC-31 ~ SEC-33] A09 安全日志和监控失败
- [SEC-34 ~ SEC-36] A10 服务端请求伪造 (SSRF)

---

## A01 权限控制失效 (Broken Access Control)

### SEC-01 最小权限原则
- 默认拒绝所有访问，只显式授予需要的权限
- API 端点是否都有权限检查

### SEC-02 水平越权
- 用户是否能通过修改 URL 参数/请求体中的 ID 访问其他用户的数据
- 资源访问是否验证了所属关系（ownership check）

### SEC-03 垂直越权
- 普通用户是否能访问管理员接口
- 角色权限是否在服务端校验（而非仅前端隐藏）

### SEC-04 CORS 配置
- `Access-Control-Allow-Origin` 是否限制了允许的域名
- 是否避免使用 `*` 通配符（特别是携带 credentials 时）

---

## A02 加密机制失效 (Cryptographic Failures)

### SEC-05 传输加密
- 所有通信是否使用 HTTPS/TLS
- 是否有 HTTP → HTTPS 重定向
- TLS 版本是否 >= 1.2

### SEC-06 密码存储
- 密码是否使用强哈希算法（bcrypt/scrypt/argon2），而非 MD5/SHA1
- 是否使用了随机盐值（salt）

### SEC-07 敏感数据存储
- 敏感信息（密码、密钥、token）是否明文存储在数据库、日志或配置文件中
- API Key 和 Secret 是否通过环境变量或密钥管理服务注入

### SEC-08 加密算法
- 是否使用了已知不安全的算法（DES、RC4、MD5 用于安全用途）
- 密钥长度是否符合当前标准（AES-256、RSA-2048+）

---

## A03 注入攻击 (Injection)

### SEC-09 SQL 注入
- 数据库查询是否使用参数化查询 / ORM
- 是否有字符串拼接 SQL 语句的情况

### SEC-10 命令注入
- 是否有使用 `os.system()`、`subprocess.call(shell=True)` 拼接用户输入的情况
- 外部命令参数是否经过转义或验证

### SEC-11 XSS（跨站脚本）
- 用户输入渲染到页面时是否经过转义
- 是否使用了模板引擎的自动转义功能
- 富文本输入是否经过白名单过滤

### SEC-12 路径遍历
- 文件操作中的路径是否验证了不包含 `../`
- 是否使用 `os.path.realpath()` 或 `pathlib.resolve()` 规范化路径

### SEC-13 反序列化
- 是否有使用 `pickle.loads()`、`yaml.load()`（非 safe_load）处理不可信数据
- JSON 反序列化后是否验证了数据结构

---

## A04 不安全的设计 (Insecure Design)

### SEC-14 速率限制
- 登录、注册、密码重置等接口是否有频率限制
- API 是否有请求速率限制防止滥用

### SEC-15 业务逻辑验证
- 关键业务操作（支付、转账、权限变更）是否有服务端校验
- 是否只依赖前端验证

### SEC-16 错误处理信息泄露
- 错误响应是否暴露了内部实现细节（堆栈信息、数据库结构、文件路径）
- 生产环境是否关闭了 debug 模式

---

## A05 安全配置错误 (Security Misconfiguration)

### SEC-17 默认配置
- 是否修改了默认密码和默认账户
- 不必要的功能、端口、服务是否已关闭

### SEC-18 HTTP 安全头
- 是否设置了 `X-Content-Type-Options: nosniff`
- 是否设置了 `X-Frame-Options` 或 CSP frame-ancestors
- 是否设置了合理的 `Content-Security-Policy`

### SEC-19 错误页面
- 404/500 页面是否自定义（不暴露服务器/框架版本信息）

### SEC-20 目录列表
- Web 服务器是否禁止了目录列表（directory listing）

---

## A06 易受攻击和过时的组件 (Vulnerable and Outdated Components)

### SEC-21 依赖版本
- 是否有已知安全漏洞的依赖版本（检查 CVE 数据库）
- 依赖是否定期更新

### SEC-22 最小依赖
- 是否引入了不必要的依赖
- 依赖的维护状态如何（是否已归档/长期无更新）

### SEC-23 锁文件
- 是否有 lock 文件（`poetry.lock`、`package-lock.json`）确保依赖版本一致

---

## A07 身份识别和认证失败 (Identification and Authentication Failures)

### SEC-24 密码策略
- 是否有密码强度要求（长度、复杂度）
- 是否检查常见弱密码

### SEC-25 会话管理
- 会话 token 是否足够随机
- 登出后是否销毁服务端会话
- 会话是否有过期时间

### SEC-26 多因素认证
- 高安全场景是否支持 MFA
- 密码重置流程是否安全（不泄露用户是否存在）

### SEC-27 JWT 安全
- JWT 是否验证了签名算法（防止 `alg: none` 攻击）
- Token 是否有合理的过期时间
- 敏感信息是否存储在 JWT payload 中（payload 是 base64 而非加密）

---

## A08 软件和数据完整性失败 (Software and Data Integrity Failures)

### SEC-28 依赖完整性
- 依赖包是否验证了完整性（hash/签名）
- CI/CD 管道是否有签名验证

### SEC-29 反序列化验证
- 反序列化数据是否有完整性校验
- 是否使用了安全的序列化格式

### SEC-30 自动更新
- 自动更新机制是否验证了更新包的签名和来源

---

## A09 安全日志和监控失败 (Security Logging and Monitoring Failures)

### SEC-31 审计日志
- 登录成功/失败、权限变更、敏感操作是否记录日志
- 日志是否包含足够的上下文（时间、用户、IP、操作）

### SEC-32 日志安全
- 日志中是否包含敏感信息（密码、token、个人数据）
- 日志是否防篡改

### SEC-33 告警机制
- 是否有异常行为检测和告警（如暴力破解、大量 4xx/5xx）

---

## A10 服务端请求伪造 (Server-Side Request Forgery)

### SEC-34 URL 验证
- 服务端发起的请求是否验证了目标 URL（白名单机制）
- 是否禁止访问内网地址（127.0.0.1、10.x、172.16.x、192.168.x）

### SEC-35 协议限制
- 是否限制了允许的协议（仅 http/https，禁止 file://、gopher:// 等）

### SEC-36 响应处理
- 远程请求的响应是否经过验证再返回给用户
- 是否限制了响应大小和超时时间
