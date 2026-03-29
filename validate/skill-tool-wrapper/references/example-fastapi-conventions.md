# FastAPI 编码规范（示范）

本文件展示一个 Tool Wrapper 的 conventions.md 应该怎么写。
以 FastAPI 为例，包含项目结构、命名、路由、错误处理等硬性规则。

## 目录
- [FAPI-01 ~ FAPI-05] 项目结构
- [FAPI-06 ~ FAPI-10] 路由与接口设计
- [FAPI-11 ~ FAPI-14] 数据验证与序列化
- [FAPI-15 ~ FAPI-18] 错误处理
- [FAPI-19 ~ FAPI-22] 依赖注入

---

## 项目结构

### FAPI-01 标准目录布局

```
project-name/
├── app/
│   ├── __init__.py
│   ├── main.py              # 应用入口，挂载路由
│   ├── config.py             # 配置管理（环境变量）
│   ├── dependencies.py       # 公共依赖（数据库会话等）
│   ├── models/               # SQLAlchemy / ORM 模型
│   ├── schemas/              # Pydantic 请求/响应模型
│   ├── routers/              # 路由模块（按资源拆分）
│   ├── services/             # 业务逻辑层
│   └── utils/                # 工具函数
├── tests/
├── alembic/                  # 数据库迁移
├── pyproject.toml
└── .env
```

### FAPI-02 路由模块拆分
每个资源对应一个路由文件：`routers/users.py`、`routers/orders.py`。
禁止在 `main.py` 中直接定义路由。

### FAPI-03 配置管理
使用 Pydantic `BaseSettings` 管理配置，从环境变量读取。
禁止在代码中硬编码配置值。

```python
# 正确
class Settings(BaseSettings):
    database_url: str
    api_key: str
    model_config = SettingsConfigDict(env_file=".env")

# 错误
DATABASE_URL = "postgresql://user:pass@localhost/db"
```

### FAPI-04 入口文件
`main.py` 只负责创建 app 实例和挂载路由，不包含业务逻辑。

### FAPI-05 分层原则
- Router 层：接收请求、调用 Service、返回响应
- Service 层：业务逻辑、事务管理
- Model 层：数据库交互

Router 不直接操作数据库，Service 不直接访问 Request 对象。

---

## 路由与接口设计

### FAPI-06 URL 命名
- 使用复数名词：`/users`、`/orders`
- 使用 kebab-case：`/user-profiles` 而非 `/user_profiles`
- RESTful 风格：`GET /users/{id}` 而非 `GET /get-user`

### FAPI-07 路由前缀与标签
每个路由模块使用 `APIRouter` 并指定 `prefix` 和 `tags`：

```python
router = APIRouter(prefix="/users", tags=["users"])
```

### FAPI-08 响应模型
所有接口必须指定 `response_model`，明确返回数据结构：

```python
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int): ...
```

### FAPI-09 状态码
显式指定非默认状态码：

```python
@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate): ...
```

### FAPI-10 版本管理
API 版本通过 URL 前缀管理：`/api/v1/users`。

---

## 数据验证与序列化

### FAPI-11 请求/响应模型分离
创建（Create）、更新（Update）、响应（Response）使用不同的 Pydantic 模型：

```python
class UserCreate(BaseModel):   # 创建时的输入
    name: str
    email: EmailStr

class UserUpdate(BaseModel):   # 更新时的输入（字段可选）
    name: str | None = None
    email: EmailStr | None = None

class UserResponse(BaseModel): # 返回给客户端
    id: int
    name: str
    email: str
    model_config = ConfigDict(from_attributes=True)
```

### FAPI-12 字段验证
使用 Pydantic `Field` 添加约束：

```python
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=200)
```

### FAPI-13 枚举类型
固定选项使用 `Enum`：

```python
class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
```

### FAPI-14 分页
列表接口统一使用分页参数：

```python
@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(skip: int = 0, limit: int = Query(default=20, le=100)):
    ...
```

---

## 错误处理

### FAPI-15 统一错误格式
所有错误响应遵循统一结构：

```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User with id 42 not found",
    "details": {}
  }
}
```

### FAPI-16 自定义异常
定义业务异常类，通过异常处理器统一转换：

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}}
    )
```

### FAPI-17 禁止暴露内部错误
生产环境不返回堆栈信息。500 错误统一返回 `INTERNAL_ERROR`。

### FAPI-18 HTTP 状态码使用
- 400：请求参数无效
- 401：未认证
- 403：无权限
- 404：资源不存在
- 409：资源冲突（如重复创建）
- 422：Pydantic 校验失败（FastAPI 默认行为）

---

## 依赖注入

### FAPI-19 数据库会话
使用 `Depends` 注入数据库会话，确保请求结束后自动关闭：

```python
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{id}")
async def get_item(id: int, db: Session = Depends(get_db)):
    ...
```

### FAPI-20 认证依赖
认证逻辑封装为依赖，通过 `Depends` 注入：

```python
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

### FAPI-21 依赖组合
复杂的权限检查通过组合依赖实现：

```python
async def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403)
    return user
```

### FAPI-22 依赖作用域
- 请求级依赖（默认）：每个请求创建新实例
- 应用级依赖（`app.dependency_overrides`）：仅用于测试
