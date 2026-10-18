# 项目资料入口 · AI-Accelerated-LaserbeamFoam

状态核对日期：2026-10-18。本页是导航与状态摘要，不替代正式计划或原始证据。各主题以导航表中的权威文件为准；发生冲突时回查正式文件和 Git 历史，不根据本页自行改计划。

最新[阶段3前方向重评](research/STAGE3_DIRECTION_REASSESSMENT_20261018.md)固化压力初值研究当前NO_GO：采集/回放通过，但真实残差拒绝及费用不支持AI开发。T组装/准备30.28%、p预测/更新20.69%是观测包围成本；唯一T–相变固定点候选NOT_READY，阶段3 AI未启动，PR #5保持Draft不合并。[阶段2原提案](research/STAGE2_CLOSEOUT_20261018.md)保留为历史。

## 目标与 Current Status

研究实质性的 AI 加速算法，保留高保真 LPBF CFD 的必要预测与数值能力，逐步交付可靠、可复现、可维护的开源 aiLaserbeamFoam。完整模拟约 2 倍、挑战 3 倍以上是长期愿景，尚无实测支持。完整定义见[研究章程](research/RESEARCH_CHARTER.md)。

| 项目 | 当前状态 | 依据 |
| --- | --- | --- |
| 正式阶段 | 阶段2限定研究BOUNDED_STUDY_CLOSED（DEC-017）；MAG候选NO_BENEFIT停止，阶段3仍未启动；细内核/AI净收益未测 | [EXP-007/008/010](research/EXPERIMENT_LOG.md)、[内部计时](validation/M1_TP_INTERNAL_TIMING_20261018.md) |
| Plate2D 串行 A/B | 用户实测 PASS；仅当前短程数值等价 | [RESULTS](validation/RESULTS.md)、[EXP-000](research/EXPERIMENT_LOG.md) |
| 三维 S | 新一次Codex本机真实执行通过：LOCAL_CODEX_CFD_AUTOMATION_VERIFIED，19场检查及23文件归档核验通过；未观察到熔化，仍为PROPOSED探针；旧S历史保留 | [EXP-004](research/EXPERIMENT_LOG.md)、[本机实证](validation/LOCAL_CODEX_CFD_AUTOMATION_20261017.md) |
| M负载与历史探索 | 原M1已批准固定性能开发用途；物理准确性/网格收敛参考未批准。早期沉积错层、IC阈值证据保留，阈值探索结束；M2/M3不在本批执行范围 | [DEC-011](research/DECISION_LOG.md)、[EXP-005/006](research/EXPERIMENT_LOG.md) |
| 论文物理验证 V | 候选研究，PROPOSED；没有新增强制阶段或已实现案例 | [文献与实验候选库](research/LITERATURE_VALIDATION_CANDIDATES.md) |
| AI 模块 | NOT_STARTED；尚未选择或实现 | [开发计划](research/DEVELOPMENT_PLAN.md) |
| MPI 固定验证矩阵 | 已撤销为强制开发门槛；保留定向验证及已知风险 | [DEC-002](research/DECISION_LOG.md)、[MPI 风险](research/MPI_RISKS.md) |

此前DEC-018/EXP-014压力系统前置结果为[INCONCLUSIVE](validation/PRESSURE_SYSTEM_FEASIBILITY_20261018.md)：离线工具构建遗漏接口参数，按失败停止；零新CFD、零采集系统/回放/AI。3343保护SHA一致；不据此否决科学假设，也不建议现在批准AI。新PR仅交付失败记录并保持Draft，数值门槛未通过，不合并；PR #4的阶段2历史及其已合并状态不变。

此前DEC-019/EXP-015已在新批次通过[压力回放接口与合成前置验证](validation/PRESSURE_REPLAY_INTERFACE_20261018.md)：BUILD/FORMAT/RESIDUAL/REPLAY全部PASS，只构建一次、零CFD；4个原生停止通过却不满足原尺度残差的负例正确拒绝。16.02 s/654.57 MiB，3398保护SHA一致。具备申请后续受控CFD的前置资格，不自动授权采集或AI；PR #5保持Draft、不合并，EXP-014原失败历史保留。

