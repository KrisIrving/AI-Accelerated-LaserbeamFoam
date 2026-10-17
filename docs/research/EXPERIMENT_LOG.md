# 实验记录（追加）

原始日志/场保留在忽略的 runs/、validation/；公开记录不包含主机私有路径、完整环境或大数据。更正用追加条目链接旧ID，不覆盖历史。

## EXP-000 — Plate2D串行A/B（历史用户证据）

- 状态：USER_REPORTED_PASS；本轮未重跑。
- 求解器：laserbeamFoam / aiLaserbeamFoam，无AI。比较器baeb8107；原运行/构建commit待原manifest和summary补录。
- 环境：OpenFOAM.com v2512，linux64GccDPInt32Opt；串行；案例Plate2D-ab-002。
- 规模/时间：3200单元，10步，0至1e-7，最终输出1e-7。
- 证据：30/30场语义及边界、263日志事件、21输入/5网格、uniform全部通过，Issues=0；已比较误差0；atol1e-12/rtol1e-10。
- 墙钟：该次完整A/B计时未提供，UNVERIFIED；不挪用此前单次原版0.67秒作为这次性能基线。
- 结论：串行重命名数值等价；物理精度/MPI/AI性能未验证。原始结果保留。

## 后续追加模板

- 实验ID/日期/状态（PLANNED、RUNNING、PASS、FAIL、REVIEW_REQUIRED）：
- 问题/可否决假设及所属批准阶段/决策：
- 源码commit、构建commit、比较/采集工具commit、dirty状态：
- 求解器/开关/共享库和依赖来源：
- OpenFOAM、WM_OPTIONS、编译优化：
- 案例配置版本/输入哈希/网格量/网格质量：
- dt、实际步数、终止时间和全部输出时刻：
- 资源（进程、线程、CPU亲和、内存预算；公开记录去隐私）：
- 初始化/推进/I/O/整体计时、最大RSS、重复次数和波动：
- 性能工具/权限/采样设置/采集本身开销：
- 数值/物理检查、原版差异、误差/守恒/失败或回退：
- 日志索引（仓库相对路径，不上传大数据）：
- 结论、局限、下一步候选；是否需要批准计划变更：

## EXP-001 — threeD-smoke-002 首次三维 S 实测（用户摘要）

- 登记日期：2026-10-16；实际运行日期未提供，UNVERIFIED。所属阶段1、DEC-003/004；S 仍为 PROPOSED 调试候选，未批准为正式性能基准，阶段1未据此自动完成。
- 来源：用户任务书《三维 S 实测反馈、实验记录与自动后处理打包》中的真实 Ubuntu 反馈摘要。用户说明 ChatGPT 已检查含19份文本的归档；本轮 Codex **仅收到该摘要，没有取得或逐行核验原始 tar.gz**。下列实测值按 USER_REPORTED 登记，不是 CI 合成结果。
- 状态：`SMOKE_CHECKS_PASSED`；`PHYSICAL_ACCURACY_UNVERIFIED`；`MELTING_NOT_OBSERVED`；`PROFILING_NOT_ESTABLISHED`。
- 溯源：`PROVENANCE_PENDING`。原始运行源码完整SHA、构建完整SHA、采集/离线检查工具SHA、dirty状态、输入哈希和实际动态库来源待原manifest/build summary补录。任务书上次确认提交e1eab16a不作为运行版本依据；不以当前HEAD代填。
- 环境/资源：Ubuntu22.04、OpenFOAM.com v2512；原版laserbeamFoam、MPI ranks=1；未回传本次WM_OPTIONS及实际编译优化记录，UNVERIFIED。不推断GPU参与。
- 网格/初始化：2048单元、5632内部面、3个有效计算方向，Mesh OK；setFields成功，金属初始区域1280/2048单元。
- 时间/检查：10步，终时1e-7 s；19个字段解析与有限值检查通过；173个已识别日志事件；solver.exit=0；issues为空。原始字段集合、边界检查明细及所有输出时刻清单待原报告，不由摘要推定。
- GNU time墙钟：blockMesh=0.08 s、checkMesh=0.07 s、setFields=0.07 s、solver=0.35 s；solver最大RSS=127488 KiB，约124.5 MiB。
- 外层范围：mesh workflow=0.50 s、solve workflow=1.25 s；准备主体加两workflow约1.9197 s。该记录范围达到约2分钟目标；排除编译、Git、人工等待及最后离线重查。不外推大型案例性能，不把嵌套计时重复相加，不据此证明AI收益。
- 最终状态：T约300.0–330.293 K；alpha.metal接近0至1；1280个金属主导单元、最高T约330.293 K、液相率0–0，epsilon1最终为0。未观察到金属熔化或可验证熔池；只覆盖本次终态观察。
- Deposition最大字段值约7.2806e14；原生字段dimensions待归档核对，不能将最大值当总吸收功率。当前源码声明为dimensionSet(1,-1,-3,0,0)，与TEqn体积源项相容；这是源码量纲证据，不替代本次字段或沉积积分核验。
- 路径：日志报告laser0–laser4、各400 W、每束每次更新150条射线种子；热源沉积、isoAdvection、温度线性求解、压力修正和体积分数诊断执行。路径调用不证明熔化、困难相变迭代、多次反射或充分界面变形；多次反射仍NOT_ESTABLISHED。
- 非致命提示：elec_resistivity弃用关键字；reconstructionScheme缺省采用isoAlpha。记录而不据此改物理输入或原生源码。
- 局限：没有A/B三维参考、离散收敛或实验物理验证；没有模块耗时占比或可信热点排名，0.35 s极短求解不足以支持性能归因。
- 原始证据位置：用户本地受保护的`runs/threeD-smoke-002/`及对应`validation/`构建记录；未上传原始场、完整主机日志或私有路径。下一步可使用显式离线反馈导出补录溯源，再审核M提案；无受控计划变更。

## EXP-001-ADD-01 — S 自动归档验收与溯源补录

- 登记日期：2026-10-16；补充EXP-001，不覆盖该记录最初的PROVENANCE_PENDING或其他历史内容。来源为用户本轮《S归档实机验收结果与阶段1收尾》：用户报告已向ChatGPT上传新版反馈包，ChatGPT实际读取日志/JSON并检查清单与SHA256。**本轮Codex未取得该tar.gz，以下引用用户提供的ChatGPT核验结果，不声称Codex直接打开或重算过归档。**
- 归档文件：`threeD-smoke-feedback.20261016T120544Z.eab2fb70215048d3930768b7c888f3c2.tar.gz`。
- 归档SHA256：`28e142f74e835d749faef2fee93d8d56d99a509d63cbad6f34ff28255cb5e4b6`；用户报告23个文件、22条内部SHA256全部匹配、FILES.txt完全匹配、无非法tar条目。
- 打包验收：`archive_status=EXPORTED`、`collection_status=COMPLETE`、`timing_status=RECORDED_SCOPE`、`missing_required=[]`、`omitted={}`。未使用aiLaserbeamFoam的日志属于可选缺项，不影响本次白名单完整性。工具已通过一次真实Ubuntu使用；仅就本次成功归档记为USER_REPORTED_WORKSTATION_ACCEPTED，无需据此继续改造工具。
- 检查/求解：`check_status=SMOKE_CHECKS_PASSED`、`check_exit_code=0`、`solver_exit_code=0`、uniform PASS；2048个三维六面体单元、5632内部面、Mesh OK、setFields选择1280个初始金属单元；10步至1e-7 s、19场解析/有限值/对应结构检查、173日志事件。
- 原始运行源码SHA：`7c094679016a2458282c9fcb261d7d55983496bb`；构建源码SHA及manifest声明的构建SHA均相同。`provenance_status=RECORDS_MATCH`；原EXP-001中的源/构建版本缺口据此补齐。
- 运行配置记录：OpenFOAM=v2512，WM_OPTIONS=linux64GccDPInt32Opt，solver=laserbeamFoam，mpi_ranks=1；上游输入基线`3c93f2657e089e22e9a8298648292969e85a4bad`。工具核对提交为`87061fe9`；它不是原始求解器运行提交，也不代填尚未提供的dirty状态或完整二进制/动态依赖校验记录。
- 溯源界限：RECORDS_MATCH仅表示原始源码/构建记录相互匹配，不等于重新验证全部实际执行二进制及动态依赖。内部SHA验证针对归档内脱敏文本，归档哈希标识本次反馈包，不是原始CFD场、输入或二进制的认证。
- 资源补充：solver墙钟0.35 s、最大RSS127488 KiB；已记录流程范围1.919696505 s。沿用EXP-001的计时范围排除项，不把嵌套阶段时长重复相加；不以打包时刻推断原始求解发生日期。
- 物理界限不变：最终T约300–330.293 K，金属主导单元液相率0–0；激光/沉积、isoAdvection、温度和压力路径有日志证据。保留`MELTING_NOT_OBSERVED`、`PHYSICAL_ACCURACY_UNVERIFIED`、`PROFILING_NOT_ESTABLISHED`；没有三维A/B等价性、网格/时间收敛、多次反射独立证据或AI收益。
- 处置：S低成本调试探针的本次运行与归档证据已补录；保留原始数据，不重跑、不重新打包、不修改工具。S仍非正式性能基准，阶段1仍IN_PROGRESS；M探索提案待明确批准后才能生成配置/执行，未修改任何受控目标、路线或决策。

