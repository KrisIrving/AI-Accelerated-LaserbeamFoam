# AI-Accelerated-LaserbeamFoam

本项目基于 [官方 LaserbeamFoam](https://github.com/laserbeamfoam/LaserbeamFoam)，目标是在保留高保真 LPBF 模型和数值校正能力的基础上开发可复现的 AI 加速求解器。

**当前仅完成工程引导，尚未开发 AI；Ubuntu 22.04 + OpenFOAM.com v2512 的编译、运行和数值精度均待工作站验证。** Codex 不连接或操作工作站。

- [源码来源与版本状态](UPSTREAM_BASELINE.md)
- [Ubuntu 首轮环境及编译验证](docs/validation/UBUNTU_2512.md)
- [官方小案例和后续 LPBF_small 验证](docs/validation/OFFICIAL_CASES.md)
- [回传格式](docs/validation/FEEDBACK.md)

官方 `README.md`、`LICENSE`、`Allwmake`、求解器、库和教程原样保留。原版文档中的支持描述不等于本项目已验证的支持状态。

上游 GitHub OpenFOAM 构建/全教程 CI 保留为手动触发，避免引导提交自动启动完整仿真；新 CI 只检查 Bash 语法与审计夹具，不运行 OpenFOAM。CI 成功不替代工作站验证。

自动 Markdown 检查只覆盖本项目新增文档；继承的官方 README/教程保持原样，不为修复其既有格式告警而改写。

## 分支及交付

- `main`：从上游基线直接建立，保留其祖先历史；接收经过审查的集成修改。
- `chore/bootstrap-ubuntu2512`：本轮审计、验证说明和反馈工具；合并前可直接检出该分支测试。
- 后续 `fix/...`、`feat/...`、`experiment/...`：独立开发，经 Pull Request 合入；不会向官方上游推送。
- 测试或编译未验证时可以提交工具和文档，但必须明确记录未验证状态；不得把静态检查改写为运行通过。

第一轮不修改物理模型、数值方法、编译优化参数，不运行 `Allwclean`、`Allclean`、DEM 或完整长时段仿真。CPU + MPI 优先；是否有 GPU 由审计确认。

## 私有验证数据

本地使用 `validation/` 保存审计、编译日志、隔离安装；使用 `runs/` 保存隔离案例。两者均忽略。不得将主机详情、未审阅日志、压缩反馈包或 CFD 输出加入公开提交。

开源源码延续原 `LICENSE`；以后发布的模型、训练数据和外部依赖还需分别记录来源及可发布条件。
