# Go 团队编码规范

本文件定义团队 Go 项目的硬性编码规则。所有生成的代码必须遵守这些规范。
违反这些规则视为代码缺陷，code review 时必须修正。

## 目录
- [GO-01 ~ GO-02] 错误处理
- [GO-03 ~ GO-04] 日志规范
- [GO-05 ~ GO-06] HTTP Handler 签名
- [GO-07 ~ GO-08] 配置管理

---

## 错误处理

### GO-01 错误必须用 pkg/errors 包装

所有返回的错误必须使用 `github.com/pkg/errors` 进行包装，附带上下文信息。
禁止直接返回裸 error 或使用 `fmt.Errorf`。包装错误时使用 `errors.Wrap` 或 `errors.Wrapf`，
创建新错误使用 `errors.New`。这样做的目的是保留完整的错误调用栈，方便线上问题排查。

**正确示例：**

```go
import "github.com/pkg/errors"

func GetUser(id int64) (*User, error) {
    user, err := db.QueryUser(id)
    if err != nil {
        // ref: GO-01 — 用 errors.Wrap 包装，附带上下文
        return nil, errors.Wrapf(err, "查询用户失败, id=%d", id)
    }
    return user, nil
}

func ValidateInput(req *Request) error {
    if req.Name == "" {
        // ref: GO-01 — 用 errors.New 创建带语义的错误
        return errors.New("name 字段不能为空")
    }
    return nil
}
```

**错误示例：**

```go
// 错误：直接返回裸 error，丢失上下文
func GetUser(id int64) (*User, error) {
    user, err := db.QueryUser(id)
    if err != nil {
        return nil, err // 不知道是哪一步失败的
    }
    return user, nil
}

// 错误：使用 fmt.Errorf 而非 pkg/errors，没有调用栈信息
func GetUser(id int64) (*User, error) {
    user, err := db.QueryUser(id)
    if err != nil {
        return nil, fmt.Errorf("查询用户失败: %w", err)
    }
    return user, nil
}
```

### GO-02 错误检查不可忽略

调用可能返回 error 的函数后，必须立即检查 error。禁止使用 `_` 丢弃 error，
除非函数文档明确说明可以安全忽略（如 `io.Closer` 在只读场景下）。

**正确示例：**

```go
data, err := json.Marshal(user)
if err != nil {
    return errors.Wrap(err, "序列化用户数据失败")
}
```

**错误示例：**

```go
// 错误：忽略了 Marshal 可能的失败
data, _ := json.Marshal(user)
```

---

## 日志规范

### GO-03 统一使用 zap 日志库

所有日志输出必须使用 `go.uber.org/zap`，禁止使用 Go 标准库的 `log` 包，
也禁止使用 `fmt.Println` / `fmt.Printf` 输出运行时日志。
zap 提供结构化日志和高性能输出，是团队统一的日志基础设施。

**正确示例：**

```go
import "go.uber.org/zap"

func InitLogger() *zap.Logger {
    // ref: GO-03 — 生产环境使用 NewProduction
    logger, _ := zap.NewProduction()
    return logger
}

func HandleRequest(logger *zap.Logger, userID int64) {
    // ref: GO-03 — 使用结构化字段
    logger.Info("处理请求",
        zap.Int64("user_id", userID),
        zap.String("action", "query"),
    )
}
```

**错误示例：**

```go
import "log"

// 错误：使用标准库 log
func HandleRequest(userID int64) {
    log.Printf("处理请求, userID=%d", userID)
}

// 错误：使用 fmt 输出运行时日志
func HandleRequest(userID int64) {
    fmt.Printf("处理请求, userID=%d\n", userID)
}
```

### GO-04 日志级别使用规范

- `Debug`：仅在开发环境输出的调试信息
- `Info`：正常的业务事件（请求处理、任务完成等）
- `Warn`：异常但可自动恢复的情况（重试、降级等）
- `Error`：需要人工关注的错误（调用失败、数据不一致等）
- `Fatal`：仅在 main 函数启动阶段使用，服务运行期间禁止调用 `Fatal`

**正确示例：**

```go
// ref: GO-04 — 正确的日志级别使用
logger.Info("订单创建成功", zap.String("order_id", orderID))
logger.Warn("缓存未命中，回源查询", zap.String("key", cacheKey))
logger.Error("调用支付服务失败",
    zap.Error(err),
    zap.String("order_id", orderID),
)
```

---

## HTTP Handler 签名

### GO-05 Handler 函数签名统一为标准库格式

所有 HTTP handler 函数签名必须统一为：

```go
func(w http.ResponseWriter, r *http.Request)
```

禁止使用自定义的 handler 签名（如返回 error 的变体），也禁止使用框架特定的 Context 对象
（如 `gin.Context`、`echo.Context`）。如果需要传入额外依赖（如 logger、service），
通过闭包或方法接收者注入。