## EXP-002 — M1 首次真实熔化探索与离线格式阻塞

- 登记日期：2026-10-16；阶段1、DEC-006已授权的M1探索，不是正式M基准批准。状态分别为 `NATIVE_SOLVE_COMPLETED`、`OFFLINE_REVIEW_REQUIRED`、`MELTING_OBSERVED`、`PHYSICAL_ACCURACY_UNVERIFIED`、`GRID_CONVERGENCE_UNVERIFIED`、`HOTSPOT_NOT_ESTABLISHED`。阶段1仍IN_PROGRESS。
- 证据来源：最初收到用户提供的ChatGPT归档分析；用户随后提供诊断压缩包，**本轮Codex直接读取该包并重新核算归档及内部哈希**。未取得原始网格、190个物理场或`uniform/cumulativeContErr`原文件，下面的场统计是归档报告中的结果，不是Codex重新解析原场的结果。
- 归档：`threeD-exploration-feedback.20261016T151231Z.af0bd3d53d0545d9b01a1983bb8ab57d.tar.gz`；SHA256=`f79055c36d6469288b8a05afacbc6f76c9343e9de0270a055213855b5c6f7dac`。26个普通文件，无重复/越界/链接tar条目；25条内部SHA256全部匹配；FILES.txt与归档清单完全匹配。归档完整不等于数值检查全部通过。
- 打包/来源：`archive_status=EXPORTED`、`collection_status=COMPLETE`、`timing_status=RECORDED_SCOPE`、`provenance_status=RECORDS_MATCH`、缺少必要文件/遗漏为空。未使用AI求解器的可选文件缺失不影响完整性。RECORDS_MATCH仅比较记录，不重新认证实际二进制和动态库。
- 原始运行源码、构建源码、manifest构建SHA均为 `1d32b6fda86d730b8e18b1d9f50e1752fffa5416`；OpenFOAM.com v2512、`linux64GccDPInt32Opt`、原版laserbeamFoam、MPI rank1。配置规范化SHA256=`abc57350052df27f49efa30791245494c3bc6a0566d373eb78d83b2045e3a109`。本轮修复工具的提交另记Git历史和未来复核记录，不替代原始运行/构建SHA。
- 网格：40×20×40=32000单元、92800内部面，`VERIFIED_CARTESIAN_HEXAHEDRA`、三维、约15 μm单元尺度，Mesh OK。初始化检查PASS，20800个初始金属单元，初始金属体积约7.02e-11 m³。
- 原生计算：固定dt=1e-8 s，1000步至1e-5 s；预期10个输出时刻全部存在；solver退出0、正常结束。归档报告记录每时刻19个场，共190个文件解析/有限值/对应结构检查通过，29491个已识别日志事件、solver_alerts为空。
- 原始离线状态：`check_exit_code=2`、`REVIEW_REQUIRED`。10条问题均为各输出时刻`uniform/cumulativeContErr`的`uniformDimensionedScalarField`不支持；这是尚缺语义解析，不能改写为求解器失败，也不能把原检查记为PASS。归档不含该原始文件，真实文件的具体字节格式仍待工作站复核。

### 资源与时间范围

| 范围 | 墙钟 / 最大RSS | 解释 |
| --- | --- | --- |
| 原生solver | 214.50 s / 240452 KiB | 包含该次原生I/O；无模块耗时分解 |
| mesh工作流 | 5.87 s / 108608 KiB | 包含网格、初始化和前置/离线检查，不能再与子阶段相加 |
| solve工作流 | 316.58 s / 240452 KiB | 包含solver及工作流检查等；差值不全归给某一检查函数 |
| 已记录准备+mesh+solve | 322.623874148 s | 排除构建、Git、人工等待和最后显式离线复查 |
| 单次离线检查 | 95.900593429 s | 独立成本；排除报告序列化和反馈导出，不是CFD加速收益 |
| 案例数据 | 121054926 bytes，约121.05 MB | 原报告采样范围；RSS/数据均在观察预算内 |

每100步累计`ExecutionTime`差分显示约0.1383、0.1379、0.1588、0.1719、0.1769、0.1781、0.1797、0.2871、0.3545、0.3599 s/步。它是原生日志CPU时间差分，不是GNU墙钟，也不是模块占比；后期成本增加已观测，具体热点未建立。

### 物理活动观察及局限

材料沿用官方案例：Tsolidus=1928.15 K、Tliquidus=1978 K、Tvap=3558 K；来源为该次配置/归档报告，不表示材料参数已独立标定。

| 输出时刻 / μs | 金属区域最高T / K | 金属最大液相率 | 金属最大速度 / m/s |
| --- | --- | --- | --- |
| 1 | 1123.36 | 0 | 8.64e-17 |
| 2 | 1774.35 | 0 | 8.77e-16 |
| 3 | 1969.13 | 0.82208 | 1.76e-6 |
| 4 | 2422.00 | 1 | 0.11753 |
| 5 | 2851.12 | 1 | 0.21671 |
| 6 | 3228.93 | 1 | 0.45589 |
| 7 | 3582.12 | 1 | 0.71225 |
| 8 | 3961.48 | 1 | 1.46950 |
| 9 | 4427.19 | 1 | 4.09781 |
| 10 | 4353.88 | 1 | 7.01494 |

- 金属液相率首次在3 μs输出非零；按1 μs采样只能定位首次观察于(2,3] μs。4 μs有完全液态单元。7 μs首次采样超过配置的Tvap，不能单凭这一阈值确认实际汽化、可信小孔或模型准确性。
- 最终液态金属体积估计5.3828e-13 m³，为初始金属体积约0.767%；金属体积相对变化约-5.25e-13。后者只是当前离散观测，不是完整质量/能量守恒验证。
- 最终`alpha>0.5 && epsilon1>0.5`区域158单元，y中心坐标仅一个层（0.0001125 m）；提示熔深欠分辨。中心包围盒y跨度0不等于物理熔深0，不能作为实验熔池尺寸。
- 旧`mixed_cells_count`严格采用0<alpha<1，最后为31766/32000；接近0/1的数值尾迹也计入。后续新增0.01<alpha<0.99观察量，保留旧计数和验收标准；两者都不能单独证明自由面剧烈运动。
- 激光/沉积、温度、压力、VOF路径有日志证据；真实多次反射、显著自由界面运动、空间/时间收敛、独立物理准确性及AI收益仍未建立。高温和单层熔化区优先支持同物理时间M3空间敏感性探索，不支持擅自调功率/材料/dt/容差。

### 后续复核与条件性选择

