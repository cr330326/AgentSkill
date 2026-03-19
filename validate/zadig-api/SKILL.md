---
name: zadig-api
description: 当需要调用 Zadig DevOps 平台的 OpenAPI 进行工作流触发、项目数据查询或管理操作时，使用此 skill。支持工作流执行、任务状态查询、项目列表获取等常用操作。
---

# Zadig API

## 概述

此 skill 提供与 Zadig DevOps 平台 OpenAPI 交互的能力，支持通过预配置的 endpoint 和 API token 进行 RESTful API 调用，返回格式化的 JSON 输出。Zadig 是一款开源的云原生 DevOps 平台，提供工作流编排、持续交付、环境管理等功能。

## 核心功能

### 1. 工作流管理

列出项目工作流、触发自定义工作流、查询工作流任务状态、取消运行中的任务。

**常见使用场景：**
- "触发 Zadig 项目的构建工作流"
- "查看工作流执行状态"
- "获取项目的工作流列表"

### 2. 项目管理

获取项目列表、查询项目详情。

**常见使用场景：**
- "列出所有 Zadig 项目"
- "获取项目详细信息"

### 3. 通用 API 调用

支持任意 HTTP 方法 (GET/POST/PUT/DELETE/PATCH)，可自定义请求参数和请求体。

**常见使用场景：**
- "调用 Zadig 的 XXX 接口"
- "执行自定义的 API 请求"

## 配置

在调用前需要设置环境变量：

```bash
export ZADIG_ENDPOINT="https://your-zadig.example.com"
export ZADIG_API_TOKEN="your-api-token"
```

获取 API Token：登录 Zadig 平台 → 点击右上角用户名 → 选择"账号设置" → 复制 API Token

## 使用方式

### 通过 Claude 调用

直接告诉 Claude 需要执行的 Zadig 操作，Claude 会使用脚本完成调用。

示例请求：
- "触发 my-project 项目的 build-deploy 工作流"
- "查询任务 12345 的状态"
- "列出所有工作流"

### 通过脚本直接调用

```bash
# 获取工作流列表
python scripts/zadig_client.py list-workflows-full --project-key my-project

# 触发工作流
python scripts/zadig_client.py trigger-workflow \
  --project-key my-project \
  --workflow-key build-deploy

# 查询任务状态
python scripts/zadig_client.py get-task-status \
  --task-id 12345 \
  --workflow-key build-deploy

# 列出所有项目
python scripts/zadig_client.py list-projects

# 自定义 API 调用
python scripts/zadig_client.py api-call GET "/openapi/workflows" \
  --params '{"projectKey": "my-project"}'
```

### 脚本完整参数

```bash
python scripts/zadig_client.py --help
```

全局选项：
- `--endpoint`: Zadig API 端点 URL
- `--token`: Zadig API token
- `--no-verify-ssl`: 禁用 SSL 验证
- `--output`: 输出格式 (json/pretty)
- `--timeout`: 请求超时时间（秒）

可用命令：
- `list-workflows-full`: 列出项目工作流
- `list-projects`: 列出所有项目
- `trigger-workflow`: 触发工作流
- `get-task-status`: 获取任务状态
- `list-workflow-tasks`: 获取工作流任务历史
- `cancel-task`: 取消任务
- `get-workflow`: 获取工作流详情
- `get-project`: 获取项目详情
- `api-call`: 自定义 API 调用

## 资源

- **scripts/zadig_client.py**: Python API 客户端，包含所有 Zadig API 交互逻辑
- **references/zadig_api.md**: 详细的 API endpoint 参考文档，包含所有可用接口的说明

## API 参考文档速查

### 工作流相关

| 操作 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 获取工作流列表 | GET | `/openapi/workflows?projectKey=<key>` |
| 获取工作流详情 | GET | `/openapi/workflows/custom/:workflowKey/detail` |
| 触发工作流 | POST | `/openapi/workflows/custom/task` |
| 获取任务状态 | GET | `/openapi/workflows/custom/task?taskId=<id>&workflowKey=<key>` |
| 获取任务历史 | GET | `/openapi/workflows/custom/:workflowKey/tasks` |
| 取消任务 | DELETE | `/openapi/workflows/custom/task?taskId=<id>&workflowKey=<key>` |

### 项目相关

| 操作 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 获取项目列表 | GET | `/openapi/projects/project` |
| 获取项目详情 | GET | `/openapi/projects/project/detail?projectKey=<key>` |

更多详细信息请参阅 `references/zadig_api.md`。
