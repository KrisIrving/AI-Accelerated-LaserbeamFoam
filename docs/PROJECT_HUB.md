# 项目资料入口 · AI-Accelerated-LaserbeamFoam

状态核对日期：2026-10-17。本页是导航与状态摘要，不替代正式计划或原始证据。各主题以导航表中的权威文件为准；发生冲突时回查正式文件和 Git 历史，不根据本页自行改计划。

## 目标与 Current Status

研究实质性的 AI 加速算法，保留高保真 LPBF CFD 的必要预测与数值能力，逐步交付可靠、可复现、可维护的开源 aiLaserbeamFoam。完整模拟约 2 倍、挑战 3 倍以上是长期愿景，尚无实测支持。完整定义见[研究章程](research/RESEARCH_CHARTER.md)。

| 项目 | 当前状态 | 依据 |
| --- | --- | --- |
| 正式阶段 | 阶段1：低成本三维开发案例，CURRENT / IN_PROGRESS | [开发计划](research/DEVELOPMENT_PLAN.md) |
| Plate2D 串行 A/B | 用户实测 PASS；仅当前短程数值等价 | [RESULTS](validation/RESULTS.md)、[EXP-000](research/EXPERIMENT_LOG.md) |
| 三维 S | 用户实测 SMOKE_CHECKS_PASSED；归档COMPLETE、源/构建记录RECORDS_MATCH；未观察到熔化；仍为 PROPOSED 探针 | [EXP-001及ADD-01](research/EXPERIMENT_LOG.md)、[首次实测说明](validation/THREED_SMOKE_FIRST_RUN.md) |
| M探索 | M1/M3基础运行及离线检查用户实测PASS，均观察熔化；早期空间敏感性显著，原场诊断已确认初始几何差异与早期沉积错层；单次M1-IC工具按DEC-007获批，实机UNVERIFIED。M2暂缓，正式M未批准 | [EXP-002/003](research/EXPERIMENT_LOG.md)、[跨网格离线比较](validation/M1_M3_SPATIAL_COMPARISON.md)、[DEC-006](research/DECISION_LOG.md) |
| 论文物理验证 V | 候选研究，PROPOSED；没有新增强制阶段或已实现案例 | [文献与实验候选库](research/LITERATURE_VALIDATION_CANDIDATES.md) |
| AI 模块 | NOT_STARTED；尚未选择或实现 | [开发计划](research/DEVELOPMENT_PLAN.md) |
| MPI 固定验证矩阵 | 已撤销为强制开发门槛；保留定向验证及已知风险 | [DEC-002](research/DECISION_LOG.md)、[MPI 风险](research/MPI_RISKS.md) |

## 已完成、正在执行与下一步

已完成的重要里程碑：独立 aiLaserbeamFoam 源码与编译入口；用户回传 v2512 双求解器编译及 Plate2D 串行短程 A/B PASS；正式研究治理文件；S 工具及文献候选库；用户回传 S 三维基础运行及自动归档验收。S归档核验来自用户提供的ChatGPT检查结果，Codex未取得原包，不能宣称直接核验。

当前执行：阶段1独立M1-IC受控探索工具开发与实机准备，见[DEC-007](research/DECISION_LOG.md)。M1/M3原场空间比较已由用户回传COMPARISON_COMPLETED；源数据与归档核验是用户提供的ChatGPT结果，Codex未取得该包/原场。S仍为2048单元/10步探针；阶段1整体尚未完成。

下一个可执行任务：按[M1-IC说明](validation/M1_IC_CONTROLLED_EXPERIMENT.md)，先新HEAD隔离构建、读取现有M1/M3生成限制参考，随后用户单独执行mesh并审阅受控alpha初始化，才启动唯一一次32000单元/300步/3 μs求解。之后全场离线检查/归档和三方1/2/3 μs比较。仅新案例alpha干预，原M1/M3只读；不自动重跑/续算/扩大规模。108000单元候选仍PROPOSED，M2暂缓，正式M未批准；不进入阶段2或开发AI。

当前待补证据与批准事项：