- 本轮交付M专用严格状态解析及合成回归测试；**尚未在工作站原场上执行修复后的完整复核**。按[M1离线复核与M3预检](../validation/M1_RECHECK_M3_PREFLIGHT.md)备份报告、保留原始场及旧包，记录新检查工具SHA，检查全部10时刻并生成新包。只有真实返回`EXPLORATION_CHECKS_PASSED`，才追加EXP-002补录，不覆盖本条原始REVIEW_REQUIRED。
- 检查器代码审查确认同一场重复读取/解析/展开，网格和日志也存在重复工作；本机小型剖析只证明重复计算，不能归因Ubuntu约96秒的全部开销。本轮暂不做缓存改造；收到原始离线夹具后才比较优化前后逐字段结果及计时，不减少范围。
- 按用户本轮指示优先条件性M3（256000单元/1000步/10 μs），M2暂缓。仅M1复核PASS、原始结果保护、资源/版本预检通过后准备；不自动启动真实CFD。新HEAD须有匹配的隔离构建；源码无变化不代表二进制相同。M仍PROPOSED，阶段顺序和正式标准未改变。

## EXP-002-ADD-01 — M1 修复后工作站离线复核 PASS

- 登记日期：2026-10-17；补充EXP-002，不覆盖原始`OFFLINE_REVIEW_REQUIRED`、95.90秒检查记录或旧归档。批准范围仍为阶段1、DEC-006探索；正式M保持PROPOSED，阶段1整体未完成。
- 来源：用户本轮《M1修复后实机复核PASS：追加证据并准备M3》，明确说明ChatGPT已实际读取并核对新反馈包。**本轮Codex未取得新tar.gz，以下为用户提供的ChatGPT核验结果，不声称Codex直接重算过新归档哈希或重新读取原生场。** EXP-002中Codex直接核验的是旧包，不能混同。
- 新归档：`threeD-exploration-feedback.20261016T160049Z.1acfc38c010a47eb82164b55c359d230.tar.gz`；SHA256=`4a60bf6e03a7d4bfd7c7ded4a8e166ecfef229610fb6dab07f4abc96085b55eb`。用户报告26个归档文件、25条内部SHA256全部匹配，FILES.txt匹配；`archive_status=EXPORTED`、`collection_status=COMPLETE`、`timing_status=RECORDED_SCOPE`。文件名时间仅标识归档，不推断原生求解日期或本地时区。
- 原生求解/构建SHA均保持`1d32b6fda86d730b8e18b1d9f50e1752fffa5416`；修复检查工具提交为`b5e429b1ef470314021f6fd03703294b8766a0a8`。后续文档提交也不代替这两个版本，不要求重跑M1。
- 实机复核：`EXPLORATION_CHECKS_PASSED`、`check_exit_code=0`、`solver_exit_code=0`、`issues=[]`。初始化PASS、32000单元、1000步至1e-5 s；10个输出时刻、190个物理场文件检查通过；10个`uniform/cumulativeContErr`均以`NUMERICAL_SEMANTIC_UNIFORM_DIMENSIONED_SCALAR`通过，七个量纲指数均为0，各时刻value有限。该记录是原生状态语义解析通过，不是字节自比较放行。
- 资源范围：本次离线复核约96.63秒；原求解器墙钟仍为214.50秒，没有重跑或新增CFD性能测量。检查/归档是后处理成本，不解释为AI提速或模块占比。
- 新包不含原生CFD场或复核前后SHA快照。只能据报告确认本次语义检查通过，**不能独立认证原场在复核期间完全未变**，也不把诊断归档哈希当作原场哈希或二进制认证。后续原始结果仍本地保留。
- 物理观察：首次非零金属液相率在3 μs输出；10 μs最高金属T约4353.88 K、最大速度约7.015 m/s、液态金属体积估计5.3828e-13 m³、阈值熔化区158单元且y方向仍一层中心。旧0<alpha<1计数31766，新增严格0.01<alpha<0.99计数226；计数差异符合端点数值尾迹风险，严格计数本身不证明显著界面运动，熔深欠分辨风险保留。
- 结论：M1首次探索的基础运行及离线数值检查通过（用户回传），`MELTING_OBSERVED`；独立实验物理准确性、时间/网格收敛、热点、多次反射及AI收益均UNVERIFIED。该检查不是独立三维A/B参考，也不批准正式M基准。
- 下一步：按用户本轮明确指令，保留M1原场/报告/归档，优先准备并由用户分阶段运行已授权M3，M2暂缓。当前HEAD与原M1的`applications/`、`src/`及`Allwmake`差异核查为空；待Ubuntu生成匹配新HEAD的隔离构建，版本/输入/资源预检通过后才mesh，再审阅初始化后solve。M3尚未构建或运行；[执行说明](../validation/M1_RECHECK_M3_PREFLIGHT.md)不代表实测。无受控计划变更。

## EXP-003 — M3真实完成与M1早期空间敏感性

- 登记日期：2026-10-17；阶段1、DEC-006已授权M3探索。来源为用户本轮《M3真实计算完成：优先研究初始几何与热源的空间敏感性》：用户报告ChatGPT实际读取新包并定量比较此前M1包。**本轮Codex未取得M3归档或两套原生场，下列数值引用用户提供的ChatGPT核验结果，不宣称Codex直接重算新包/原场。**
- 状态分别为`M3_NATIVE_SOLVE_COMPLETED`、`M3_EXPLORATION_CHECKS_PASSED`、`MELTING_OBSERVED`、`SPATIAL_SENSITIVITY_SIGNIFICANT`、`INITIAL_INTERFACE_DISCRETIZATION_DIFFERS`、`PHYSICAL_ACCURACY_UNVERIFIED`、`GRID_CONVERGENCE_NOT_ESTABLISHED`、`HOTSPOT_NOT_ESTABLISHED`。其中界面差异由网格/体积推算支持，**原生alpha层分布与表面截面尚待本轮离线工具核对**，不把该标签当作已独立读取原场的证明。
- 归档：`threeD-exploration-feedback.20261017T041609Z.00d4e0c9a0a64da4842369f279fba463.tar.gz`；SHA256=`600189893c72ada6882c44bc3b3af9311b300dae9ba046fe1ba4bd6248565483`。用户报告26文件、25条内部SHA256及FILES清单全部匹配；`COMPLETE`、`RECORDED_SCOPE`、`RECORDS_MATCH`。匹配记录不等于认证执行二进制或原场历史不变。
- 原始源码/构建SHA均为`8f60695ac39dd7c5ce096ad5781528c229f08ce3`，原版laserbeamFoam；M1原始运行/构建仍`1d32b6fda86d730b8e18b1d9f50e1752fffa5416`，M1修复复核代码仍b5e429b1。新离线比较工具的提交另记Git历史，不能冒充这些运行版本。
- 运行/检查：256000个三维六面体单元，固定dt=1e-8 s，1000步至1e-5 s；10输出时刻、190物理场文件及10时刻uniform状态通过；检查退出0、solver退出0、`issues=[]`。47517个诊断事件，无已识别solver alerts。原有单案例解析/有限性等检查通过不等于独立参考或物理验证。
- 资源：原生solver墙钟2872.64秒（约47.88分钟）、最大RSS1104420 KiB；已记录工作流范围3983.762秒，最新显式离线检查724.874秒、案例902667461字节。工作流范围包含子阶段，不与solver时长重复相加；最后显式离线检查另外列示。solver小于3600秒护栏，工作流超过3600秒不等于solver超时；RSS/数据观察预算内，无模块计时归因。

### 用户提供的M1/M3定量对照

| 观察量 | M1 | M3 |
| --- | --- | --- |
| 网格 | 40×20×40 | 80×40×80 |
| 初始金属体积 / m³ | 7.02e-11 | 7.29e-11 |
| 首次非零金属液相率输出 | 3 μs | 1 μs |
| 1 μs金属最高T / K | 1123.36 | 2274.19 |
| 3 μs金属最高T / K | 1969.13 | 4086.86 |
| 10 μs金属最高T / K | 4353.88 | 4605.54 |
| 10 μs液态体积 / m³ | 5.3828e-13 | 5.7878e-13 |
| 10 μs金属最大速度 / m/s | 7.0149 | 7.1425 |
| 10 μs阈值熔化区y中心层数 | 1 | 4 |
| 原生solver墙钟 / s | 214.50 | 2872.64 |

上述舍入值推得终点最高T约+5.78%、液态体积约+7.52%、初始金属体积约+3.846%；前3 μs温度/熔化时序差异远大于终点指标。首次输出非零不是连续时间中的精确起熔时刻，M3只能定位首次观察不晚于1 μs。

