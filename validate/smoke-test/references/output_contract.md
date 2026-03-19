# Output Contract

这个 skill 的最终结果应该既能给人看，也能被其他流程消费。

## 顶层字段

```json
{
  "status": "generated",
  "executed": false,
  "workspace": "/abs/path/.tmp/smoke/smoke-test",
  "test_file": "/abs/path/.tmp/smoke/smoke-test/tests/test_smoke_generated.py",
  "manifest_file": "/abs/path/.tmp/smoke/smoke-test/smoke_manifest.json",
  "result_file": null,
  "selected_operations": [],
  "skipped_operations": [],
  "warnings": [],
  "next_steps": []
}
```

## 字段说明

- `status`: `generated`、`executed`、`failed`
- `executed`: 布尔值，表示是否真的运行了 pytest
- `workspace`: smoke 工作目录的绝对路径
- `test_file`: 生成的 pytest 文件
- `manifest_file`: 记录候选端点、跳过原因和筛选依据的 JSON 文件
- `result_file`: 运行结果 JSON；未执行时为 `null`
- `selected_operations`: 被纳入 smoke test 的接口摘要数组
- `skipped_operations`: 被跳过的接口摘要数组，必须包含 `reason`
- `warnings`: 风险、退化模式、依赖缺失等说明
- `next_steps`: 给用户的后续建议数组

## selected_operations 单项示例

```json
{
  "method": "GET",
  "path": "/health",
  "summary": "Health check",
  "score": 160
}
```

## skipped_operations 单项示例

```json
{
  "method": "POST",
  "path": "/orders",
  "summary": "Create order",
  "reason": "write_operation"
}
```

## 失败场景

如果生成或执行失败，仍然要返回同一套顶层字段，并补充：

- `error`: 简短错误描述
- `warnings`: 可继续调查的线索
- `next_steps`: 明确的修复建议