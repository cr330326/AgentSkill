# 版本发布流水线

## 适用场景

软件版本发布时使用：npm 包、PyPI 包、Docker 镜像、GitHub Release、
移动应用上架等。发布操作不可逆（尤其是公开仓库的版本号），
流水线确保每一步都经过确认，避免发错版本。

## 阶段定义

### 阶段 1: 发布前检查 [CHECKPOINT]

- **目标**: 确认代码和环境已经准备好发布
- **输入**: 当前代码库状态
- **操作**:
  1. 检查当前分支是否正确（通常是 main/master 或 release 分支）
  2. 检查是否有未提交的变更（`git status` 应干净）
  3. 检查是否有未合并的 PR/MR
  4. 运行完整测试套件，确认全部通过
  5. 检查 lint/类型检查是否通过
  6. 确认 CI/CD 管道最近一次运行是否成功
- **输出**: 发布前检查报告（通过/失败项列表）
- **检查要点**: 所有检查是否通过？失败项是否可以接受？

### 阶段 2: 版本号确定 [CHECKPOINT]

- **目标**: 确定新版本号和更新日志
- **输入**: 阶段 1 通过确认
- **操作**:
  1. 查看当前版本号
  2. 分析自上次发布以来的 commit 历史
  3. 根据变更类型建议版本号（遵循 semver）：
     - 破坏性变更 → major（x.0.0）
     - 新功能 → minor（0.x.0）
     - 修复/优化 → patch（0.0.x）
  4. 生成 CHANGELOG 草稿
  5. 更新版本号文件（package.json / pyproject.toml / Cargo.toml 等）
- **输出**: 新版本号 + CHANGELOG 草稿
- **检查要点**: 版本号是否合适？CHANGELOG 内容是否准确完整？

### 阶段 3: 构建和打包

- **目标**: 构建发布产物
- **输入**: 阶段 2 确认的版本号
- **操作**:
  1. 执行构建命令（`npm run build` / `python -m build` / `cargo build --release` 等）
  2. 验证构建产物完整性（文件大小、文件列表）
  3. 如果有 Docker 镜像，构建并打 tag
  4. 如果有二进制产物，为各平台构建
- **输出**: 构建产物列表（文件名、大小、hash）

### 阶段 4: 发布确认 [CHECKPOINT]

- **目标**: 最终确认，执行发布
- **输入**: 阶段 3 的构建产物
- **操作**:
  1. 展示即将发布的内容摘要：
     - 版本号
     - 包含的变更
     - 构建产物列表
     - 发布目标（npm / PyPI / Docker Hub / GitHub 等）
  2. **明确警告**：此操作发布后不可撤回（或撤回成本很高）
  3. 等待用户最终确认
- **输出**: 确认摘要
- **检查要点**: 发布内容是否正确？是否准备好发布到生产？

### 阶段 5: 执行发布

- **目标**: 执行实际的发布操作
- **输入**: 阶段 4 的最终确认
- **操作**:
  1. 发布到包管理器（`npm publish` / `twine upload` / `cargo publish` 等）
  2. 创建 Git tag（`git tag v<version>`）
  3. 推送 tag 到远端（`git push origin v<version>`）
  4. 如果有 GitHub Release，创建 Release 并上传资产
  5. 如果有 Docker 镜像，推送到 registry
- **输出**: 发布确认（包含发布链接/URL）

### 阶段 6: 发布后验证

- **目标**: 验证发布成功
- **输入**: 阶段 5 的发布确认
- **操作**:
  1. 验证包管理器上能否正常安装新版本
  2. 检查 release notes 是否正确显示
  3. 如果有 CI/CD 自动触发的后续流程，确认是否正常启动
  4. 通知相关人员/频道（如 Slack 通知）
- **输出**: 发布完成报告

## 各平台发布命令速查

| 平台 | 发布命令 | 版本号文件 |
|------|---------|-----------|
| npm | `npm publish` | `package.json` |
| PyPI | `twine upload dist/*` | `pyproject.toml` / `setup.py` |
| Cargo | `cargo publish` | `Cargo.toml` |
| Docker | `docker push <image>:<tag>` | `Dockerfile` |
| GitHub | `gh release create v<ver>` | N/A |

## 注意事项

- **dry run 优先**：发布命令如果支持 `--dry-run`，先执行一次干跑确认无误
- **发错版本**：npm 可以 `npm unpublish`（72小时内）或 `npm deprecate`；PyPI 可以 yank；Docker 可以删 tag。但最佳策略是发一个新的修复版本而非撤回
- **预发布版本**：对于不确定的版本，使用 prerelease 标记（如 `1.2.0-beta.1`），这样不会影响使用 `^` 或 `~` 的用户
- **monorepo**：如果是 monorepo，需要确认哪些包需要发布，以及包间依赖版本是否同步更新