solver耗时比13.392，超过8倍单元增幅；按单元步数归一仍约1.674倍。这是不同网格/物理演化下的成本差异，不能称AI加速，也不能据此指定哪个模块是热点。M3实际成本明显高于低成本日常探针，不因此自动扩大基准预算或选定正式M。

### 初始界面混杂与本轮处置

- 静态官方输入确认boxToCell下界y=100.1 μm，激光名义起始y=10 μm、方向+y。根据回传体积及均匀单元中心推算，M1金属13/20层、厚195 μm、下表面105 μm；M3为27/40层、厚202.5 μm、下表面97.5 μm，相差7.5 μm。该推算不是原生alpha截面验证。
- 初始几何、沉积空间支撑/局部源峰值及热流动离散共同变化，构成早期熔化比较的潜在混杂。不能统一归为Bug，也不能只靠终点相近或两级网格宣布收敛。多次反射、显著界面运动、实验准确性及热点仍未建立。
- 本轮仅交付独立[原场离线比较工具](../validation/M1_M3_SPATIAL_COMPARISON.md)：用原生坐标/体积核对8→1映射，保留初态，报告温度/沉积/alpha×epsilon1/速度及各自权重与限制。合成测试不替代真实M1/M3原场比较；真实工具结果仍待用户回传。
- [108000单元/300步短程诊断](SHORT_GEOMETRY_DIAGNOSTIC_PROPOSAL.md)仅PROPOSED，先估算、再决定是否必要和请求批准；不创建正式配置。改初始化、几何位置或物性必须另提受控对照并获批准。本轮不重跑M1/M3、不运行M2、不改S/原求解器/已有配置/检查标准或受控计划；PR #4继续Draft，阶段1仍IN_PROGRESS。

## EXP-003-ADD-01 — 原场 M1/M3 空间诊断已完成（用户回传）

- 登记日期：2026-10-17；来源为负责人《M1/M3空间诊断结论与M1-IC受控实验》，明确由ChatGPT实际读取并核验。Codex本轮未收到该包或两套原场，以下为USER_PROVIDED_CHATGPT_VERIFICATION，不声称独立解析或重算归档。
- 工具提交8dcdcdcc09c4548564eea66ce4426e5515531346；归档m1-m3-comparison-feedback.tar.gz，SHA256=8ac01be3e64254bb9130596f6e7bace9a2f8b266a868f5e97a1f723c4a0f221c。用户报告9文件/8内部SHA及FILES全部通过，外部sources.sha256与包内相同文件逐字节一致。
- COMPARISON_COMPLETED，issues=[]，全部10个共同输出时刻；NATIVE_COORDINATES_VOLUMES_VERIFIED的8→1映射；已消费原场在读取窗口内前后SHA保持一致，不扩展为原场全部历史不变。工具墙钟154.70秒，为离线诊断开销，不是CFD模块计时或AI加速。
- 原运行/构建仍为M1=1d32b6fda86d730b8e18b1d9f50e1752fffa5416、M3=8f60695ac39dd7c5ce096ad5781528c229f08ce3。准备输入仅system/blockMeshDict不同。初始T映射差异仅浮点舍入级。
- 原生alpha确认初始金属表面M1=105 μm、M3=97.5 μm，体积7.02e-11/7.29e-11 m³，相差3.846%，均符合各自boxToCell中心选择。此项由EXP-003中的推算升级为用户提供的原场诊断证据，不抹去原记录当时的不确定性。

| 1 μs观察量 | M1 | M3 |
| --- | --- | --- |
| 沉积总功率 / W | 755.601608 | 755.601608 |
| 正沉积y质心 / μm | 112.5 | 101.25 |
| 体积源峰值 / W/m³ | 2.202245e15 | 9.060464e15 |
| 正沉积有效支撑体积 / m³ | 6.5745e-13 | 1.58065e-13 |
| 金属最高T / K | 1123.36 | 2274.19 |

- M3峰值约4.11倍、有效支撑体积约24%；M3沉积层映射到粗90–105 μm单元，M1沉积层在105–120 μm单元。用户按积分及体积加权L1计算1/2/3 μs正沉积空间重叠约0（数值精度内）。这是粗共同支撑上的空间诊断，非连续介质亚单元交集证明。
- 结论：INITIAL_INTERFACE_DISCRETIZATION_DIFFERS与EARLY_DEPOSITION_LAYER_MISMATCH有原场证据。总功率相同不等于局部能量输入相同；几何、热源分配与分辨率耦合。不能宣称初始界面独立解释全部早期温差或存在求解器Bug；PHYSICAL_ACCURACY_UNVERIFIED、GRID_CONVERGENCE_NOT_ESTABLISHED、HOTSPOT_NOT_ESTABLISHED、AI_NOT_STARTED。
- 后续仅按新增DEC-007交付独立[M1-IC受控探索](../validation/M1_IC_CONTROLLED_EXPERIMENT.md)。新实验尚未初始化或运行，结果UNVERIFIED；不预填其起熔时刻/温度/沉积/耗时，不覆盖M1/M3原场或报告，阶段1仍IN_PROGRESS。

## EXP-004 — Codex Ubuntu 本机自主 S smoke 验证

- 日期：2026-10-17（Asia/Shanghai）；阶段1、DEC-008明确授权。Codex直接执行本机终端及真实OpenFOAM，LOCAL_CODEX_CFD_AUTOMATION_VERIFIED；既有实验历史不覆盖。详情见[实证报告](../validation/LOCAL_CODEX_CFD_AUTOMATION_20261017.md)及[脱敏指标/哈希JSON](../validation/local-codex-S-20261017-summary.json)。
- 运行/构建/工具SHA：07496d15d1eebcb99f618d148a54af3729210669；批准时PR #4远端HEAD=a5f53b9158871f363a669c16a2a1a631103674b9。Ubuntu22.04.5、OpenFOAM.com v2512、linux64GccDPInt32Opt、GCC11.4.0；新隔离构建通过，二进制/库哈希及实际依赖来源守卫通过。原生源码、库、教程、脚本及S/M配置未改。
- 新案例local-codex-S-20261017-001：原版laserbeamFoam，2048单元，固定dt1e-8 s、10步至1e-7 s；rank1/数值库线程1并限制单逻辑CPU亲和。solver超时120 s、唯一一次尝试，未重试/续算/启动其他CFD。
- blockMesh/checkMesh/setFields/solver均退出0；Mesh OK，3有效方向，1280初始金属单元；SMOKE_CHECKS_PASSED，19场、173日志事件，issues=[]。最终显式离线检查与归档成功；既有S的cumulativeContErr字节自比较回退另用已有M严格语义解析器补查，有限value=8.641891144171712e-10、无量纲，PASS；未改标准。
- GNU墙钟/RSS：隔离构建185.44 s/1230492 KiB（8作业，最大进程值不等于并发内存总量）；solver0.36 s/126568 KiB；准备主体+mesh/solve wrapper范围1.875943304 s；最终离线检查/导出另计0.61 s/20736 KiB。范围不含构建、Git、阶段间等待和准备Python启动，不重复加总嵌套阶段。原始输入/网格/初终场57文件1163232 bytes，采集时案例合计1276402 bytes。
- 反馈包threeD-smoke-feedback.20261017T121903Z.5a055feb3a9143e998ab753f13b1f3fa.tar.gz；SHA256=78573716e1c99ff20fe3320bd8454c61eea5f4db2e0bd3c1fb729f749ec0c58c，11240 bytes。EXPORTED/COMPLETE/RECORDED_SCOPE/RECORDS_MATCH；本轮直接核对23文件/22内部哈希及FILES通过，missing_required=[]、omitted={}。包与原始场/日志/私有路径均只留本地。
- 最终金属最高T330.293282 K，液相率0，MELTING_NOT_OBSERVED；正沉积、五激光、VOF、温度/压力路径有日志依据。PHYSICAL_ACCURACY_UNVERIFIED、GRID_CONVERGENCE_NOT_ESTABLISHED、HOTSPOT_NOT_ESTABLISHED、AI_NOT_STARTED。
- 旧原始数据实际在另一既有本机工作区存在（M1/M3/M1-IC），RAW_DATA_PRESENT。本轮只清点文件并核验已有诊断包，不宣称重新完成原场数值审计。既有IC报告在1/3 μs最高金属T1113.62/1957.76 K，M3为2274.19/4086.86 K，保留“初态干预未复现M3”；详情及旧归档哈希见[静态审查](ALPHA_DEPOSITION_STATIC_REVIEW.md)。
- 后续建议仅为PROPOSED：利用已有原场做只读0.5阈值资格/法向/沉积层审计，先单时刻、零新增CFD；未自动执行。DEC-008是本次执行模式授权，不变更阶段路线、正式M、物理或验收。PR #4保留Draft，不合并。

