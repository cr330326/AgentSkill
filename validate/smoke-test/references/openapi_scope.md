# OpenAPI Scope

这个 skill 不是完整回归测试生成器。它只负责从 OpenAPI 中挑出最适合做 smoke test 的最小集合。

## 端点优先级

优先选择以下端点：

1. 健康检查或状态检查：`/health`、`/ready`、`/live`、`/status`、`/ping`
2. 无副作用的只读端点：`GET`、`HEAD`、`OPTIONS`
3. 无路径参数、无复杂请求体的端点
4. 与 SPEC 关键词更接近的端点

## 默认跳过

默认跳过以下端点，除非用户明确要求：

- 明显写操作：`POST`、`PUT`、`PATCH`、`DELETE`
- 带路径参数但没有默认样例值的端点
- 带必填 query 参数但没有 `example`、`default`、`const` 或 `enum` 可用值的端点
- 带必填 header 参数且主 Swagger 与 seed 文档都无法提供样例值的端点
- 需要鉴权但未提供鉴权信息的端点
- 需要复杂请求体、文件上传、多段表单的端点

## 候选集策略

- 默认最多保留 8 个端点。
- 至少包含 1 个健康类端点；如果没有，说明原因。
- 如果找不到可安全执行的端点，也要生成 manifest，并把所有候选放进 `skipped_operations`。
- 如果主 Swagger 缺少样例，但 `seed_path` 中存在同 path+method 或后缀匹配的接口定义，可用 seed 补齐 query/header 样例。

## SPEC 的作用

SPEC 只用于帮助排序，不应覆盖 OpenAPI 的事实定义。

- 如果 SPEC 中反复出现“登录”“订单”“支付”这类关键词，可优先保留与这些关键词匹配的只读或低风险端点。
- 如果 SPEC 与 OpenAPI 冲突，以 OpenAPI 的字段和路径为准。

## 不负责的范围

- 完整端到端回归
- 性能压测
- 安全扫描
- 复杂鉴权流程编排