- S 用户提供的ChatGPT核验结果：23个归档文件/22条内部哈希、清单通过；源/构建完整SHA均为7c094679016a2458282c9fcb261d7d55983496bb。solver=0.35 s、最大RSS=127488 KiB，已记录流程范围1.919696505 s；归档标识和SHA256见EXP-001-ADD-01。RECORDS_MATCH不等于重验实际二进制和动态库，工具87061fe9不等于原运行版本。物理/性能证据缺口仍保留。
- Plate2D-ab-002 的实际构建/求解 SHA 待原 manifest 和构建摘要补录；不能用离线比较器提交替代。
- M1实测32000单元、1000步/10 μs，solver退出0，190场检查记录、29491日志事件；3 μs采样首次熔化，7 μs采样超过配置Tvap。原solver214.50 s、RSS240452 KiB、约121.05 MB数据与322.623874 s流程范围保持原记录。工具b5e429b1复核10时刻/190场和10个cumulativeContErr均PASS，离线约96.63 s；原95.90 s/REVIEW记录保留，来源及新包哈希见EXP-002-ADD-01。
- M3源/构建8f60695a，256000单元/1000步，190场及10时刻uniform通过；solver2872.64 s、RSS1104420 KiB、工作流范围3983.762 s、显式离线724.874 s、数据902667461字节。原生与后处理范围不混加。M3温度/起熔时序与M1差异显著，终点熔化区y有4层；不证明收敛或物理准确性。
- 用户回传原场比较：105/97.5 μm二值初始面及7.02e-11/7.29e-11 m³体积已由原生alpha确认，1/2/3 μs早期沉积在共同粗格上重叠约0，1 μs总功率均755.601608 W但细格源峰值约4.11倍。10时刻、原生8→1映射及消费文件读取窗口前后SHA通过，离线154.70 s，见EXP-003-ADD-01及归档哈希。不能独立解释全部温差。M1-IC尚未实测；其分数alpha不证明精确VOF重构面。M2未运行。RSS/数据仍MONITORED_ONLY，多次反射/显著界面运动/热点/实验准确性未建立。
- M正式选型仍待实测成本及负责人批准；V选择/实施仍待批准。DEC-006批准三级探索，DEC-007仅增加单次M1-IC受控配置/工具，不自动批准其余候选或改变阶段顺序。

## GitHub 状态与版本追溯