## EXP-005 — 1 μs光学阈值原场只读审计

- 日期：2026-10-17；阶段1、DEC-009。直接读取Ubuntu既有M1/M3/M1-IC的0/alpha.metal及1 μs alpha.metal、alpha_filtered、rayQ、Deposition和原生网格；零新增CFD，无smoke、旧案例重跑、原场写入或物理/阈值/容差修改。详情见[原场审计报告](../validation/OPTICAL_THRESHOLD_AUDIT_20261017.md)、[脱敏JSON](../validation/optical-threshold-20261017.json)、[分层CSV](../validation/optical-threshold-20261017-layers.csv)。这是限定时刻/字段审计，不替代全场全时刻审计。
- 工具SHA=ba6f73f6af56dc16e0f34b24984166a88fb61b83；M1/M3/IC原运行SHA保持1d32b6fda86d730b8e18b1d9f50e1752fffa5416 / 8f60695ac39dd7c5ce096ad5781528c229f08ce3 / a5f53b9158871f363a669c16a2a1a631103674b9。六份关键历史源码与审查源码一致；54项原场/依赖及10项源码/工具的64个SHA读取前后全部一致。
- 状态：THRESHOLD_HYPOTHESIS_SUPPORTED，限定为“IC半填充层在保存的1 μs状态低于包含等号的0.5光学门槛”。IC97.5 μm层1600单元alpha_filtered=0.49999999999999856–0.4999999999999987，比0.5低1.4432899320127035e-15至1.27675647831893e-15；没有等于/大于0.5者。该层346个rayQ>0单元、无正沉积。初态已略低于0.5，过滤场未修正该表示。
- 原生Cartesian网格及实际Gauss linear设置核验后，内部1444个半填充层单元重建mag(n)=0.9999999800000003，法向有资格但alpha门槛不通过。n_filtered未保存，156个层边界单元不重建。实际正沉积单元均处于可重建内部并通过法向门槛。
- M1与IC全部正沉积仍在112.5 μm，各346单元；M3在101.25 μm、556单元。功率755.6016078368726 / 755.6016078368726 / 755.6016078368696 W；峰值2.2022451587296515e15 / 2.2022451587296515e15 / 9.060463501997016e15 W/m³。这支持初态体积守恒不保持光学资格与局部沉积支撑，不证明全部温差的唯一原因。
- 边界：15份射线VTK全为空路径；rayQ是追踪聚合诊断，不能当射线计数、独立功率或事件序列。不能证明逐射线首遇、反射次数、Fresnel/体内/安全终止各自贡献或所有早期调用；物理准确性与网格收敛仍UNVERIFIED。
- 成本：分析含最终SHA核验48.406255704 s；外层GNU墙钟48.49 s、最大RSS469860 KiB（458.85 MiB），均低于120 s/1 GiB。使用115 s分析截止与1 GiB虚拟内存保守限制。前置字典读取预检0.006 s退出且未读取物理场，复用现有受限字典读取器后完成本次审计；两份记录本地保留。
- 公开证据：JSON15567 bytes，SHA256=d5407277d6595086643bdfc648d49ab8a1756bac57b221970cac8a7547ddafc4；CSV11734 bytes/80层，SHA256=ea59e68dcada5b591cbd6ba9a48b77bef3b530cb19859d1293ec729f6c6ef03e。相关3测试通过，不代表CFD。原始场、日志和绝对路径不提交。
- 下一项PROPOSED：只读抽样追溯半填充父单元的原生体积/限制权重，定量比较限制与光学门槛的不交换性；零新CFD，未自动执行。PR #4仍Draft，阶段1及研究路线不变。

## EXP-006 — 最后一次父子体积限制诊断，阈值探索结束

- 日期：2026-10-17；DEC-010，SAMPLED_RESTRICTION_DIAGNOSIS_COMPLETED / THRESHOLD_EXPLORATION_CLOSED。五个IC父单元及40个M3子单元只读，零新CFD、不改alpha/阈值/容差、不覆盖原场；不继续阈值实验链。[简短报告](../validation/RESTRICTION_FINAL_DIAGNOSIS_20261017.md)、[数值及21项来源SHA](../validation/restriction-samples-final-20261017.json)、[子单元表](../validation/restriction-samples-final-20261017-children.csv)。
- 工具提交432d8d7d2bf29f100db4713a2b0e18ea28d12d05；复用m1_ic.volume_restriction，代码与IC原运行a5f53b9158871f363a669c16a2a1a631103674b9的blob完全相同。参考SHA=13c923af2e72f7002cd353764d7c2a5094747e2bc172eb1056926656a64a8ccf匹配manifest；21项读取前后SHA一致。
- 半填充父单元5846/5859/5873各有四个alpha=0、四个=1子单元；实际逐项乘积→fsum分子→fsum子体积分母→除法，均复现保存alpha=0.49999999999999867；气/金属控制分别0/1，五样本与参考及原0场逐位一致。
- 精确ASCII坐标构造所得半填充分数比0.5低1.1500000000000017e-15；把已算double子体积当精确有理数，差值分别−1.38781085177771e-15 / −1.3512895135730315e-15 / −1.38781085177771e-15。最终fsum/除法误差为+5.554322222752219e-17 / +1.9021884022843542e-17 / +5.554322222752219e-17，均不造成门槛跨越。不能将其描述为“最后一次除法把精确0.5舍入到阈值下方”；保存坐标表示及体积构造已有微小不对称，未追溯网格生成前历史。
- 定义R为体积平均、H为alpha>=0.5。实际半填充样本R(H(alpha))=0.49999999999999867、H(R(alpha))=0，差约−0.5；即使理想等体积精确算术，前者=1/2、后者=1，差+1/2。非交换性不依赖浮点，表示微扰可改变临界粗资格及差值符号；这些资格量不是吸收功率。与EXP-005的1 μs沉积错层一致，不证明全部温差唯一因果。
- 单次诊断含最终SHA7.573650959 s，外层GNU墙钟7.66 s、RSS163020 KiB（159.20 MiB），低于10 s/256 MiB；8.5 s分析截止及256 MiB虚拟内存保护未触发。两项精确算术测试通过。没有重跑诊断、CFD或清理。
- JSON38728 bytes/SHA256=741c6fcf5321bfb0407bc1b6a2a322b84c4d6396ff3ed86c1b04d3a8c3351a93；CSV4112 bytes/SHA256=8a374e56b9c3559d3788e56d00e163ecf31b9a4657b85a7298177fd8c160309a。仅脱敏摘要/小表/源码提交，原场和私有资源记录留本机。
- 按负责人要求结束阈值探索，随后提交[正式M候选与阶段2简短提案](M_SELECTION_STAGE2_PROPOSAL.md)：优先提请批准原M1为固定性能开发负载，物理参考用途保持未验证；阶段2仅建议三次无埋点基线加一次原版外部采样，未自动运行、未选定AI或改研究路线。PR #4保持Draft，不合并。

## EXP-007 — 阶段2三次原版M1基线通过，调用栈采样权限受阻

