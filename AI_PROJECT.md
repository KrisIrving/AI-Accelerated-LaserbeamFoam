# AI-Accelerated-LaserbeamFoam

本项目基于 [官方 LaserbeamFoam](https://github.com/laserbeamfoam/LaserbeamFoam)，目标是在保留高保真 LPBF 模型和数值校正能力的基础上开发可复现的 AI 加速求解器。

**用户已回传 Plate2D 串行 A/B 数值等价性 PASS：3,200单元、10步、263个日志事件、30/30物理场及嵌套 uniform 均通过，Issues=0。最终比较器为 `baeb8107`；实际构建/求解 SHA 待原 manifest 与构建摘要补录。MPI、三维 LPBF、物理精度及加速性能仍未验证。尚无 AI 算法。** Codex 不连接或操作工作站。

- [项目资料入口：当前状态、下一步、证据与完整导航](docs/PROJECT_HUB.md)
- [源码来源与版本状态](UPSTREAM_BASELINE.md)
- [用户回传的原生验证记录](docs/validation/RESULTS.md)
- [独立 aiLaserbeamFoam 与 Plate2D A/B 验证](docs/validation/PLATE2D_AB.md)
- [Ubuntu 首轮环境及编译验证](docs/validation/UBUNTU_2512.md)
- [官方小案例和后续 LPBF_small 验证](docs/validation/OFFICIAL_CASES.md)
- [回传格式](docs/validation/FEEDBACK.md)
- [受控研究章程](docs/research/RESEARCH_CHARTER.md)
- [正式开发计划](docs/research/DEVELOPMENT_PLAN.md)
- [基准候选与Ubuntu分阶段命令](docs/research/BENCHMARK_DESIGN.md)
- [追加式决策记录](docs/research/DECISION_LOG.md)
- [追加式实验记录](docs/research/EXPERIMENT_LOG.md)
- [S首次运行核对与最小反馈](docs/validation/THREED_SMOKE_FIRST_RUN.md)
- [M1/M2/M3分级探索与Ubuntu执行](docs/validation/THREED_M_EXPLORATION.md)
- [M1结果离线复核与条件性M3预检](docs/validation/M1_RECHECK_M3_PREFLIGHT.md)
- [M1–M3原场只读空间比较与反馈](docs/validation/M1_M3_SPATIAL_COMPARISON.md)
- [实验文献及V验证候选（非受控、PROPOSED）](docs/research/LITERATURE_VALIDATION_CANDIDATES.md)

官方 `README.md`、`LICENSE`、`Allwmake`、原求解器、库和教程原样保留。新增入口位于 `applications/solvers/aiLaserbeamFoam`；不是重命名已有二进制，也不替换原源码。两者当前只读共享原生库；未来改库必须先隔离目录和库名。

上游 GitHub OpenFOAM 构建/全教程 CI 保留为手动触发，避免提交自动启动完整仿真；自动 CI 只做脚本/源码一致性及比较器夹具检查，不运行 OpenFOAM。CI 成功不替代工作站验证。

自动 Markdown 检查只覆盖本项目新增文档；继承的官方 README/教程保持原样，不为修复其既有格式告警而改写。

## 分支及交付

- `main`：从上游基线直接建立，保留其祖先历史；接收经过审查的集成修改。
- `chore/bootstrap-ubuntu2512`：PR #1 已合并，已验证提交 `98f99de8` 保留在历史中。
- `feat/ai-laserbeamfoam-solver`：从 PR #1 的 merge commit 建立，交付独立入口和串行 A/B；不堆叠在未合并 PR 上。
- PR #2 已由用户合并（`532ed068`）；随后从更新的main建立 `feat/research-plan-smoke-benchmark`，交付PR #3。
- PR #3 已由负责人合并（`5e08097d`）；新的 `feat/threeD-progressive-m-exploration` 从最新main开发DEC-006授权的M1/M2/M3探索，通过[Draft PR #4](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/pull/4)交付，不自动合并。原研究顺序与正式M待批准状态不变。
- 后续 `fix/...`、`feat/...`、`experiment/...`：独立开发，经 Pull Request 合入；不会向官方上游推送。
- 测试或编译未验证时可以提交工具和文档，但必须明确记录未验证状态；不得把静态检查改写为运行通过。

当前正式路线（负责人2026-10-16明确批准）：阶段0串行基线COMPLETED；阶段1低成本三维开发案例CURRENT；阶段2真实剖析、阶段3一个AI模块、阶段4代表性粉末床PLANNED。取消固定MPI矩阵与MPI前置门槛，保留定向并行验证和既有风险记录。不修改物理模型/优化等级，本轮不开发AI或埋点。S仅为已实测探针；M1/M2/M3探索开发按DEC-006获准，正式M/粉末选型未批准。M1/M3实测见EXP-002/003，M2仍UNVERIFIED。

正式目标/路线/精度/基准变更须负责人显式批准并追加DECISION_LOG；聊天建议不自动改计划。新任务先读取根AGENTS.md、PROJECT_HUB和研究章程/计划，再读相关源码及详细文档，不能依赖会话记忆。

阶段1用户实测：threeD-smoke-002 的三维基础检查 SMOKE_CHECKS_PASSED，2048单元、10步；用户提供的ChatGPT归档核验结果补齐源/构建SHA为7c094679016a2458282c9fcb261d7d55983496bb，归档COMPLETE、记录RECORDS_MATCH。Codex未取得原包；记录匹配不等于重验二进制/动态依赖。未观察到熔化，物理精度与热点剖析未建立。来源及界限见[EXP-001和ADD-01](docs/research/EXPERIMENT_LOG.md)，不据此批准M或完成阶段1。

M1已真实完成32000单元/1000步，观察到熔化；solver墙钟214.50秒、最大RSS240452 KiB。2026-10-17补录用户提供的ChatGPT核验：工具b5e429b1复核10时刻/190场及10个uniform/cumulativeContErr全部PASS，约96.63秒。新包非Codex直接核验，不含原场或前后SHA快照，不能独立认证原场复核期间未变；原运行/构建仍1d32b6fd，原REVIEW历史保留。见[EXP-002及ADD-01](docs/research/EXPERIMENT_LOG.md)。阶段1未完成，正式M、物理精度、网格收敛及热点未建立。

最新M3已由用户实测完成并检查PASS：原生源/构建8f60695a，256000单元/1000步/10 μs，solver2872.64秒；数据及核验来自用户提供的ChatGPT结果，Codex未收到新包/原场。早期熔化/温度与M1差异显著，初始体积及界面离散混杂需先调查；当前下一步为[原场只读比较](docs/validation/M1_M3_SPATIAL_COMPARISON.md)，不重跑M1/M3，不运行M2。[短程新候选](docs/research/SHORT_GEOMETRY_DIAGNOSTIC_PROPOSAL.md)仅PROPOSED，无配置或执行；阶段1及原有物理/收敛/热点限制保持，详见EXP-003。

## 私有验证数据

本地使用 `validation/` 保存审计、编译日志、隔离安装；使用 `runs/` 保存隔离案例。两者均忽略。不得将主机详情、未审阅日志、压缩反馈包或 CFD 输出加入公开提交。

开源源码延续原 `LICENSE`；以后发布的模型、训练数据和外部依赖还需分别记录来源及可发布条件。
