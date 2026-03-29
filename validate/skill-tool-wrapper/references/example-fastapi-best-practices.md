# FastAPI 最佳实践（示范）

本文件展示一个 Tool Wrapper 的 best-practices.md 应该怎么写。
这里的内容是推荐而非强制的，目的是引导更好的设计决策。

## 目录
- [BP-01 ~ BP-04] 性能优化
- [BP-05 ~ BP-08] 安全实践
- [BP-09 ~ BP-12] 测试策略
- [BP-13 ~ BP-15] 部署与运维

---

## 性能优化

### BP-01 异步优先
I/O 密集型操作（数据库查询、HTTP 请求、文件读写）使用 `async/await`。
CPU 密集型操作不要用 async（会阻塞事件循环），使用 `run_in_executor` 或后台任务。

```python
# I/O 操作 — 使用 async
@router.get("/users/{id}")
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == id))
    return result.scalar_one_or_none()

# CPU 密集型 — 放到线程池
@router.post("/process")
async def process_data(data: DataInput):
    result = await run_in_executor(None, heavy_computation, data)
    return result
```

### BP-02 数据库查询优化
- 使用 `selectinload` / `joinedload` 避免 N+1 查询
- 列表查询只 select 需要的列
- 大批量写入使用 `bulk_insert_mappings`

### BP-03 响应缓存
对于不频繁变化的数据，使用缓存中间件或手动缓存：

```python
from fastapi_cache.decorator import cache

@router.get("/config")
@cache(expire=300)  # 缓存 5 分钟
async def get_config():
    return await load_config()
```

### BP-04 后台任务
不需要实时返回结果的操作（如发送邮件、生成报告）使用 `BackgroundTasks`：

```python
@router.post("/orders")
async def create_order(order: OrderCreate, background_tasks: BackgroundTasks):
    result = await order_service.create(order)
    background_tasks.add_task(send_confirmation_email, result.email)
    return result
```

---

## 安全实践

### BP-05 CORS 配置
明确配置允许的源，不使用通配符：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### BP-06 请求限流
对公开接口添加频率限制，防止滥用：

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginInput):
    ...
```

### BP-07 敏感数据过滤
日志和响应中不暴露密码、token 等敏感字段：

```python
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    # 不包含 password_hash、api_key 等字段
```

### BP-08 输入大小限制
限制请求体大小和文件上传大小，防止资源耗尽：

```python
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.size > 10 * 1024 * 1024:  # 10MB
        raise AppError("FILE_TOO_LARGE", "File exceeds 10MB limit")
```

---

## 测试策略

### BP-09 使用 TestClient
集成测试使用 FastAPI 提供的 `TestClient`：

```python
from fastapi.testclient import TestClient

def test_create_user():
    response = client.post("/api/v1/users", json={"name": "Alice", "email": "a@b.com"})
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
```

### BP-10 数据库隔离
测试使用独立的数据库或事务回滚，确保测试之间互不影响：

```python
@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

### BP-11 依赖覆盖
测试中通过 `dependency_overrides` 替换外部依赖：

```python
def override_get_db():
    return test_db_session

app.dependency_overrides[get_db] = override_get_db
```

### BP-12 测试覆盖目标
- 每个路由至少有正常路径和一个异常路径的测试
- Service 层的业务逻辑单独测试
- 不测试 FastAPI 框架本身的行为（如 Pydantic 校验）

---

## 部署与运维

### BP-13 健康检查
提供 `/health` 端点，检查核心依赖状态：

```python
@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"}
        )
```

### BP-14 结构化日志
使用结构化日志（JSON 格式），方便日志聚合和搜索：

```python
import structlog
logger = structlog.get_logger()

logger.info("user_created", user_id=user.id, email=user.email)
```

### BP-15 优雅关闭
使用 lifespan 管理启动/关闭逻辑：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    await init_db()
    yield
    # 关闭时
    await close_db_connections()

app = FastAPI(lifespan=lifespan)
```