最新DEC-020/EXP-016已完成[真实压力采集与原生回放](validation/REAL_PRESSURE_REPLAY_20261018.md)：唯一S→唯一M1，190场/30 uniform/事件及258步轨迹对三原版一致；33原初值回放通过，3493保护SHA不变。30 M1样本原迭代160，外推含回退194、零初值532，无净节省；采集链路PASS，但当前AI初值开发建议NO_GO。批次389.79 s，不训练/接入AI，不自动追加CFD，PR #5保持Draft、不合并。

## 已完成、正在执行与下一步

已完成的重要里程碑：独立 aiLaserbeamFoam 源码与编译入口；用户回传 v2512 双求解器编译及 Plate2D 串行短程 A/B PASS；正式研究治理文件；S 工具及文献候选库；用户回传 S 三维基础运行及自动归档验收。S归档核验来自用户提供的ChatGPT检查结果，Codex未取得原包，不能宣称直接核验。

当前完成：按[DEC-008](research/DECISION_LOG.md)，Codex在Ubuntu直接完成一次全新2048单元/10步S的隔离构建→mesh→solve→检查→归档，[本机实证](validation/LOCAL_CODEX_CFD_AUTOMATION_20261017.md)记录完整SHA与成本。另一个既有工作区实际存在M1/M3/M1-IC原场和诊断报告；本轮直接核验旧诊断包，不重跑CFD或冒充全套原场重审。阶段1整体尚未完成。

最新科学进展：DEC-009/EXP-005已直接完成三组1 μs alpha.metal/alpha_filtered/rayQ/Deposition及原生网格的只读定向审计，48.41 s/458.85 MiB、64项读取前后SHA一致、零新增CFD。IC97.5 μm层1600单元alpha_filtered比0.5低约1.28–1.44e-15，346个rayQ>0单元而无沉积；内部重建mag(n)≈0.99999998。结论仅支持保存状态的alpha门槛机制，不证明逐射线事件或全部温差因果；详见[原场报告](validation/OPTICAL_THRESHOLD_AUDIT_20261017.md)。

阈值问题已结束：DEC-010/EXP-006最后一次五父/40子只读诊断7.57 s/159.20 MiB、21项SHA一致，限制结果逐位复现。精确保存坐标/体积下仍略低于0.5，最后fsum/除法没有造成跨越；即使理想精确等体积，限制与二值光学资格仍不交换。THRESHOLD_EXPLORATION_CLOSED，见[最后诊断](validation/RESTRICTION_FINAL_DIAGNOSIS_20261017.md)，不继续阈值实验链。

当前实测EXP-007：按DEC-011完成三个新目录原M1，190场/10时刻/uniform全部通过，190个物理输出场三例逐字节一致；solver205.96/206.52/204.95 s，中位205.96 s、CV0.3866%，批次15分49秒。25项准备输入及10个原生网格/初态文件冻结且匹配原M1；[阶段2报告](validation/STAGE2_M1_PERFORMANCE_20261017.md)记录完整资源/I/O/检查成本。perf实际探测被paranoid=4拒绝，第四例未执行；采样开销未测，内部模块份额/首个AI候选不选定，不宣称阶段2全部完成。原[提案](research/M_SELECTION_STAGE2_PROPOSAL.md)保留历史，不自动进入AI、M2/M3、IC或smoke。

最新EXP-008：DEC-012授权的一次隔离计时S门槛通过后，唯一完整M1 solver205.07 s/RSS233.14 MiB，对全部三次基线190场/10时刻/30个uniform文件逐字节一致，2009项保护SHA不变。互斥阶段计时闭合：T38.5752%、p30.0516%、激光沉积11.4613%、U9.2683%、VOF4.2397%；未归入物理模块0.99924%。相对205.96 s为−0.4321%，单次观测不能分离计时净开销；295项测试通过。可信的是固定M1的粗阶段成本，不是内部线性求解或AI收益；下一步只读审查T/p源码和既有求解事件，不自动新CFD/AI。见[完整计时报告](validation/STAGE2_M1_TIMING_20261017.md)。