截至上述核对日期：[PR #3](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/pull/3) 已由负责人手动合并，合并提交5e08097d420af3cfb746eda8ec1833da1d068395已核验属于main历史；PR #2亦已合并。本轮从最新main新建`feat/threeD-progressive-m-exploration`，通过[Draft PR #4](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/pull/4)交付，OPEN / DRAFT / 未合并。新M工具与本页更新目前位于该分支，不代表main已接收；不继续使用已合并PR #3分支，不自动合并。

| 关键提交 | 含义与边界 |
| --- | --- |
| [3c93f265](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/3c93f2657e089e22e9a8298648292969e85a4bad) | 锁定上游源码；详见[来源记录](../UPSTREAM_BASELINE.md) |
| [baeb8107](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/baeb810719a6f24693672d266905da2ef1587c9c) | 用户完成串行 A/B 验证所用离线比较器；不是实际求解 SHA |
| [532ed068](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/532ed0683890ea4e7b368d0fec7ea668d6e6afa8) | PR #2 合并，独立求解器及串行回归基础 |
| [ba94bf88](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/ba94bf8854d1b7a42ff4481237937d34d55d5e31) | 受控路线与 S 探针工具；没有真实三维运行结论 |
| [7c094679](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/7c094679016a2458282c9fcb261d7d55983496bb) | S原始运行/构建记录匹配的版本；亦含S说明与文献候选 |
| [87061fe9](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/87061fe9a83a51e3bf9c6ad3058979715b06658e) | 自动反馈工具核对版本；本次实机归档已验收，不是原始运行SHA |
| [5e08097d](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/5e08097d420af3cfb746eda8ec1833da1d068395) | PR #3合并到main；本轮三级M开发起点 |
| [15df5607](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/15df5607b51427b96e46b3db27c345169a345590) | DEC-006授权的M1/M2/M3配置、运行/多时刻检查/反馈工具；真实M运行UNVERIFIED |
| [1d32b6fd](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/1d32b6fda86d730b8e18b1d9f50e1752fffa5416) | M1原始运行/构建记录SHA；solver成功、原离线uniform格式REVIEW_REQUIRED，详见EXP-002 |
| [b5e429b1](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/b5e429b1ef470314021f6fd03703294b8766a0a8) | uniform标量状态严格解析工具；M1修复后实机复核PASS所用版本，不是原生求解SHA |
| [8f60695a](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/commit/8f60695ac39dd7c5ce096ad5781528c229f08ce3) | M3原生运行/构建SHA，用户实测PASS；不是本轮新离线比较工具版本 |

当前分支后续提交以 PR 提交列表为准；上表仅列关键既有节点，不作为构建匹配记录。CI 的语法、合成夹具和 Markdown 通过不等于 OpenFOAM 编译、实测或物理验证。

## 文档导航与证据位置

| 文件 | 职责与权威范围 |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | 新任务阅读顺序、执行与变更规则 |
| [AI_PROJECT.md](../AI_PROJECT.md) | 项目简介、分支和交付约定 |
| [RESEARCH_CHARTER.md](research/RESEARCH_CHARTER.md) | 受控目标、精度原则、变更权限 |
| [DEVELOPMENT_PLAN.md](research/DEVELOPMENT_PLAN.md) | 受控阶段、优先级、阶段完成依据 |
| [DECISION_LOG.md](research/DECISION_LOG.md) | 追加式批准记录和未批准提案 |
| [EXPERIMENT_LOG.md](research/EXPERIMENT_LOG.md) | 追加式实验事实、版本和性能证据索引 |
| [BENCHMARK_DESIGN.md](research/BENCHMARK_DESIGN.md) | S/M 候选定义、预算与比较设计 |
| [MPI_RISKS.md](research/MPI_RISKS.md) | 已知并行风险与定向验证依据 |
| [LITERATURE_VALIDATION_CANDIDATES.md](research/LITERATURE_VALIDATION_CANDIDATES.md) | 非受控文献/实验数据候选、V1/V2 提案及缺失输入 |
| [M_CASE_NEXT_PROPOSAL.md](research/M_CASE_NEXT_PROPOSAL.md) | S实测后的历史提案与研究依据；100步建议不再是当前入口 |
| [THREED_M_EXPLORATION.md](validation/THREED_M_EXPLORATION.md) | DEC-006三级M探索配置、一次构建与M1/条件M2/M3执行和反馈 |
| [M1_RECHECK_M3_PREFLIGHT.md](validation/M1_RECHECK_M3_PREFLIGHT.md) | M1复核历史/报告保护、M3资源版本预检、隔离构建及mesh→solve→离线反馈指令 |
| [M1_IC_CONTROLLED_EXPERIMENT.md](validation/M1_IC_CONTROLLED_EXPERIMENT.md) | DEC-007单次受控初态、隔离构建/mesh/solve/离线归档、三方对照 |
| [M1_M3_SPATIAL_COMPARISON.md](validation/M1_M3_SPATIAL_COMPARISON.md) | 已有原场只读比较、8→1坐标/体积映射、指标定义、JSON/CSV与反馈命令 |
| [SHORT_GEOMETRY_DIAGNOSTIC_PROPOSAL.md](research/SHORT_GEOMETRY_DIAGNOSTIC_PROPOSAL.md) | 108000单元/300步诊断的PROPOSED科学设计与成本，不是已批准配置 |
| [THREED_SMOKE_FIRST_RUN.md](validation/THREED_SMOKE_FIRST_RUN.md) | S 分阶段 Ubuntu 命令和最小反馈 |
| [RESULTS.md](validation/RESULTS.md) | 用户回传的编译、运行、串行数值基线及局限 |
| [PLATE2D_AB.md](validation/PLATE2D_AB.md) | 原生场、边界、日志和 uniform 的 A/B 比较方法 |
| [FEEDBACK.md](validation/FEEDBACK.md) | 实机反馈格式与日志管理 |
| [UPSTREAM_BASELINE.md](../UPSTREAM_BASELINE.md) | 上游来源、许可证和兼容状态追溯 |

现有串行证据摘要位于 RESULTS 和 EXP-000：3200 单元、10 步、30/30 场及边界、263 日志事件、21 输入/5 网格和 uniform 通过。原始结果在用户本地受保护、被 Git 忽略的 `runs/Plate2D-ab-002/`；构建和审计原记录保存在本地 `validation/`。这些本地目录不是公开下载链接。

目前没有项目自身完成的物理实验验证。公开实验数据来源、DOI、参数匹配问题及许可缺口见文献候选库；列入候选库不表示已下载核验或已经复现。

## 仍然 UNVERIFIED 的结论

- S/M全部实际二进制/动态依赖的独立重验、真实多次反射及困难路径覆盖；S未观察到熔化，M1/M3已观察熔化并完成基础离线检查，已有跨网格结果及读取窗口哈希证据（用户回传），仍不证明原场全部历史未变。M1-IC实际初始化/求解/三方比较、M2成本和正式参考未建立。
- 网格/时间收敛、物理精度、实验一致性、MPI 正确性与三维代表性 LPBF 能力。
- 性能瓶颈、AI 净收益、端到端数倍加速及训练成本摊销。
- 外部实验的完整输入、可追溯材料参数、数据版本与再发布权限；逐项状态以候选库为准。

A/B 数值回归、物理实验验证、AI 加速效果是三类独立证据，不能相互替代。

## 长期维护与公开边界

新任务先读 AGENTS、本页和正式研究计划，再读相关源码/详细文档。新 PR、重要功能完成、正式实机反馈、批准决策、正式基准验证及关键 Bug 确认/解决时，检查本页；有实质状态变化才随对应 PR 更新摘要，附实验记录、提交或批准依据，不每次聊天自动提交。更新日期表示最后核对，不把计划任务写成完成。

新增或移动文档时检查相对导航链接；自动 CI 检查本页、AGENTS 和 AI_PROJECT 的本地 Markdown 链接目标。维护入口不授权改章程、开发计划、已批准决策或验收标准；受控变更仍须负责人明确批准并追加记录。

GitHub 可保存项目文档、基准配置、验证工具、已审阅的实验摘要/数值与性能结论、论文来源和 DOI。公开证据宜采用经审查的小型摘要表、数据文件和哈希记录。

不得提交个人电脑绝对路径、主机识别信息、完整未审查环境报告、私有日志、大量 CFD 原始场，或许可未确认的论文 PDF/实验数据。原始数据继续留在本地受保护的 `runs/` 和 `validation/`；引用外部数据前核对许可与引用要求。
