---
name: smoke-test
description: 从 SPEC 与 OpenAPI/Swagger 生成最小可执行的冒烟测试，并在用户确认后对目标服务执行。Use when 用户提到“执行冒烟测试”、“发布后验证”、“部署后检查”、“根据 Swagger 生成 smoke case”。不负责完整回归测试、性能测试或安全测试。
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: testing
---

# Smoke Test

为已部署服务生成最小可执行的 smoke cases，并在确认后运行。这个 skill 默认优先保证隔离性、可解释性和低风险，而不是覆盖率最大化。

## Quick Reference

| 用户需要 | 你应该做什么 | 需要加载的资源 |
|---|---|---|
| 只想根据 SPEC/Swagger 生成用例 | 只生成测试文件与清单，不执行请求 | 当需要校验参数与产物位置时，加载 `references/input_contract.md` 获取输入契约与目录约定 |
| 想在部署后做一次最小验证 | 先校验输入与环境，再生成测试；只有在用户明确同意后才执行 | 当需要决定是否允许执行时，加载 `references/execution_policy.md` 获取安全边界与确认规则 |
| 不确定哪些接口适合做 smoke test | 按优先级选择健康检查、只读、无路径参数、低鉴权依赖的端点 | 当需要选择或过滤端点时，加载 `references/openapi_scope.md` 获取筛选规则 |
| 需要稳定、可消费的结果 | 返回统一 JSON 摘要，并落盘到工作目录 | 当需要组织结果格式时，加载 `references/output_contract.md` 获取输出字段约定 |

## Default Workflow

1. 识别用户目标是“只生成”还是“生成并执行”。如果用户只说“生成冒烟用例”，不要默认执行。
2. 校验输入。优先确认 `swagger_path` 与 `workspace`；如果用户要求执行，再确认 `service_url`。当输入不完整时，加载 `references/input_contract.md`。
3. 如果用户提供参数样例表、Apifox 导出文档或其他带 `example` 的补充 OpenAPI，把它作为 `seed_path` 读取，用来补齐主 Swagger 中缺失的 query/header 样例。
4. 评估执行风险。任何会请求真实服务的动作都必须先经过用户明确确认。执行前加载 `references/execution_policy.md`。
5. 解析 OpenAPI/Swagger，并从 SPEC 中提取业务关键词，用于帮助筛选更有代表性的端点。端点筛选规则见 `references/openapi_scope.md`。
6. 使用 `scripts/generate_smoke_tests.py` 在隔离目录生成测试产物。不要写入项目根目录下的 `tests/`。
7. 如果用户确认执行，再使用 `scripts/run_smoke_tests.py` 运行 pytest，并把结果写入工作目录。
8. 按 `references/output_contract.md` 返回统一 JSON，并附带关键文件路径、跳过原因和下一步建议。

## Contract References

- 当需要确认必填参数、输出目录、缺失输入时的降级策略：
  -> 加载 `references/input_contract.md` 获取输入契约、路径约定和降级规则。
- 当需要决定哪些 OpenAPI 端点适合纳入 smoke 集：
  -> 加载 `references/openapi_scope.md` 获取端点优先级、默认跳过规则和候选集策略。
- 当用户要求直接跑测试，或目标地址看起来像真实部署环境：
  -> 加载 `references/execution_policy.md` 获取执行前确认项、禁止行为和降级规则。
- 当需要返回统一 JSON，或把结果接入其他自动化流程：
  -> 加载 `references/output_contract.md` 获取顶层字段、数组项格式和失败场景要求。

## Required Inputs

- `swagger_path`: 必填。OpenAPI/Swagger 文件路径，支持 JSON；YAML 需要环境中可导入 `yaml`。
- `workspace`: 必填。生成产物和日志写入的隔离目录。
- `spec_path`: 可选。需求设计文档路径。缺失时允许继续，但需要在输出中说明场景筛选退化为仅依据 OpenAPI。
- `seed_path`: 可选。参数样例表或补充 OpenAPI，用于补齐主 Swagger 缺失的 query/header 样例。
- `service_url`: 执行时必填。仅生成时可省略。
- `confirm_execute`: 执行时必需为真。没有明确确认时只能生成，不得执行。

## Execution Rules

- 默认只生成，不执行。
- 默认不安装依赖；如果缺少 `pytest` 或 `yaml`，应在结果中报出缺失项，而不是直接修改环境。
- 默认不写项目正式测试目录；所有产物写入 `workspace/smoke-test/`。
- 默认不请求高风险写操作接口。优先选择健康检查、状态查询、只读端点。
- 遇到鉴权、路径参数、复杂请求体或副作用明显的接口时，优先跳过并给出原因，不要猜测参数。
- 遇到必填 query 参数但文档没有 `example`、`default`、`const` 或 `enum` 时，默认跳过，不要自行捏造请求值。
- 如果主 Swagger 缺少必填 query/header 样例，但 `seed_path` 能提供同 path+method 或后缀匹配接口的样例，可优先使用 seed 补齐后再生成请求。
- 如果 OpenAPI 无法解析或没有适合的候选端点，仍要生成结果清单与失败原因，不能静默结束。

## Script Entry Points

生成阶段：

```bash
python scripts/generate_smoke_tests.py \
  --swagger-path api/openapi.json \
  --workspace .tmp/smoke \
  --spec-path docs/spec.md \
  --seed-path test/test_data.json
```

执行阶段：

```bash
python scripts/run_smoke_tests.py \
  --workspace .tmp/smoke \
  --service-url https://example.com \
  --execute
```

## Output Rules

始终返回一个结构化摘要，至少包含：

- `status`: `generated`、`executed`、`failed` 之一
- `executed`: 是否真的发起了测试执行
- `workspace`: 产物目录
- `test_file`: 生成的 pytest 文件路径
- `manifest_file`: 生成的清单文件路径
- `result_file`: 执行结果文件路径；仅执行后存在
- `selected_operations`: 被纳入 smoke test 的端点摘要
- `skipped_operations`: 被跳过的端点与原因
- `warnings`: 风险或退化行为说明
- `next_steps`: 建议用户下一步做什么

字段细则见 `references/output_contract.md`。

## Failure Handling

- `swagger_path` 不存在或不可解析：停止执行，返回 `failed` 与解析错误。
- `pytest` 不可用：生成测试文件，但不执行；在结果中标记缺失依赖。
- `service_url` 缺失：允许生成，但不执行。
- 所有候选端点都不可安全执行：生成仅包含跳过项的测试清单，并说明为什么无法形成可执行 smoke 集。

## Example

用户说：“执行冒烟测试，SPEC 在 docs/spec.md，Swagger 在 api/swagger.yaml，部署地址是 staging.example.com。”

你应该：

1. 先确认是否允许请求该地址。
2. 校验输入与环境。
3. 生成隔离目录下的测试文件与 manifest。
4. 只有在用户确认后才运行 pytest。
5. 返回统一 JSON 摘要，而不是只给自然语言描述。