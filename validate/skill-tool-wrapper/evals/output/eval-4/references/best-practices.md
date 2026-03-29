# Go 团队最佳实践

本文件定义团队 Go 项目的推荐实践。这些不是硬性规则，但遵循它们可以获得更好的
代码质量、可维护性和性能表现。

## 目录
- [BP-01 ~ BP-03] 项目结构
- [BP-04 ~ BP-06] 并发与性能
- [BP-07 ~ BP-08] 测试策略
- [BP-09 ~ BP-10] 部署与运维

---

## 项目结构

### BP-01 标准目录布局

推荐遵循社区通用的项目布局，业务代码放在 `internal/` 下防止外部引用，
对外暴露的库代码放在 `pkg/` 下。

```
my-service/
├── cmd/
│   └── server/
│       └── main.go              # 入口，只做初始化和启动
├── internal/
│   ├── config/
│   │   └── config.go            # 配置结构体和加载逻辑
│   ├── handler/
│   │   ├── user.go              # HTTP handler
│   │   └── order.go
│   ├── service/
│   │   ├── user.go              # 业务逻辑
│   │   └── order.go
│   ├── repository/
│   │   ├── user.go              # 数据库访问
│   │   └── order.go
│   └── model/
│       ├── user.go              # 数据模型
│       └── order.go
├── config.yaml
├── go.mod
└── go.sum
```

### BP-02 分层架构

推荐三层架构，每层职责清晰：

- **Handler 层**：接收 HTTP 请求，解析参数，调用 Service，返回响应
- **Service 层**：业务逻辑，事务编排，不直接操作 `http.Request` / `http.ResponseWriter`
- **Repository 层**：数据库操作，SQL 查询

Handler 不直接调用 Repository，Service 不直接操作 HTTP 对象。

```go
// ref: BP-02 — 分层示例

// handler 层：接收请求，调用 service
func MakeCreateOrderHandler(svc *service.OrderService, logger *zap.Logger) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        var req CreateOrderRequest
        if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
            http.Error(w, "invalid request body", http.StatusBadRequest)
            return
        }

        order, err := svc.CreateOrder(r.Context(), req.UserID, req.Items)
        if err != nil {
            logger.Error("创建订单失败", zap.Error(err))
            http.Error(w, "internal error", http.StatusInternalServerError)
            return
        }

        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusCreated)
        json.NewEncoder(w).Encode(order)
    }
}

// service 层：业务逻辑，不碰 HTTP 对象
func (s *OrderService) CreateOrder(ctx context.Context, userID string, items []Item) (*Order, error) {
    user, err := s.userRepo.GetByID(ctx, userID)
    if err != nil {
        return nil, errors.Wrap(err, "查询用户失败")
    }

    order := &Order{
        UserID: user.ID,
        Items:  items,
        Status: "pending",
    }
    if err := s.orderRepo.Create(ctx, order); err != nil {
        return nil, errors.Wrap(err, "创建订单记录失败")
    }

    s.logger.Info("订单创建成功",
        zap.String("order_id", order.ID),
        zap.String("user_id", userID),
    )
    return order, nil
}
```

### BP-03 依赖注入

推荐通过构造函数注入依赖，避免使用全局变量。所有依赖在 `main.go` 中组装。

```go
// ref: BP-03 — 构造函数注入依赖
func NewUserService(repo UserRepository, logger *zap.Logger) *UserService {
    return &UserService{
        repo:   repo,
        logger: logger,
    }
}

// main.go 中组装
func main() {
    cfg, err := config.LoadConfig()
    if err != nil {
        log.Fatalf("加载配置失败: %v", err) // 仅启动阶段允许 Fatalf
    }

    logger, _ := zap.NewProduction()
    defer logger.Sync()

    db := repository.NewDB(cfg.Database)
    userRepo := repository.NewUserRepository(db)
    userSvc := service.NewUserService(userRepo, logger)

    mux := http.NewServeMux()
    handler.RegisterRoutes(mux, userSvc, logger)

    server := &http.Server{
        Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
        Handler:      mux,
        ReadTimeout:  cfg.Server.ReadTimeout,
        WriteTimeout: cfg.Server.WriteTimeout,
    }

    logger.Info("服务启动", zap.Int("port", cfg.Server.Port))
    if err := server.ListenAndServe(); err != nil {
        logger.Fatal("服务启动失败", zap.Error(err))
    }
}
```

---

## 并发与性能

### BP-04 Goroutine 生命周期管理

启动 goroutine 时必须确保有明确的退出机制。推荐使用 `context.Context` 控制取消，
使用 `sync.WaitGroup` 或 `errgroup.Group` 等待完成。