- 日期：2026-10-17；DEC-011已正式批准原M1固定性能开发用途及本批限定阶段2。状态THREE_BASELINES_PASSED_SAMPLING_BLOCKED；不把M1登记为物理/网格准确性参考，不标阶段2热点任务全部完成。[完整脱敏报告](../validation/STAGE2_M1_PERFORMANCE_20261017.md)、[JSON](../validation/stage2-M1-20261017-summary.json)、[运行CSV](../validation/stage2-M1-20261017-runs.csv)。
- 运行/构建/工具SHA=2d3b2591bb8fec521448f9e47662ab595983f737；新隔离安装复用wmake缓存，build wrapper5.29 s。原M1的25个准备输入SHA、32000单元原生网格和0场10文件冻结；三例及历史原M1初始化清单SHA均2a9e3fef75b6ab988e0bcc23d2353a20fbc41cae4c008c26aba73b551b9395a7。三例使用同一二进制/项目库且运行入口实际依赖守卫通过；原源码/库/教程/物理/容差未改。
- 自动顺序完成三个新目录stage2-M1-20261017-001-baseline-1/2/3，原版rank1/数值线程1、CPU亲和0、dt1e-8 s/1000步/10 μs、每100步写出。所有OS样本观察线程1；保留schedutil及正常缓存，不调系统、不并行CFD、不续算/重试。单solver1800 s及整批1800 s护栏未触发；RSS8 GiB/新增数据3 GiB为MONITORED_ONLY警戒，均未超限。
- 三例solver墙钟205.96 / 206.52 / 204.95 s，RSS243648 / 242656 / 242824 KiB；完整案例墙钟314.794643 / 315.404889 / 313.791609 s；完整检查主体95.762353 / 95.579212 / 95.616881 s，含两次初始化检查的全部检查主体104.976199 / 104.700719 / 104.744685 s。反馈导出约1.92 s/例，均嵌套在完整案例中，不重复相加。
- 每例原检查EXPLORATION_CHECKS_PASSED、issues=[]，10时刻/190场/10时刻uniform及29491日志事件；三例190个输出物理场文件逐字节相同，清单SHA=eb3611844ab57ef13e5e91bfe78ec2902ec5a8f716517ea6b62d0b4a0c7f7803。每例反馈COMPLETE/RECORDED_SCOPE，26文件/25内部哈希和FILES直接复核通过；原报告不改写，完整wrapper成本在批次摘要补齐。
- solver中位205.96 s、均值205.81 s、样本CV0.386607%、极差/中位数0.762284%，通过预先冻结的5%/10%稳定性资格。完整案例CV0.258870%。主动批次949.491482 s（外层949.56 s）约15分49秒，含构建、全部检查/归档；不含代码准备与最终报告整理。新批次目录/安装及案例382257383 bytes；峰值solver RSS约237.94 MiB，未作硬RSS/数据隔离。
- GNU/rusage文件系统输入计数均0，输出225400 / 225392 / 225488；末次/proc逻辑读取均8289437 bytes而read_bytes=0，保留缓存语境；写计数为最后采样下界，不能当完整逻辑输出量或I/O墙钟。详细CPU/写出/样本和磁盘口径见JSON，未构造I/O耗时份额。
- perf6.8.12实际49 Hz用户态cpu-clock调用栈探测在/bin/true上exit255，被paranoid=4拒绝；无可用标准替代采样入口，不安装/sudo/调权限/改求解器。第四例未执行，采样开销NOT_MEASURABLE，不能记0；射线/VOF/物性相变/线性求解/I/O/未知栈份额均null，不虚构排名。
- 直接流程计时：solver占完整案例65.4063%、全部检查主体33.3077%。仅在“整个solver连同原生I/O都消失、其他成本固定、零新增开销”的假设下，完整案例天花板2.8907倍；这不是AI模块Amdahl预测。缺可信模块f/s/h、采样开销及误差/回退证据，第一个AI候选不选定，AI仍NOT_STARTED。
- 公开JSON25334 bytes/SHA256=8f097585f64bdf68ff3742f6886a41e6e41aac03953bd910097e155f9f7a6bfc；CSV557 bytes/SHA256=a8ee584d9bf5acc5f814109b5ebaa75cc0e66bd156bcdbc46a6b4ca1d30d77ae。原始场、日志、程序安装、环境及资源原记录留本地；仅脱敏摘要与冻结记录推送PR #4，Draft、不合并。

## EXP-008 — 隔离可关闭阶段计时：S门槛与唯一完整M1

- 日期：2026-10-17；授权DEC-012；状态 **M1_TIMING_PASSED**。实际工具/运行SHA=`6b8a5ac471bd8f1fa48e9abcdd11ff70bf1ddb05`，基线原库构建SHA=`2d3b2591bb8fec521448f9e47662ab595983f737`。阶段2限定观测已完成，AI仍NOT_STARTED、物理/网格参考UNVERIFIED。
- perf免sudo探测exit255/paranoid=4；无合适替代采样器。首份构建成功后因工具错误预设geometricVoF路径而在零CFD时停止；实际和基线同来自OpenFOAM，改为全部动态依赖来源逐项相同后执行，预检48.851 s及原记录保留。没有失败solver重试；实际只有一次S和一次M1。
- 独立laserbeamFoamStageTiming，原main移除计时语句后字节一致，头文件内容/优化/原库不变。互斥steady_clock累计，无逐单元/逐射线日志；默认关闭，最终单次CSV。禁用/纳秒闭合/源码守卫测试及全部295项测试通过；测试不执行CFD。
- S=2048单元/10步，solver0.34 s、126720 KiB，原数值检查PASS、issues为空；19场/1时刻/3个uniform文件对原S逐字节一致，uniform标量另按原M解析器严格验证。
- 唯一M1=32000单元/1000步/dt1e-8/10 μs/每100步输出，25项输入与冻结配置一致，10项原生网格/初态SHA一致。原完整检查EXPLORATION_CHECKS_PASSED、issues为空；190场/10时刻/30个uniform文件对**全部三个原版基线**逐字节一致，29491诊断事件。
- M1 solver墙钟205.07 s、user203.34 s/system1.63 s、RSS238732 KiB；相对205.96 s中位−0.89 s/−0.4321%，在204.95–206.52 s原范围内，未观察到>5%墙钟增加。单次差值不能证明计时本身零/负开销。GNU timeout1800 s/rank1/thread1/CPU0；日志落盘、不高频轮询。
- 互斥累计：VOF1000次8.694355 s/4.2397%；updateProps1000次4.698286 s/2.2911%；激光沉积1000次23.503735 s/11.4613%；U1000次19.006525 s/9.2683%；T1000次79.106177 s/38.5752%；p3000次61.626799 s/30.0516%；原生输出边界1000次（实际10次写出）4.109849 s/2.0041%。另mixture2.273694 s、turbulence0.001433 s、MTHD求解0次；全表见报告/CSV。
- 阶段纳秒和与内部总计204.939328627 s精确一致；外部进程边界差0.130671373 s。初始化0.219538317 s、其他1.698938148 s加外部差合计未归入物理模块2.049147838 s/0.99924%，不重复加总。stdout I/O计入所在阶段，原生输出不是全部I/O。
- 既有日志：T线性求解7244次/8705总迭代、p_rgh3000次/16099总迭代。momentumPredictor=no，无U线性求解；laminar。T含热/相变迭代，p含通量/速度修正；纯线性求解、组装及射线子阶段份额未测。T+p阶段合计68.6268%值得优先成本研究；不据调用次数分配时间，不预选AI。激光阶段有11.46%成本但非主导；不预设射线AI。
- Amdahl仅作极端上限：整个T/p/激光阶段降为零、其余不变且无新开销，solver上限分别1.628/1.430/1.129×，不是可实现AI收益。下一项建议仅只读审查现有T/p源码/日志及保留数值约束；细分计时或AI必须后续批准，本轮结束后不自动执行。
- 有效批次348.735 s（隔离构建46.362 s、S/M1及检查/哈希），此前预检另48.851 s，合397.586 s，报告/Git不计；M1全检查92.224 s单列，不进入模块分母。有效本地目录/两案例约128.61 MB，M1案例约120.96 MB；MONITORED_ONLY，无RSS/磁盘硬隔离，未达8 GiB/3 GiB观察警戒。
- 2009项受保护原版源码/教程、旧S/三次M1全案例及原安装内容SHA前后一致；清单SHA均`b99a49fe1ceaa6f58d4647546dbf8d62a54811e825e44dddf493559daddfd2f3`。原始结果/日志留Ubuntu，原版src/applications/tutorials/冻结输入未改，不清理/覆盖旧数据。
- 脱敏[实测报告](../validation/STAGE2_M1_TIMING_20261017.md)、[JSON](../validation/stage2-M1-timing-20261017-summary.json)（14780字节，SHA256=`d585ff551e581bc8bf04e652b3e4a1384c0991d24f625f2c7079f2de30e7c0b0`）、[CSV](../validation/stage2-M1-timing-20261017-modules.csv)（542字节，SHA256=`93c09dd88d7bbdb72389fae265fc0bbb99f331a9a1b0afb241914e86c5c1b530`）。二进制SHA=`650762c4dbd47efc68b4dc4ceb73e0e18f62db0a4806b5e434df76917f71ea33`，生成main SHA=`c169b241914a780f5d95ca1803e4f738f7f49b4b7c13bfa3045e4aaff10e4211`，源码溯源见JSON。PR #4保持Draft，不合并。