最新EXP-009完成[T/p内部只读分析及唯一提案](validation/M1_TP_INTERNAL_ANALYSIS_20261017.md)：零新CFD，四份M1的T/p/epsilon事件序列一致。T7244调用/8705迭代，p3000/16099；后3 μs占T调用77.28%，不是时间份额。发现258步达到21次热校正后epsilon1变化残差仍>1e-6，原检查PASS契约未要求此项收敛，不能当已收敛物理/AI真值。内部7处切换点提案及开销尺度已说明，后续实验仅PROPOSED、未实现/未运行；不更改循环/容差或进入AI。

最新EXP-010已按DEC-014完成唯一S→唯一冻结M1内部七点/10箱计时，205.01 s/236.50 MiB；190场/30 uniform及事件对三基线一致、258步风险保留，2703保护SHA不变，父子/分箱精确闭合。T_ASSEMBLY15.25%、T_OTHER15.03%、P_OTHER11.85%、P_UPDATE8.85%，两个solve API合13.03%；仅让两个API归零的solver极端上限1.14976×，不是AI收益预测。后3 μs占T实测74.98%；不能把整段费用都归258步。见[内部计时结果](validation/M1_TP_INTERNAL_TIMING_20261018.md)。本轮约6分钟且门槛通过，额度已用完，不自动追加模拟/AI。

最新EXP-011完成[依赖审计与唯一候选](validation/M1_REUSE_DEPENDENCY_AUDIT_20261018.md)，零新CFD/优化实现。仅提议单次TEqn内复用原生mag(gradAlpha)，其输入局部固定但thermalDamper/辐射/蒸发仍变化；p的H读取当前U，不能直接缓存整个预测量。候选自身成本/等价/净收益未测，T_OTHER15.03%不是可加速份额。一个OFF/ON未来协议仅PROPOSED，258步风险保持，不自动运行。

最新EXP-012/DEC-016对唯一缓存做[非CFD原生场筛选](validation/MAG_CACHE_NATIVE_20261018.md)，最终NO_BENEFIT。12组字段/108次乘法正确性通过；完整mag最大批均136.501 μs，2倍安全系数并假设全部7244次消除仍仅1.978 s/solver0.9602%，不足约2%目标，已停止，无S/M1/优化求解器。83.65 s、3189项保护SHA一致；此为经验成本否决而非实测CFD净收益，258步风险保持。本候选不继续投入，不自动扩大研究。

当前待补证据与批准事项：

