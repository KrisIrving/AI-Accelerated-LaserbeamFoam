# AI-Accelerated-LaserbeamFoam

本项目基于 [官方 LaserbeamFoam](https://github.com/laserbeamfoam/LaserbeamFoam)，目标是在保留高保真 LPBF 模型和数值校正能力的基础上开发可复现的 AI 加速求解器。

**用户已回传：两个独立求解器均编译通过；Plate2D 串行 A/B 均完成十步，263个日志事件相等，最终时刻13个关键场文件逐字节一致。全部输出与嵌套 uniform 状态的自动比较仍待完成，尚未登记整体数值等价 PASS。尚无 AI 算法。** Codex 不连接或操作工作站。

- [源码来源与版本状态](UPSTREAM_BASELINE.md)
- [用户回传的原生验证记录](docs/validation/RESULTS.md)
- [独立 aiLaserbeamFoam 与 Plate2D A/B 验证](docs/validation/PLATE2D_AB.md)
- [Ubuntu 首轮环境及编译验证](docs/validation/UBUNTU_2512.md)
- [官方小案例和后续 LPBF_small 验证](docs/validation/OFFICIAL_CASES.md)
- [回传格式](docs/validation/FEEDBACK.md)

官方 `README.md`、`LICENSE`、`Allwmake`、原求解器、库和教程原样保留。新增入口位于 `applications/solvers/aiLaserbeamFoam`；不是重命名已有二进制，也不替换原源码。两者当前只读共享原生库；未来改库必须先隔离目录和库名。

上游 GitHub OpenFOAM 构建/全教程 CI 保留为手动触发，避免提交自动启动完整仿真；自动 CI 只做脚本/源码一致性及比较器夹具检查，不运行 OpenFOAM。CI 成功不替代工作站验证。

自动 Markdown 检查只覆盖本项目新增文档；继承的官方 README/教程保持原样，不为修复其既有格式告警而改写。

## 分支及交付

- `main`：从上游基线直接建立，保留其祖先历史；接收经过审查的集成修改。
- `chore/bootstrap-ubuntu2512`：PR #1 已合并，已验证提交 `98f99de8` 保留在历史中。
- `feat/ai-laserbeamfoam-solver`：从 PR #1 的 merge commit 建立，交付独立入口和串行 A/B；不堆叠在未合并 PR 上。
- 后续 `fix/...`、`feat/...`、`experiment/...`：独立开发，经 Pull Request 合入；不会向官方上游推送。
- 测试或编译未验证时可以提交工具和文档，但必须明确记录未验证状态；不得把静态检查改写为运行通过。

当前不修改物理模型、数值方法、编译优化参数，不开发推理或性能埋点，不运行清理、DEM或长时段仿真。本轮只做串行 A/B，MPI 与 LPBF 留待此关通过后安排。

## 私有验证数据

本地使用 `validation/` 保存审计、编译日志、隔离安装；使用 `runs/` 保存隔离案例。两者均忽略。不得将主机详情、未审阅日志、压缩反馈包或 CFD 输出加入公开提交。

开源源码延续原 `LICENSE`；以后发布的模型、训练数据和外部依赖还需分别记录来源及可发布条件。