## EXP-009 — T/p内部只读工作量与时间演化审查

- 日期：2026-10-17；授权DEC-013；状态READ_ONLY_TP_ANALYSIS_PASSED；零新增CFD、原版/容差/AI均未改。起点37d4400d572dd4023477d08255ed252812214b6c；新解析工具独立SHA记录在JSON，交付版本查git历史，不冒充起点已有代码。
- 原mc.parse_log/scan_log验证四份既有M1（三次原版+一次粗计时），1000步T/p/epsilon1完整事件序列SHA一致。只读分析14.472 s，18项消费文件前后SHA不变；本机v2512控制代码另有读取窗口SHA。T/p内部时间份额仍UNMEASURED，既有T38.58%/p30.05%仅为父阶段墙钟。
- T7244调用/8705线性迭代，平均1.2017/最大3，39次0迭代；每步1–21次T校正。p3000调用/16099迭代，平均5.3663/最大25，629次0迭代；每步固定3调用。p校正位置1/2/3的迭代分别2747/5540/7812；第三次Final字典relTol0，其余0.05，不按次数换算时间。
- T首个多校正步228（2.28 μs）；(7,10] μs占T调用77.28%。p早期大量0迭代、后期迭代工作增加，只有次数演化，没有子模块时间演化。
- 新增数值背景：258步达到21次热校正且最终max epsilon1变化残差>1e-6，首次步738/7.38 μs（0.07114668063610671），各步最终残差最大1。TEqn do-while中iter从0开始、尾部++iter及<=20允许21次；四日志相同。原检查契约没有要求该残差每步收敛，因此原PASS及字节一致性保留；不把这批后期状态称作已收敛相变参考/AI真值，不自行改循环或容差。
- 最小后续测点为T四处（组装、solve、相变后处理、其余）/p三处（组装、solve、更新），加现有父边界组成互斥8类，约37976次新增切换。5批200万次的非CFD计时器微基准中位28.2509 ns/次，对应约0.001073 s调用量级；未来分箱/编译布局等净开销仍UNVERIFIED。
- 唯一PROPOSED方案：隔离可关闭副本，先一次S门槛再最多一次冻结M1；190场/10时刻/30 uniform对三原版一致并复核事件序列/保护SHA、纳秒和闭合，>5%墙钟增加不排名。solver预算S120/M11800 s、整次20分钟，RSS8 GiB/数据3 GiB MONITORED_ONLY；独立Ubuntu进程与系统timeout。本轮未实现/运行，不是执行批准。
- 研究优先级是区分T重复组装/相变与solve、p预测/更新与solve；低T线性迭代和p零迭代都不能证明求解API便宜。初值/预条件/复用只是潜在假设，未选AI；后期相变收敛缺口保持公开，不凭调用数分配成本或宣称收益。
- [报告与唯一提案](../validation/M1_TP_INTERNAL_ANALYSIS_20261017.md)、[JSON](../validation/M1_TP_INTERNAL_ANALYSIS_20261017.json)（11364字节；SHA256=1a38b5bfd56c1178e4b7645767b530c7969b79e4a0f406437b50026be4021b10）、[10箱CSV](../validation/M1_TP_INTERNAL_TIME_BINS_20261017.csv)（549字节；SHA256=4d919b3cc5db0efb90a18778b3c928ff565785093600b09b003682221ba97f73）。原日志/逐步事件/微基准源和原始输出留Ubuntu。2项针对性测试通过，不启动CFD；PR #4仍Draft。

## EXP-010 — 批准后的T/p内部互斥十箱计时

- 日期：2026-10-18；DEC-014；状态 **M1_TP_INTERNAL_TIMING_PASSED**。实际运行HEAD=a14e5e1d3ad181ca71db6edb979000373d917332；私有观察代码、驱动及生成main/TEqn/pEqn各有独立SHA，不把其冒充授权提交已有代码。按公开边界仅提交脱敏报告/数值证据/记录，原观察副本留本机。
- 原版tracked框架/solver/方程/库/输入/迭代上限/容差均不改。复用隔离粗计时，私有副本T四处/p三处互斥切换，10个100步物理箱、初始化箱0单列；无新作用域/循环日志。移除观察语句后main/两个方程头逐字节复原；禁用/闭合/错误CSV拒绝的两项非CFD预检通过。
- 唯一S solver0.33 s/127488 KiB，原检查PASS；19场/1时刻/3 uniform及T/p/epsilon事件与原S一致，计时闭合后才启动唯一M1。没有失败重试/续算。
- M1原完整检查EXPLORATION_CHECKS_PASSED、issues为空，190场/10时刻/30 uniform分别对三次原版基线逐字节一致；25项准备输入与10项原生mesh/0场SHA一致。29491诊断事件；T7244调用/8705线性迭代、p3000/16099。T/p/epsilon1事件序列逐项一致，258个21次热校正后残差>1e-6的步数/位置完整保留。
- M1 solver205.01 s/RSS242180 KiB（236.50 MiB）；相对205.96 s原中位−0.4613%、相对粗计时205.07 s为−0.0293%，在原重复范围内，未观察到>5%增加。单次变化不等于计时净开销或加速。所有叶/独立父/箱0–10/全局纳秒精确闭合；内部总计204.872072782 s，外部边界差0.137927218 s。
- T父79.143062163 s：T_ASSEMBLY31.265989050 s（solver15.2510%）、T_SOLVE13.740892604 s（6.7025%）、T_POST_PHASE3.330317147 s（1.6245%）、T_OTHER30.805863362 s（15.0265%）。p父61.486699030 s：P_ASSEMBLY6.104733755 s（2.9778%）、P_SOLVE12.962529164 s（6.3229%）、P_UPDATE18.135859559 s（8.8463%）、P_OTHER24.283576552 s（11.8451%）。父子不可重复相加；solve是完整API，不是纯迭代内核，POST/OTHER的准备、边界/诊断/析构范围见报告。
- 最后3 μs T59.344114912 s/全部T的74.9833%，对应5598调用。其中T组装23.856456 s、其他准备23.144400 s、solve9.800886 s、POST2.542373 s。300步中258步未满足残差、42步其他，不能全归258步；箱10全部100步未满足，故258步T成本仅能界定22.180–59.344 s（28.03%–74.98%）。不冒充精确逐步计时。
- 加速证据：两solve API合26.703421768 s/13.0254% solver；固定其余成本/调用轨迹、整API归零、h=0时solver上限1.14976×，局部2倍仅1.06966×。T组装+其他准备62.071852412 s/30.2775%，归零上限1.43426×；p预测准备+更新42.419436111 s/20.6914%，归零上限1.26090×。这是极端否决边界，不是可实现AI收益，重叠范围不能相加。
- 优先只读研究重复算子/源项及p预测/更新的数据依赖和保留数值契约的复用条件，不能预先宣称都可缓存或选定AI。仅优化线性API无法在本固定轨迹达到solver2倍；不泛化到别的网格/工况。保留258步非线性未收敛风险，不把原版后期状态当物理真值或AI准确性参考；本轮不更改循环、容差或追加修复模拟。
- 主动构建→最终检查/保护SHA360.293 s（GNU外层360.39 s），隔离构建46.363 s、原完整离线检查96.119 s单列。外层1200 s系统截止/内层foreground，S120/M11800 s上限另受剩余批时约束；rank1/线程1/CPU0，阻塞等待/日志落盘。外层命令最大RSS1189764 KiB，solver RSS另报，不是全工作站峰值。末次新目录及两例128920356字节；8 GiB/3 GiB MONITORED_ONLY观察未触警戒，无硬RSS/磁盘隔离。
- 2703项受保护tracked native/教程/benchmark/profiling/scripts及运行前全部runs/validation条目内容SHA前后一致（当前目录排除），清单SHA均d974413c6cc86500a83bf37140790e031de0f3cb2db51d160c7b98f57b14b6c4。原始场/日志/私有代码本地保留，无覆盖/清理。二进制SHA=7f0b32d8aa70577a0c5219bbb0f4729529daa08aaa1e83a45ac1606874ad721f；实际库路径与基线逐项一致，基线库构建仍2d3b2591bb8fec521448f9e47662ab595983f737。
- [结果报告](../validation/M1_TP_INTERNAL_TIMING_20261018.md)；[JSON](../validation/M1_TP_INTERNAL_TIMING_20261018-summary.json)33765字节/SHA256=7262c05e1bd9e4c17afb891de3aab7b583af9cc54a0f9a2e74d3e98fe4c2f753；[模块CSV](../validation/M1_TP_INTERNAL_TIMING_20261018-modules.csv)426字节/SHA256=ba8a292e21838137ae24acf8ea08078efeffc8297e12196cb9818d125b18b333；[10箱CSV](../validation/M1_TP_INTERNAL_TIMING_20261018-bins.csv)1475字节/SHA256=e668829a7cb832e560a3843121ac5002085dff9c889f8938abd8bb98a22fe34e。PR #4仍Draft、不合并；本次额度已用完，不自动新增CFD或AI开发。