- S 用户提供的ChatGPT核验结果：23个归档文件/22条内部哈希、清单通过；源/构建完整SHA均为7c094679016a2458282c9fcb261d7d55983496bb。solver=0.35 s、最大RSS=127488 KiB，已记录流程范围1.919696505 s；归档标识和SHA256见EXP-001-ADD-01。RECORDS_MATCH不等于重验实际二进制和动态库，工具87061fe9不等于原运行版本。物理/性能证据缺口仍保留。
- 新S本机实证EXP-004：源/构建07496d15d1eebcb99f618d148a54af3729210669，solver0.36 s/126568 KiB，准备及mesh/solve范围1.875943304 s，构建另计185.44 s，最终离线检查/导出0.61 s；二进制/动态库来源守卫通过，归档COMPLETE。原始数据本地保留，仅公开脱敏摘要及哈希；不替代旧S运行记录或物理验证。
- Plate2D-ab-002 的实际构建/求解 SHA 待原 manifest 和构建摘要补录；不能用离线比较器提交替代。
- M1实测32000单元、1000步/10 μs，solver退出0，190场检查记录、29491日志事件；3 μs采样首次熔化，7 μs采样超过配置Tvap。原solver214.50 s、RSS240452 KiB、约121.05 MB数据与322.623874 s流程范围保持原记录。工具b5e429b1复核10时刻/190场和10个cumulativeContErr均PASS，离线约96.63 s；原95.90 s/REVIEW记录保留，来源及新包哈希见EXP-002-ADD-01。
- M3源/构建8f60695a，256000单元/1000步，190场及10时刻uniform通过；solver2872.64 s、RSS1104420 KiB、工作流范围3983.762 s、显式离线724.874 s、数据902667461字节。原生与后处理范围不混加。M3温度/起熔时序与M1差异显著，终点熔化区y有4层；不证明收敛或物理准确性。
- 用户回传原场比较：105/97.5 μm二值初始面及7.02e-11/7.29e-11 m³体积已由原生alpha确认，1/2/3 μs早期沉积在共同粗格上重叠约0，1 μs总功率均755.601608 W但细格源峰值约4.11倍。10时刻、原生8→1映射及消费文件读取窗口前后SHA通过，离线154.70 s，见EXP-003-ADD-01。EXP-004核验本地旧包与该哈希一致；EXP-005另直接审计1 μs的限定光学字段，不是全时刻重审。既有IC报告3 μs最高金属T1957.76 K，M3为4086.86 K，初态干预未复现M3；分数alpha不证明精确VOF重构面或独立解释全部温差。M2未运行，多次反射/显著界面运动/热点/实验准确性未建立。
- DEC-011已正式批准原M1固定性能开发用途，EXP-007完成三次成本/重复性测量；物理准确性/网格参考及V选择/实施仍未批准。DEC-006/007历史范围保留，不自动批准其余候选、AI或阶段3。

## GitHub 状态与版本追溯

