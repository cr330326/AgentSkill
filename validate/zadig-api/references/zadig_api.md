# Zadig OpenAPI 参考文档

本文档提供 Zadig DevOps 平台 OpenAPI 的详细参考信息，基于 Zadig v4.1 官方文档。

## 认证方式

### 获取 API Token

1. 登录 Zadig 平台
2. 点击右上角用户名
3. 选择"账号设置"
4. 复制 API Token

### 请求头格式

所有 API 请求需要在 HTTP Header 中包含 Authorization：

```
Authorization: Bearer <your-api-token>
Content-Type: application/json
```

## 项目相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 获取项目列表 | GET | `/openapi/projects/project?pageSize=20&pageNum=1` |
| 获取项目详情 | GET | `/openapi/projects/project/detail?projectKey=<key>` |
| 创建空项目 | POST | `/openapi/projects/project` |
| 创建 YAML 项目并初始化 | POST | `/openapi/projects/project/init/yaml` |
| 创建 Helm 项目并初始化 | POST | `/openapi/projects/project/init/helm` |
| 删除项目 | DELETE | `/openapi/projects/project?projectKey=<key>&isDelete=true` |

### 获取项目列表

```http
GET /openapi/projects/project?pageSize=20&pageNum=1
```

**查询参数：**
- `pageSize` (int, optional): 每页显示数量，默认 20
- `pageNum` (int, optional): 当前页数，默认 1

**响应示例：**
```json
{
  "total": 14,
  "projects": [
    {
      "project_name": "my-project",
      "project_key": "my-project",
      "description": "项目描述",
      "deploy_type": "k8s"
    }
  ]
}
```

### 获取项目详情

```http
GET /openapi/projects/project/detail?projectKey=<key>
```

## 工作流相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 获取工作流列表 | GET | `/openapi/workflows?projectKey=<key>&viewName=<view>` |
| 获取工作流详情 | GET | `/openapi/workflows/custom/:workflowKey/detail?projectKey=<key>` |
| 执行工作流 | POST | `/openapi/workflows/custom/task` |
| 获取工作流任务状态 | GET | `/openapi/workflows/custom/task?taskId=<id>&workflowKey=<key>` |
| 获取工作流任务列表 | GET | `/openapi/workflows/custom/:workflowKey/tasks?projectKey=<key>` |
| 取消工作流任务 | DELETE | `/openapi/workflows/custom/task?taskId=<id>&workflowKey=<key>` |
| 重试工作流任务 | POST | `/openapi/workflows/custom/:workflowKey/task/:taskID` |
| 审批工作流 | POST | `/openapi/workflows/custom/task/approve` |
| 创建工作流 | POST | `/api/aslan/workflow/v4` |
| 更新工作流 | PUT | `/api/aslan/workflow/v4/:name` |
| 删除工作流 | DELETE | `/openapi/workflows/custom` |

### 获取工作流列表

```http
GET /openapi/workflows?projectKey=<key>&viewName=<view>
```

**查询参数：**
- `projectKey` (string, required): 项目标识
- `viewName` (string, optional): 工作流视图名称

**响应示例：**
```json
{
  "workflows": [
    {
      "workflow_key": "build-deploy",
      "workflow_name": "build-deploy",
      "update_by": "admin",
      "update_time": 1686217885,
      "type": "custom"
    }
  ]
}
```

### 执行工作流

```http
POST /openapi/workflows/custom/task
```

**请求体：**
```json
{
  "project_key": "my-project",
  "workflow_key": "build-deploy",
  "parameters": [
    {
      "name": "branch",
      "type": "string",
      "value": "main"
    }
  ],
  "inputs": [
    {
      "job_name": "build",
      "job_type": "zadig-build",
      "parameters": {
        "registry": "https://registry.example.com",
        "service_list": [...]
      }
    }
  ]
}
```

**响应示例：**
```json
{
  "project_name": "my-project",
  "workflow_name": "build-deploy",
  "task_id": 12345
}
```

### 获取工作流任务状态

```http
GET /openapi/workflows/custom/task?taskId=12345&workflowKey=build-deploy
```

**查询参数：**
- `taskId` (int, required): 工作流任务 ID
- `workflowKey` (string, required): 工作流标识

### 取消工作流任务

```http
DELETE /openapi/workflows/custom/task?taskId=12345&workflowKey=build-deploy
```

## 工作流视图相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 获取工作流视图列表 | GET | `/openapi/workflows/view?projectKey=<key>` |
| 创建工作流视图 | POST | `/openapi/workflows/view` |
| 编辑工作流视图 | PUT | `/openapi/workflows/view/:viewName` |
| 删除工作流视图 | DELETE | `/openapi/workflows/view/:viewName` |

## 环境相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 查看测试环境列表 | GET | `/openapi/environments` |
| 查看生产环境列表 | GET | `/openapi/environments/production` |
| 查看环境详情 | GET | `/openapi/environments/:envName` |
| 查看生产环境详情 | GET | `/openapi/environments/production/:envName` |
| 新建测试环境 | POST | `/openapi/environments` |
| 新建生产环境 | POST | `/openapi/environments/production` |
| 编辑环境 | PUT | `/openapi/environments/:envName` |
| 删除环境 | DELETE | `/openapi/environments/:envName` |
| 更新 Deployment 镜像 | POST | `/openapi/environments/image/deployment/:envName` |
| 重启服务实例 | POST | `/openapi/environments/:envName/service/:serviceName/restart` |