## EXP-011 — 重复计算与数据依赖静态审计

- 日期2026-10-18；DEC-015；状态ONE_CONDITIONAL_CANDIDATE_PROPOSED，零新CFD/优化实现/AI/容差修改。起点de4c959457b3bceb1a6b5af8bda88aa43b8f551c；26项原版/本机v2512源码、冻结配置及既有小型结果SHA前后一致，不重读大日志。
- 关键依赖：T的cp/kappa等按现有执行顺序滞后冻结，rhoCp/rhophicp/em已经在do-while外；T/epsilon1/TRHS、辐射/蒸发/thermalDamper逐热校正变化，完整矩阵不能因kappa固定而缓存。p的UEqn.H原生实现读取当前U，p每轮更新U/phi，故HbyA/预测通量不能凭矩阵未重组而复用；A/rAU/插值部分还需边界/临时量/约束证明，本轮不选。压力/通量/连续性更新保留。
- 唯一候选T_LOCAL_NATIVE_MAG_GRADALPHA：在一次TEqn内首次原位置求完整原生mag(gradAlpha)，用拥有存储的只读局部值复用，离开TEqn失效；不缓存随T变的thermalDamper或乘积，不跨时间步。防止tmp乘法消费/重写缓存，处理完整patch/orientation/边界与不注册/写出副作用；这些条件未满足即禁用/否决。
- 源码调用次数推导7244→1000次求mag，6244次复用、后3 μs5298次；这是表达式次数而非时间。操作自身g/净收益UNVERIFIED，T_OTHER30.805863 s/15.0265%只是包围阶段；其全归零1.17684×不是候选收益。缓存标量载荷估计0.293 MiB+元数据，非RSS实测。
- 证据等级：已有阶段计时DIRECT；依赖为有条件STATIC_SOURCE；缓存运行字节等价及收益未实现/未测。唯一PROPOSED协议：非CFD命中/tmp/边界测试→一次S ON门槛→同一隔离二进制一次冻结M1 OFF、一次新M1 ON。S每步仅一热校正不覆盖命中；两M1须190场/30 uniform/原检查及T/p/epsilon1/258步序列对三基线一致，所有成本/父子/箱闭合。提议>2%solver配对收益且目标差方向一致才继续投入，仅作待批准保守筛选而非统计证明；否则无收益/INCONCLUSIVE，不追加运行。
- 未来预算提案仍1200 s整批，S120 s/每M11800 s且剩余批时优先，8 GiB/3 GiB MONITORED_ONLY，串行线程1/CPU0，系统进程负责超时/日志、完成后集中检查。实际未批准/未启动。本轮不改258步非线性退出，不把轨迹等价当物理/训练真值。
- [依赖表/唯一提案](../validation/M1_REUSE_DEPENDENCY_AUDIT_20261018.md)、[证据JSON](../validation/M1_REUSE_DEPENDENCY_AUDIT_20261018.json)10684字节/SHA256=a2b2934cd8ff4f0b8106778bc801783163b61189ea006c3965887aef4db94bb5。原版及旧结果只读，PR #4仍Draft、不合并，阶段3未启动。

## EXP-012 — 单项mag缓存原生场测试与非CFD否决

- 日期2026-10-18；DEC-016；最终 **NO_BENEFIT**（针对约2%solver收益筛选，非证明任何正收益不存在）。执行HEAD=ebcb72effcd6b28c037db26aae2308d8a78b01ed；私有原生工具/Make/驱动独立SHA见JSON。原版源码/数值标准不变、无AI。
- 零新增CFD，未推进Time/求解方程/写场；没有S、M1 OFF/ON，也未构建优化求解器。独立工具读取复制的原生M1网格、0–10 μs共11个alpha快照重建梯度，加synthetic非均匀内部/patch；每样本32000单元/6400边界值，12样本×9轮变化damper=108次乘积逐元素字节一致，dimensions/orientation/patch类型一致。缓存fill12/hit96，原输入/缓存经tmp构造/析构及乘法后未变，不注册/NO_WRITE、不跨样本复用；复制输入SHA不变。此正确性不代替完整M1等价。
- 每样本/模式/操作5批，hot256次/批、128 MiB缓存扰动32次/批；共360批/51840运算，完整mag17280次。计时含分配/内部/patch/局部边界/析构及volatile结果读取，未扣chrono开销；扰动在计时外，大于观察LLC但不保证硬件冷缓存，顺序固定不作随机试验声明。
- 完整mag hot批均中位74.723 μs、范围69.679–77.395；扰动中位125.279 μs、范围101.898–136.501。最大精确136500.96875 ns（3 μs样本扰动、32次总4368031 ns）。原完整乘积hot/扰动中位98.496/167.151 μs，缓存命中乘积24.135/89.415 μs；后者不计首次填充/owner生命周期，不是CFD净收益。
- 按运行前DEC-016判据，2×最大批均×全部7244次（比只省6244次更宽松、且忽略缓存开销）=1.97762603525秒/原205.96秒的0.9602%，不足2%目标4.1192秒的一半；触发NO_BENEFIT，停止全部后续CFD。它是经验保守筛选，不是全部CFD/跨机器数学上界；真实M1收益与190场/30 uniform的优化版等价未测，不冒充通过，也无统计显著结论。
- 主动批83.592秒/GNU83.65秒（build12.55/native66.94），native RSS207588 KiB、build/批最大693644 KiB，新本地12281317字节；1200秒系统截止、线程1/CPU0、8 GiB/3 GiB MONITORED_ONLY未触警戒。无重试/续算、无安装/sudo，日志本地、进程独立阻塞完成后集中分析。
- 3189项原版tracked源码/教程/框架/配置及运行前全部runs/validation内容SHA前后一致，清单SHA均7e582f47e0412f926f67ff1f32891750977aa45fa0e7af7e72f7e604e7ea12af；二进制SHA=0bd14242ec4704566c58eda3dfb5dbd2d5e5cd73870a1e66229d2b8672a4da07。原字段/日志/测试源码/二进制本地保留，不覆盖旧结果。
- [否决报告](../validation/MAG_CACHE_NATIVE_20261018.md)、[JSON](../validation/MAG_CACHE_NATIVE_20261018-summary.json)10136字节/SHA256=c473003ceb0a4dbdfa83aa72076d8452e276437971951eed6af467877d17c5ed、[聚合CSV](../validation/MAG_CACHE_NATIVE_20261018-trials.csv)5519字节/SHA256=b0a8c53a4835f35f1cc28d4ca6882f4a9a4918146222642ae761efe680bf253e。停止本候选投入，不扩展其他优化；258步非线性未收敛风险保持，不当物理/AI真值。PR #4继续Draft，不合并。