**正确示例：**

```go
// ref: GO-05 — 标准 handler 签名，通过闭包注入依赖
func MakeGetUserHandler(svc *UserService, logger *zap.Logger) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        userID := r.URL.Query().Get("id")
        user, err := svc.GetUser(r.Context(), userID)
        if err != nil {
            logger.Error("获取用户失败", zap.Error(err))
            http.Error(w, "internal error", http.StatusInternalServerError)
            return
        }
        json.NewEncoder(w).Encode(user)
    }
}
```

**错误示例：**

```go
// 错误：使用 gin.Context，耦合框架
func GetUser(c *gin.Context) {
    id := c.Param("id")
    c.JSON(200, user)
}

// 错误：自定义返回 error 的签名
func GetUser(w http.ResponseWriter, r *http.Request) error {
    // ...
    return nil
}
```

### GO-06 Handler 注册方式

使用标准库 `http.ServeMux` 或轻量路由库（如 `chi`）注册路由。
路由注册集中在一个文件中（如 `routes.go`），不分散在各个 handler 文件里。

**正确示例：**

```go
// routes.go
// ref: GO-06 — 集中注册路由
func RegisterRoutes(mux *http.ServeMux, svc *UserService, logger *zap.Logger) {
    mux.HandleFunc("GET /users", MakeListUsersHandler(svc, logger))
    mux.HandleFunc("GET /users/{id}", MakeGetUserHandler(svc, logger))
    mux.HandleFunc("POST /users", MakeCreateUserHandler(svc, logger))
}
```

---

## 配置管理

### GO-07 使用 viper 从 YAML 文件读取配置

所有配置必须通过 `github.com/spf13/viper` 从 YAML 文件读取。
禁止在代码中硬编码配置值（如端口号、数据库地址、超时时间等）。
配置文件默认路径为项目根目录下的 `config.yaml`，可通过环境变量 `CONFIG_PATH` 覆盖。

**正确示例：**

```go
import "github.com/spf13/viper"

// ref: GO-07 — 使用 viper 加载 YAML 配置
func LoadConfig() (*Config, error) {
    v := viper.New()
    v.SetConfigName("config")
    v.SetConfigType("yaml")
    v.AddConfigPath(".")

    // 支持环境变量覆盖配置文件路径
    if path := os.Getenv("CONFIG_PATH"); path != "" {
        v.SetConfigFile(path)
    }

    if err := v.ReadInConfig(); err != nil {
        return nil, errors.Wrap(err, "读取配置文件失败")
    }

    var cfg Config
    if err := v.Unmarshal(&cfg); err != nil {
        return nil, errors.Wrap(err, "解析配置失败")
    }
    return &cfg, nil
}
```

**对应的 config.yaml 示例：**

```yaml
server:
  port: 8080
  read_timeout: 30s
  write_timeout: 30s

database:
  host: localhost
  port: 5432
  name: myapp
  user: postgres
  password: "${DB_PASSWORD}"

log:
  level: info
  format: json
```

**错误示例：**

```go
// 错误：硬编码配置
func main() {
    db, _ := sql.Open("postgres", "host=localhost port=5432 dbname=myapp")
    http.ListenAndServe(":8080", nil)
}

// 错误：使用 os.Getenv 散落读取，缺乏集中管理
func getDBHost() string {
    return os.Getenv("DB_HOST")
}
```

### GO-08 配置结构体定义

配置必须映射到强类型的 Go 结构体，禁止在业务代码中直接调用 `viper.GetString` 等方法。
配置结构体统一定义在 `internal/config/config.go` 中。

**正确示例：**

```go
// internal/config/config.go
// ref: GO-08 — 强类型配置结构体
type Config struct {
    Server   ServerConfig   `mapstructure:"server"`
    Database DatabaseConfig `mapstructure:"database"`
    Log      LogConfig      `mapstructure:"log"`
}

type ServerConfig struct {
    Port         int           `mapstructure:"port"`
    ReadTimeout  time.Duration `mapstructure:"read_timeout"`
    WriteTimeout time.Duration `mapstructure:"write_timeout"`
}

type DatabaseConfig struct {
    Host     string `mapstructure:"host"`
    Port     int    `mapstructure:"port"`
    Name     string `mapstructure:"name"`
    User     string `mapstructure:"user"`
    Password string `mapstructure:"password"`
}

type LogConfig struct {
    Level  string `mapstructure:"level"`
    Format string `mapstructure:"format"`
}
```

**错误示例：**

```go
// 错误：业务代码中直接调用 viper
func StartServer() {
    port := viper.GetInt("server.port") // 散落在各处，无法统一管理
    http.ListenAndServe(fmt.Sprintf(":%d", port), nil)
}
```
