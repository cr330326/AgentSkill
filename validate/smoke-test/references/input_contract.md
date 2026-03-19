# Input Contract

在生成或执行 smoke test 之前，先按下面顺序校验输入。

## 必填项

### 生成阶段

- `swagger_path`: OpenAPI/Swagger 文件路径。
- `workspace`: 隔离工作目录。

### 执行阶段

- `service_url`: 目标服务基地址。
- `confirm_execute`: 明确的用户确认。

## 可选项

- `spec_path`: SPEC 或需求说明文档。用于提取业务关键词和优先场景。
- `max_operations`: 最多生成多少个候选测试，默认 8。
- `timeout_seconds`: 请求超时，默认 10 秒。

## 校验顺序

1. 检查 `swagger_path` 是否存在。
2. 检查 `workspace` 是否可创建或可写入。
3. 如果用户要求执行，检查 `service_url` 是否存在。
4. 如果 `spec_path` 存在，读取它；不存在时继续执行，但在结果里加入 warning。

## 路径约定

所有输出都写到：

`<workspace>/smoke-test/`

其中至少包含：

- `tests/test_smoke_generated.py`
- `smoke_manifest.json`
- `smoke_result.json`，仅执行后存在
- `pytest.log`，仅执行后存在

## 缺失输入时的行为

- 缺少 `swagger_path`: 直接失败。
- 缺少 `workspace`: 直接失败。
- 缺少 `service_url`: 如果是执行请求，则降级为只生成。
- 缺少 `spec_path`: 允许继续，但在结果中说明“未使用 SPEC 进行场景筛选”。