[PR #3](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/pull/3) 合并提交5e08097d420af3cfb746eda8ec1833da1d068395属于main历史；PR #2亦已合并。`feat/threeD-progressive-m-exploration`通过[PR #4](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/pull/4)交付；DEC-017新增授权：审查与最终CI通过后自主Ready并采用Merge Commit，保留历史。实际状态/合并SHA以PR及Git历史为准；此前Draft限制属于历史，不授权任何新增CFD或AI。

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
| [LOCAL_CODEX_CFD_AUTOMATION_20261017.md](validation/LOCAL_CODEX_CFD_AUTOMATION_20261017.md) | DEC-008授权的新S真实本机自动化、资源、归档与哈希 |
| [ALPHA_DEPOSITION_STATIC_REVIEW.md](research/ALPHA_DEPOSITION_STATIC_REVIEW.md) | 旧原场/报告实际存在、IC结论、过滤与射线门槛静态审查和最低成本后续建议 |
| [OPTICAL_THRESHOLD_AUDIT_20261017.md](validation/OPTICAL_THRESHOLD_AUDIT_20261017.md) | 1 μs三组原场阈值审计、半填充层数值、内部法向重建、JSON/CSV和证据边界 |
| [RESTRICTION_FINAL_DIAGNOSIS_20261017.md](validation/RESTRICTION_FINAL_DIAGNOSIS_20261017.md) | 最后一次五父/40子体积与精确算术诊断，阈值探索结束 |
| [M_SELECTION_STAGE2_PROPOSAL.md](research/M_SELECTION_STAGE2_PROPOSAL.md) | 阶段2历史提案；后续DEC-011批准范围与原始方案边界 |
| [STAGE2_M1_PERFORMANCE_20261017.md](validation/STAGE2_M1_PERFORMANCE_20261017.md) | 三次原M1基线、冻结、资源/I/O/检查成本、重复性与采样阻塞，AI未选定 |
| [STAGE2_M1_TIMING_20261017.md](validation/STAGE2_M1_TIMING_20261017.md) | 隔离轻量计时、S/M1逐字节一致性、模块成本及未归因/开销边界 |
| [M1_TP_INTERNAL_ANALYSIS_20261017.md](validation/M1_TP_INTERNAL_ANALYSIS_20261017.md) | T/p源码/求解事件时间演化、原版校正上限退出、唯一PROPOSED内部计时方案 |
| [M1_TP_INTERNAL_TIMING_20261018.md](validation/M1_TP_INTERNAL_TIMING_20261018.md) | 已批准七点/10箱内部计时、精确等价、T/p成本及极端加速上限 |
| [M1_REUSE_DEPENDENCY_AUDIT_20261018.md](validation/M1_REUSE_DEPENDENCY_AUDIT_20261018.md) | T/p不变量/变化量/未证明依赖、唯一条件候选及未批准OFF/ON协议 |
| [MAG_CACHE_NATIVE_20261018.md](validation/MAG_CACHE_NATIVE_20261018.md) | 单项缓存原生字段正确性/完整运算成本及无CFD的NO_BENEFIT否决 |
| [RESULTS.md](validation/RESULTS.md) | 用户回传的编译、运行、串行数值基线及局限 |
| [PLATE2D_AB.md](validation/PLATE2D_AB.md) | 原生场、边界、日志和 uniform 的 A/B 比较方法 |
| [FEEDBACK.md](validation/FEEDBACK.md) | 实机反馈格式与日志管理 |
| [UPSTREAM_BASELINE.md](../UPSTREAM_BASELINE.md) | 上游来源、许可证和兼容状态追溯 |

现有串行证据摘要位于 RESULTS 和 EXP-000：3200 单元、10 步、30/30 场及边界、263 日志事件、21 输入/5 网格和 uniform 通过。原始结果在用户本地受保护、被 Git 忽略的 `runs/Plate2D-ab-002/`；构建和审计原记录保存在本地 `validation/`。这些本地目录不是公开下载链接。

目前没有项目自身完成的物理实验验证。公开实验数据来源、DOI、参数匹配问题及许可缺口见文献候选库；列入候选库不表示已下载核验或已经复现。

## 仍然 UNVERIFIED 的结论

- 历史S/M全部实际二进制/动态依赖的独立重验、真实多次反射及困难路径覆盖；新S有直接执行与依赖守卫证据。EXP-005证明限定0/1 μs光学字段审计读取窗口SHA一致，不证明全部历史不变、逐射线事件或温差唯一归因；M2成本和正式参考未建立。
- 网格/时间收敛、物理精度、实验一致性、MPI 正确性与三维代表性 LPBF 能力。
- 原M1粗阶段成本已由EXP-008测得；EXP-010另测得T/p内部边界成本；纯迭代内核/更细函数热点、跨工况性能瓶颈、AI净收益、端到端数倍加速及训练成本摊销仍未验证。
- 外部实验的完整输入、可追溯材料参数、数据版本与再发布权限；逐项状态以候选库为准。

A/B 数值回归、物理实验验证、AI 加速效果是三类独立证据，不能相互替代。

## 长期维护与公开边界

新任务先读 AGENTS、本页和正式研究计划，再读相关源码/详细文档。新 PR、重要功能完成、正式实机反馈、批准决策、正式基准验证及关键 Bug 确认/解决时，检查本页；有实质状态变化才随对应 PR 更新摘要，附实验记录、提交或批准依据，不每次聊天自动提交。更新日期表示最后核对，不把计划任务写成完成。

新增或移动文档时检查相对导航链接；自动 CI 检查本页、AGENTS 和 AI_PROJECT 的本地 Markdown 链接目标。维护入口不授权改章程、开发计划、已批准决策或验收标准；受控变更仍须负责人明确批准并追加记录。

GitHub 可保存项目文档、基准配置、验证工具、已审阅的实验摘要/数值与性能结论、论文来源和 DOI。公开证据宜采用经审查的小型摘要表、数据文件和哈希记录。

不得提交个人电脑绝对路径、主机识别信息、完整未审查环境报告、私有日志、大量 CFD 原始场，或许可未确认的论文 PDF/实验数据。原始数据继续留在本地受保护的 `runs/` 和 `validation/`；引用外部数据前核对许可与引用要求。