## 服务相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 获取测试服务列表 | GET | `/openapi/service/yaml/services` |
| 获取生产服务列表 | GET | `/openapi/service/yaml/production/services` |
| 获取服务详情 | GET | `/openapi/service/yaml/:serviceName` |
| 新建服务 | POST | `/openapi/service/yaml/raw` |
| 更新服务配置 | PUT | `/openapi/service/yaml/:serviceName` |
| 删除服务 | DELETE | `/openapi/service/yaml/:serviceName` |

## 构建相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 使用构建模板创建构建 | POST | `/openapi/build` |
| 查询构建列表 | GET | `/openapi/build` |
| 获取构建详情 | GET | `/openapi/build/:buildName/detail` |
| 删除构建 | DELETE | `/openapi/build` |

## 测试相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 执行测试任务 | POST | `/openapi/quality/testing/task` |
| 获取测试任务详情 | GET | `/openapi/quality/testing/:testName/task/:taskID` |

## 代码扫描相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 创建代码扫描 | POST | `/openapi/quality/codescan` |
| 执行代码扫描任务 | POST | `/openapi/quality/codescan/:scanName/task` |
| 获取代码扫描任务详情 | GET | `/openapi/quality/codescan/:scanName/task/:taskID` |

## 版本管理相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 列出版本 | GET | `/openapi/delivery/releases` |
| 获取版本详情 | GET | `/openapi/delivery/releases/:id` |
| 删除版本 | DELETE | `/openapi/delivery/releases/:id` |
| K8s YAML 项目创建版本 | POST | `/openapi/delivery/releases/k8s` |
| Helm Chart 项目创建版本 | POST | `/openapi/delivery/releases/helm` |
| 重试创建版本 | POST | `/openapi/delivery/releases/retry` |

## 发布计划相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 创建发布计划 | POST | `/openapi/release_plan/v1` |
| 获取发布计划列表 | GET | `/openapi/release_plan/v1` |
| 获取发布计划详情 | GET | `/openapi/release_plan/v1/:id` |
| 更新发布计划 | PATCH | `/openapi/release_plan/v1/:id` |

## 集群相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 列出集群信息 | GET | `/openapi/system/cluster` |
| 创建集群 | POST | `/openapi/system/cluster` |
| 更新指定集群 | PUT | `/openapi/system/cluster/:id` |
| 删除指定集群 | DELETE | `/openapi/system/cluster/:id` |

## 镜像仓库相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 集成镜像仓库 | POST | `/openapi/system/registry` |
| 列出镜像仓库信息 | GET | `/openapi/system/registry` |
| 获取指定镜像仓库信息 | GET | `/openapi/system/registry/:id` |
| 更新指定镜像仓库信息 | PUT | `/openapi/system/registry/:id` |

## 效能洞察相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 数据概览 | GET | `/openapi/statistics/overview` |
| 构建数据统计 | GET | `/openapi/statistics/build` |
| 部署数据统计 | GET | `/openapi/statistics/deploy` |
| 测试数据统计 | GET | `/openapi/statistics/test` |
| 生产环境发布数据统计 | GET | `/openapi/statistics/v2/release` |

## 用户及权限相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 列出用户信息 | GET | `/openapi/users` |
| 列出用户组信息 | GET | `/openapi/user-groups` |
| 列出项目权限定义 | GET | `/openapi/policy/resource-actions` |
| 列出角色信息 | GET | `/openapi/policy/roles` |
| 获取角色详情 | GET | `/openapi/policy/roles/:name` |
| 创建项目角色 | POST | `/openapi/policy/roles` |
| 编辑项目角色 | PUT | `/openapi/policy/roles/:name` |
| 删除项目角色 | DELETE | `/openapi/policy/roles/:name` |
| 列出项目成员 | GET | `/openapi/policy/role-bindings` |
| 增加项目成员 | POST | `/openapi/policy/role-bindings` |
| 删除项目成员 | DELETE | `/openapi/policy/role-bindings/user/:uid` |

## 系统相关 API

| 功能 | HTTP 方法 | Endpoint |
|------|-----------|----------|
| 列出系统操作日志 | GET | `/openapi/system/operation` |
| 列出环境操作日志 | GET | `/openapi/system/operation/env` |

## 响应格式

所有 API 响应均为 JSON 格式。成功响应通常返回 HTTP 200 状态码。

### 错误响应格式

```json
{
  "code": 400,
  "description": "错误描述",
  "message": "Bad Request",
  "type": "error"
}
```

## 常见 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（API Token 无效） |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 使用示例

### 使用 Python 脚本

```bash
# 设置环境变量
export ZADIG_ENDPOINT="https://zadig.example.com"
export ZADIG_API_TOKEN="your-api-token"

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
```

### 通用 API 调用

```bash
# 自定义 GET 请求
python scripts/zadig_client.py api-call GET "/openapi/workflows" \
  --params '{"projectKey": "my-project"}'

# 自定义 POST 请求
python scripts/zadig_client.py api-call POST "/openapi/workflows/custom/task" \
  --data '{"project_key": "my-project", "workflow_key": "build"}'
```

## 参考资源

- [Zadig 官方文档](https://docs.koderover.com/zadig/)
- [Zadig v4.1 API 使用指南](https://docs.koderover.com/zadig/cn/Zadig%20v4.1/api/usage/)
- [Zadig v4.1 工作流 API](https://docs.koderover.com/zadig/cn/Zadig%20v4.1/api/workflow/)
- [Zadig v4.1 项目 API](https://docs.koderover.com/zadig/cn/Zadig%20v4.1/api/project/)