```go
import "golang.org/x/sync/errgroup"

// ref: BP-04 — 使用 errgroup 管理并发任务
func ProcessBatch(ctx context.Context, items []Item) error {
    g, ctx := errgroup.WithContext(ctx)

    for _, item := range items {
        item := item // 闭包变量捕获
        g.Go(func() error {
            return processItem(ctx, item)
        })
    }

    if err := g.Wait(); err != nil {
        return errors.Wrap(err, "批量处理失败")
    }
    return nil
}
```

### BP-05 避免 Goroutine 泄漏

常见的泄漏场景和预防方式：

- **无缓冲 channel 无人读取**：确保 channel 的生产者和消费者成对出现
- **无超时的阻塞操作**：使用 `context.WithTimeout` 限制等待时间
- **后台任务无退出信号**：传入 `ctx` 并监听 `ctx.Done()`

```go
// ref: BP-05 — 带超时的外部调用
func CallExternalAPI(ctx context.Context, url string) ([]byte, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return nil, errors.Wrap(err, "创建请求失败")
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return nil, errors.Wrap(err, "调用外部 API 失败")
    }
    defer resp.Body.Close()

    return io.ReadAll(resp.Body)
}
```

### BP-06 合理使用 sync.Pool

对于频繁分配和回收的对象（如 buffer），使用 `sync.Pool` 减少 GC 压力：

```go
// ref: BP-06 — sync.Pool 复用 buffer
var bufPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func EncodeResponse(data interface{}) ([]byte, error) {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufPool.Put(buf)
    }()

    if err := json.NewEncoder(buf).Encode(data); err != nil {
        return nil, errors.Wrap(err, "编码响应失败")
    }
    return buf.Bytes(), nil
}
```

---

## 测试策略

### BP-07 表驱动测试

Go 的测试推荐使用表驱动（table-driven）模式，覆盖多种输入组合：

```go
// ref: BP-07 — 表驱动测试
func TestValidateEmail(t *testing.T) {
    tests := []struct {
        name    string
        email   string
        wantErr bool
    }{
        {"valid email", "user@example.com", false},
        {"missing @", "userexample.com", true},
        {"empty string", "", true},
        {"unicode domain", "user@例え.jp", false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ValidateEmail(tt.email)
            if (err != nil) != tt.wantErr {
                t.Errorf("ValidateEmail(%q) error = %v, wantErr %v",
                    tt.email, err, tt.wantErr)
            }
        })
    }
}
```

### BP-08 使用接口做依赖 mock

Service 层依赖 Repository 接口而非具体实现，测试时传入 mock：

```go
// ref: BP-08 — 接口定义，方便测试 mock
type UserRepository interface {
    GetByID(ctx context.Context, id string) (*User, error)
    Create(ctx context.Context, user *User) error
}

// 测试中使用 mock 实现
type mockUserRepo struct {
    users map[string]*User
}

func (m *mockUserRepo) GetByID(ctx context.Context, id string) (*User, error) {
    user, ok := m.users[id]
    if !ok {
        return nil, errors.New("user not found")
    }
    return user, nil
}

func (m *mockUserRepo) Create(ctx context.Context, user *User) error {
    m.users[user.ID] = user
    return nil
}

func TestUserService_GetUser(t *testing.T) {
    repo := &mockUserRepo{
        users: map[string]*User{
            "1": {ID: "1", Name: "Alice"},
        },
    }
    logger, _ := zap.NewDevelopment()
    svc := NewUserService(repo, logger)

    user, err := svc.GetUser(context.Background(), "1")
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if user.Name != "Alice" {
        t.Errorf("expected Alice, got %s", user.Name)
    }
}
```

---

## 部署与运维

### BP-09 健康检查端点

提供 `/healthz` 和 `/readyz` 端点，分别用于存活探针和就绪探针：

```go
// ref: BP-09 — 健康检查
func MakeHealthHandler() http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{
            "status": "ok",
        })
    }
}

func MakeReadyHandler(db *sql.DB) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if err := db.PingContext(r.Context()); err != nil {
            w.WriteHeader(http.StatusServiceUnavailable)
            json.NewEncoder(w).Encode(map[string]string{
                "status":   "not ready",
                "database": "disconnected",
            })
            return
        }
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{
            "status":   "ready",
            "database": "connected",
        })
    }
}
```

### BP-10 优雅关闭

服务收到关闭信号后，先停止接收新请求，等待正在处理的请求完成后再退出：

```go
// ref: BP-10 — 优雅关闭
func main() {
    // ... 初始化代码 ...

    server := &http.Server{
        Addr:    fmt.Sprintf(":%d", cfg.Server.Port),
        Handler: mux,
    }

    // 启动服务
    go func() {
        if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            logger.Fatal("服务异常退出", zap.Error(err))
        }
    }()

    // 等待中断信号
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    logger.Info("收到关闭信号，开始优雅关闭...")

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := server.Shutdown(ctx); err != nil {
        logger.Error("优雅关闭失败", zap.Error(err))
    }

    logger.Info("服务已关闭")
}
```
