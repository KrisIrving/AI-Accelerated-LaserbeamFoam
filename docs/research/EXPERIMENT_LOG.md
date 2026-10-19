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

## EXP-013 — 阶段2收尾与合并审查（零新CFD）

- 2026-10-18；DEC-017；审查起点a1e5e1f7df54e1d8667c59f14f7e5ffee936e6aa，最新main 5e08097d420af3cfb746eda8ec1833da1d068395。负责人批准审查通过后Ready及Merge Commit，旧Draft限制保留为历史，不恢复任何实验额度。
- 297项Python测试、9组shell/mock及shell语法通过；原生源/库/教程/构建入口相对main无改动。3189保护内容SHA再读一致；40项私有源码/输入/清单SHA吻合；冻结树、配置及三例75项输入吻合；DEC/EXP历史只追加。
- 75文件/28既有分支提交及163历史blob审阅：无tracked原始runs/validation或匹配凭据；私有路径模式仅合成脱敏测试夹具。起点两项CI成功、无未处理审查；最终分支提交仍须CI成功、正常GitHub合并许可。未把模式扫描宣称为完备安全证明。
- MAG候选NO_BENEFIT正式关闭；阶段2限定研究收尾、阶段3未启动。258步相变非线性未收敛、物理/网格参考缺口及API/内核成本边界继续公开。
- [完整收尾与唯一AI候选](STAGE2_CLOSEOUT_20261018.md)建议压力初值预测+原生PCG校正，仅PROPOSED；P_SOLVE12.963 s/6.32%，零成本极端solver上限1.06750×。未来数值合同、矩阵采集、离线及CFD预算均须另批，本轮没有AI实现、训练、采集或新增CFD。合并结果/实际SHA以PR #4及Git历史为准。

## EXP-014 — 压力系统前置构建失败，INCONCLUSIVE

- 日期2026-10-18；DEC-018；基准main a8861ea9c0d4514f10606da5d3fb9568b4c86f92，授权/运行HEAD 7f28ed8549c7abee5739aac35e03451237f9db43。
- 唯一阶段build-replay返回2：新增离线工具两处lduMatrix::Amul遗漏v2512要求的direction参数。是工具实现错误，不是原版求解器/科学假设失败。按失败停止、不重试，未修复/重建或执行后续阶段；新CFD=0、S/M1=0、真实系统0/30、离线回放/AI均未开始。
- 格式/残差/数值等价门槛NOT_STARTED/NOT_TESTED，不冒充通过。3343项批次前后保护SHA一致，40项实际源码SHA核对一致；原版/冻结输入/原历史场未改，258步相变未收敛风险保持。
- 外层11.07 s，构建6.62 s，峰值552624 KiB，新增私有数据末次观察约1.07 MB；1200 s系统截止未触发，8 GiB/3 GiB MONITORED_ONLY未越警戒。原件/日志/失败标记保留本机。
- [脱敏失败报告与来源](../validation/PRESSURE_SYSTEM_FEASIBILITY_20261018.md)及JSON给出INCONCLUSIVE；迭代/采集开销/推理验证回退预算均UNMEASURED，目前不建议批准AI开发。只建议另行授权修复与新的原生前置门槛，不自动恢复运行额度；MAG候选仍关闭。
- 新PR只提交证据与记录，保持Draft不合并：数值门槛未通过，文档CI不能替代该门槛。

## EXP-015 — 新批次压力回放接口修复：全部非CFD门槛通过

- 2026-10-18；DEC-019；起点415e97534cb1b0ea85f374d5e16eef2fa545a817，授权/运行HEAD 6cc79354108ffe7c8364e60b098c1ed810dcd3bd。新隔离目录中经v2512签名/标量源码确认两处Amul补component=0；只构建一次且通过，没有修补后重建；不是EXP-014自动重试。
- BUILD_PASS / FORMAT_PASS / RESIDUAL_PASS / REPLAY_PASS。两个2048单元制造SPD系统，有效/无效参考、内部/非耦合边界及精确解独立验证；完整格式/解逐位往返，10个坏输入拒绝。四对原生fvMatrix与ldu解/残差/次数完全相同；12组重复解逐位相同，32次纯线性代数求解，零物理时间推进。
- 12组原生停止均通过，但4组大偏置初值不满足原始尺度真实Ax-b标准，正确拒绝；8个替代初值均改变归一化。严格原始固定门槛不变，独立Python舍入区间在同一侧认证，不用次数推算费用或宣称AI收益。
- 外层16.02 s，控制器15.959 s，构建11.20 s，原生测试0.08 s；峰值670280 KiB/654.57 MiB，新增私有数据约5.53 MB；300 s截止内退出0，1 GiB/200 MiB MONITORED_ONLY警戒未越界。
- 3398保护内容SHA一致，旧失败40项源码与6项证据SHA核对一致，6项原生源与EXP-014哈希一致；原版、冻结输入、旧原场和失败工件只读。原始数组/拓扑/源码/日志留本地，[脱敏报告/JSON/CSV/接口diff](../validation/PRESSURE_REPLAY_INTERFACE_20261018.md)追溯实际版本。
- 具备申请下一次受控CFD采集的非CFD前置资格；真实采集完整性及S/M1全场/事件等价仍未验证，任何新CFD须另批。本轮CFD=0、S/M1=0、真实系统=0，不AI，258步未收敛风险及MAG关闭保持。PR #5维持Draft，不合并。

## EXP-016 — 真实压力系统采集/回放通过，AI初值研究当前NO_GO

- 2026-10-18；DEC-020；起点f2696ca3d1582e6781838f31c7bf21fe9fd4998e，授权/运行HEAD 73491dd5；新批次复用EXP-015回放二进制/序列化头，原版投影与冻结输入/库来源通过，旧额度不恢复。
- 唯一S0.33 s、step5三真实系统完整通过后，唯一M1204.86 s完成step50/150/…/950×三位置30系统。S19场/3 uniform等价；M1190场/10时刻/30 uniform对三原版逐字节一致、原检查issues空，完整事件/T/p/epsilon及258步热校正轨迹相同。
- 原始初值全部33系统回放解逐位一致、初/终残差/次数与在线日志精确相同，固定真实残差通过。30 M1样本原生160迭代；零初值455、含失败回退532，10/30接收；外推170、含回退194，28/30接收，无净迭代节省。外推step750-c3及950-c2虽满足新初值原生停止，仍违反原始固定尺度/相对目标，正确拒绝，不降标。
- 原生核心中位数合计121.819 ms，外推127.558 ms；计参考尺度、复制/特征、核验及失败原生回退169.800 ms，零初值396.332 ms。是独立分量记账，不是在线回退或整CFD性能；不以迭代数换算时间。新固定尺度/核验中位相加约801.431 μs/调用，对3000次的2.404 s仅筛选情景，非全M1实测。
- 全批389.79 s、全检查合96.206 s；峰值1176260 KiB（约1.122 GiB）、M1 RSS243008 KiB；新增约245.74 MB，1200 s退出0，8 GiB/3 GiB MONITORED_ONLY未越警戒。压力solve边界12.876952 s/6.2857%，固定其他工作时零成本极端上限1.06707×；不是纯迭代份额或AI收益。
- 3493保护SHA一致，实际源码/二进制/库、字段/uniform/事件及33数据集SHA留证；原矩阵/场/日志本机保留，仅发布[脱敏报告/JSON/CSV](../validation/REAL_PRESSURE_REPLAY_20261018.md)。EXP-014/015及旧原场不改。
- 执行/数值链路PASS；研究建议NO_GO针对当前批准AI初值开发的收益证据，不是普遍不可能证明或永久路线变更。下一项仅提既有系统PCG内部成本/下界只读审计，不自动执行。本轮不AI、不M2/M3、不重试/续算；258步风险及MAG关闭保持，PR #5维持Draft，不合并。

## EXP-017 — 零新增计算的压力研究收尾与方向重评

- 2026-10-18；DEC-021；起点7e27b28a9237586e60a1ac02ea826698a2930613。仅复用小型公开证据/原生源码与Git历史，零新CFD、构建、矩阵回放或AI；不是新的性能实验。
- 固化EXP-016链路PASS/研究NO_GO：33原生回放通过；30 M1原迭代160，外推含回退194，2个原尺度真实残差拒绝；分量计费121.819→169.800 ms，尚未单列历史维护/推理成本。30样本不能认证泛化或完整CFD收益；旧失败与原始系统保留。
- EXP-010同次205.01 s计时中，T组装/准备62.071852 s（30.2775%），p预测/更新42.419436 s（20.6914%）。仅为互斥包围区间；依赖变化阻止整体缓存，未测可避免份额。不得以次数换算时间或重开MAG。
- 唯一研究候选为受约束T–相变固定点加速，NOT_READY：缺独立收敛参考/误差合同、完整T回放状态、可省费用与创新性论证。不能把258个上限退出步当真值，不能减校正换速度；M1物理/网格参考仍UNVERIFIED，不选择AI方法或授权实现。
- 起点PR7提交/16文件/32公开blob审核，仅文档治理/脱敏证据；无原版/输入改动或匹配敏感数据。历史非空DEC/EXP内容保留，起点Markdown CI成功、无审查线程；保留Draft/unmerged，最终CI另核。27项消费来源SHA不变，不冒充重审全部原场，证据见[简短评估/JSON](STAGE3_DIRECTION_REASSESSMENT_20261018.md)。

## EXP-018 — T–相变固定点数学与文献只读审查

- 2026-10-18；DEC-022；main原版a8861ea9、证据起点9f658caa。零新增CFD、构建、原生回放或算法/AI实现；不是新数值实验。必要源码与小型证据约405 kB/34项归档窗口前后SHA一致，原版消费源/冻结benchmark匹配main；未重扫大日志或旧原场。
- [唯一报告](T_PHASE_FIXED_POINT_REVIEW_20261018.md)定义G_native,C及理想G_*，区分旧时间层/入口冻结/当轮/prevIter；完整T/l场在冻结C及固定边界路径下条件封闭，两个内部数组不足。实查l为calculated patch、原生relax(1)仍修正对角，不能简化成纯Picard/恒等松弛。未证压缩性、根存在/唯一或收敛。
- 独立验收草案区分原l增量、完整固定点残差、温度/相分数互补一致性、同态未松弛离散能量/潜热与边界缺陷；当前仅日志可保留258步未达门槛事实，不能认证能量/完整收敛或物理真值。逐热校正快照、Euler旧层/NO_WRITE冻结量及热矩阵缺失，现有场不足回放，压力矩阵不可替代。
- 核实Walker–Ni2011、Tóth–Kelley2015、Zhang/O'Donoghue/Boyd2020、Kang/Wang/Zhu2025及传统阻尼/Aitken/半光滑相关原文/DOI；报告明确全文与仅摘要/节选访问范围、假设不满足及费用/失败边界。不以LPBF应用宣称创新，不选择AI。Kang的ITEM/TEM不等同于本T潜热源校正。
- 最终NOT_READY；唯一未来提案为零CFD的8单元非正交制造状态/独立残差/单次G往返门槛，未实现、未批准运行。原版次数/标准、压力初值NO_GO、MAG关闭与258步及物理/网格风险均保留，PR #5 Draft/unmerged。

## EXP-019 — 零CFD热制造解与原生G回放门槛通过

- 2026-10-18；DEC-023；起点282f6d48424ca768ac500b0b9088eb3d624e51d0，实际运行HEAD de688dd7（完整SHA见JSON）。新隔离目录，只构建一次。MANUFACTURED_RESIDUAL_PASS / NATIVE_G_REPLAY_PASS / NEGATIVE_CONTROLS_PASS / PROVENANCE_PASS；BUILD/FORMAT亦PASS。零S/M1、零物理时间推进、零真实采集/AI/加速算法。
- 独立8单元剪切非正交逐面/Euler计算在原生执行前制造已知T/相分数与平衡源；原材料/辐射/蒸发/阻尼及原生BC/数值/停止语义保留。三组矩阵最大缩放误差1.681e-16，原生同态未松弛F_E最大2.722e-16；固定预算分别5e-12。完整快照及三组原生G的10文件/组逐字节一致；所有源、旧层及边界参与核对。
- 正例平衡G各0线性迭代，不能冒充非平衡覆盖；三个组装后+1 K线性恢复探针各2次原生迭代，最大T误差1.415e-10 K、相变一致性2.005e-12。含gamma256的独立真实残差上界最大1.772e-11<原1e-9；保持未扰动T参考归一化也通过，不降标。
- 六项负例全部拒绝。特别是冷固T+10 K的实际原生G：epsilon增量=0，但输出T偏差0.025413 K、同态能量缺陷8.92879e-6>既定2e-9；只从已产出状态集中分析，不追加G。证明该构造下增量单判不足，不解释真实258步或AI成败。
- 主动批次23.90 s、控制器23.8353 s，唯一构建17.3406 s；峰值810792 KiB/791.79 MiB，新增末次约3.78 MB。300 s硬截止内退出0，rank1/线程环境1/CPU0，1 GiB/200 MiB MONITORED_ONLY阶段后观察未越界，非内存/磁盘硬隔离；工具编写及最终报告/Git不计主动执行。
- 4225项批次前后保护内容SHA一致，26项消费源/输入、8项私有工具及实际库/二进制SHA留证；原始工具/数组/日志本机保留，仅提交[脱敏报告/JSON/CSV](../validation/T_PHASE_MANUFACTURED_REPLAY_20261018.md)。原版、三基线、旧失败及研究负结果不改。
- 只获得申请下一轮真实单步采集/数值参考设计的前置资格；任意非平衡G、真实T回放状态、收敛参考与物理/网格准确性仍未验证。不实现采集器/AI，不恢复旧额度，压力初值NO_GO、258步风险及MAG关闭保持，PR #5 Draft/unmerged。

## EXP-020 — 真实单步热状态采集：唯一构建失败停止

- 2026-10-18，DEC-024；负责人明确批准新批次，起点a908d7997fce984ad51e23e450dc09ce6670381d，实际执行HEAD=9d2d2cd94d9a6d85e307d03e00db8e31b05dc746。报告：[真实单步热状态采集](../validation/T_PHASE_REAL_CAPTURE_20261018.md)、[脱敏SHA/资源JSON](../validation/T_PHASE_REAL_CAPTURE_20261018-summary.json)。PR #5保持Draft、不合并。
- INCONCLUSIVE。唯一wmake隔离构建失败（exit2）：新增thermalReplay.H先于Polynomial.H引入，Polynomial<8>未声明，继发polycp_m/g错误。为集成工具的头文件依赖遗漏，不是原生物理、固定点/AI算法失败。没有修补重建、重试或续算；零S/M1、零原生G、零真实状态/残差数据。原制造框架平衡证据不扩展为非平衡/真实链验证。
- CAPTURE_FAIL / G_CHAIN_REPLAY_FAIL / NUMERICAL_PARITY_FAIL / INDEPENDENT_RESIDUAL_EVALUATION_FAIL均指NOT_RUN_BUILD_GATE_FAILED，不能解释为已经测得数值不一致或独立F_E超标；PROVENANCE_PASS。没有分轮结果可报告，不生成空表冒充测量。
- 预注册SHA256=622d9fd8b2449d4ece020270104da8b3bdb7819f0f895d047208d59c8b53227d，44项工具/16项消费来源内容不变；4750项保护内容SHA不变。编译失败工件/全部日志留新本地目录，只推脱敏摘要。首次后台包装器在控制器入口前退出、尚无构建/CFD；保留空日志后换持久会话，实际仅一个主动批次。
- GNU批次17.55 s，控制器17.3792 s，唯一构建11.66 s，峰值797208 KiB（778.52 MiB），末次主动数据1650796 B；rank1/thread1/CPU0，1200秒硬截止未触发；8 GiB/3 GiB MONITORED_ONLY阶段后观察，非cgroup/磁盘硬隔离。编写/最终报告/Git另计。
- 完成后停止；本次额度已消耗，不具备另批独立收敛参考的新增资格。仅建议另行批准一次隔离包含依赖修复和非CFD非平衡G配对门槛，不自动恢复CFD额度。原258步未收敛、压力初值NO_GO、M1物理/网格缺口、MAG关闭及AI未启动保持。

## EXP-021 — 回放头依赖修复与非平衡G门槛

- 2026-10-18，DEC-025；负责人明确回复“批准本次非CFD新批次”，起点6b5dc548979b7b184b38a9be19145a57d5d02b81，执行HEAD=8e432de090b81d3bdcf85b44d6eca614d72fc102。报告：[非平衡G门槛](../validation/T_PHASE_HEADER_NONEQUILIBRIUM_20261018.md)、[三组CSV](../validation/T_PHASE_HEADER_NONEQUILIBRIUM_20261018-comparisons.csv)、[脱敏SHA/资源JSON](../validation/T_PHASE_HEADER_NONEQUILIBRIUM_20261018-summary.json)。PR #5 Draft/unmerged。
- BUILD_PASS / NON_EQUILIBRIUM_G_REPLAY_PASS / RESIDUAL_PASS / PROVENANCE_PASS。新副本回放头显式包含fvCFD.H和Polynomial.H，正文/G/序列化/残差器保持EXP-020；最小非CFD入口唯一wmake通过。旧失败工件不改，不修补重建。零S/M1、真实热采集、物理推进或AI。
- 原96个制造输入/源按字节复用；三母状态各一次非平衡直接G和一次回放，各2次原生线性迭代；完整内场/patch/实际Euler旧层/prevIter/标志、两矩阵/源/事件等195项文件比较逐字节一致。clip活动集变化4/3/4单元；三组T各24个patch值变化，糊状epsilon另24值变化；原生T/epsilon事件字节相同。独立矩阵/relax/逐面Euler交叉误差最坏2.522e-16/9.958e-17/1.933e-16，零梯度边界缺陷0；真实线性加舍入界最坏4.491e-11，严格<原1e-9。
- RESIDUAL_PASS不是非线性收敛：单G同态F_E最大固定缩放缺陷约0.059815/0.040852/0.032226，均超过原2e-9；epsilon增量约0.35，糊状相变/温度缺陷0.883056。联合草案正确拒绝三终态，没有延长校正、改源或放宽标准；不据此解释M1真实258步。
- 注册SHA256=5345a37f772d01109f60384f6dddd25dc9e84bd0facecd217017efadb3253102；43工具/18消费来源/96输入固定，4910项保护SHA不变。GNU批次25.14 s、构建18.32 s、峰值818916 KiB（799.72 MiB），末次主动数据4192070 B；rank1/thread1环境/CPU0，300秒系统截止未触发，退出0。1 GiB/200 MiB MONITORED_ONLY，非硬内存/磁盘隔离；编写/报告/Git另计。原始数据/工具/日志留本机。
- 仅具备申请下一次受控S/M1采集的非CFD前置资格，不自动恢复step738或历史额度；完整CFD观测求解器构建、真实21轮链及数值参考仍未验收。本批结束，不自动新实验或AI。压力NO_GO、258步风险、M1物理/网格缺口及MAG关闭保持。

## EXP-022 — 真实热链自主验证：S符号零恢复门槛失败停止

- 2026-10-18，DEC-026新一次性分阶段明确授权，起点06f072e97814d95efc571d9c531d47ad16c408b3；执行HEAD=d23dc893427973986878c07c018f639930089ed9。报告：[真实链门槛停止](../validation/T_PHASE_REAL_CHAIN_20261018.md)、[位差CSV](../validation/T_PHASE_REAL_CHAIN_20261018-signedzero.csv)、[来源/资源JSON](../validation/T_PHASE_REAL_CHAIN_20261018-summary.json)。INCONCLUSIVE；PR #5 Draft，不合并。
- BUILD_PASS / NONCFD_GATE_PASS / S_PARITY_PASS；CAPTURE_COMPLETENESS_FAIL / G_CHAIN_REPLAY_FAIL（S单G失败，M1真实21轮未执行）；M1_PARITY、真实INDEPENDENT_RESIDUAL_EVALUATION及EXPLORATORY_REFERENCE均NOT_RUN。PROVENANCE_PASS。只有一次完整观测构建、唯一S；原检查issues为空、19场/3 uniform/完整事件与原S字节一致。未使用剩余预CFD构建额度、无S重跑/续算、零M1/延拓/AI。
- S step5原生2次线性迭代；9个矩阵/源/初终值/指标/几何文件完全一致，但入口/出口全状态分别3314/3051个binary64零值符号位不一致，全部−0→+0，数值数组/时间/维度/类型/标志相等。严格字节门槛不放宽，停止后续科学实验。完整原二进制状态仍保存，不把数值相等写成回放PASS。
- 源码核实v2512 ScalarRead会把±ScalarVSMALL区间归零，Field uniform压缩也可合并混合符号零；当前元数据恢复跳过值数组、依赖ASCII读值。允许范围内两次新副本非CFD格式诊断（-0.0 token；从原metadata数组逐项科学计数法/nonuniform）均FAIL，保留全部失败证据；没有追加构建/CFD或恢复原S门槛，不继续第三种方案。真实F_E未评价，不宣称新M1收敛/不收敛结论。
- 注册SHA256=8532e73221d220ac86a1c105c13f7e9b63111cbceadd353793731425cc3fc7ea；观察源码投影精确还原原版，原库来源相同，5578保护SHA及工具/消费来源不变，两项诊断另确认原S/回放/源码不变。主批次217.53 s，构建208.39 s，S solver0.42 s；峰值1234456 KiB（约1.18 GiB）。两项诊断GNU0.92/4.11 s，合计进程222.56 s，最后诊断在原起点528.316 s内结束，未触发1200 s截止。rank1/thread1环境/CPU0；8 GiB/3 GiB MONITORED_ONLY，非硬资源隔离。
- 末次审计逻辑39.157 MB/唯一inode38.843 MB/实际分配40.542 MB，241个新工件硬链接保留所有路径/字节，旧数据不动。原始工具/字段/矩阵/日志本地留存，公开仅脱敏记录；编写/报告/Git另计。尚无传统算法研究资格；后续只建议另批二进制位保真格式/混合符号零门槛，再申请新S/M1。压力NO_GO、MAG关闭、258步及M1物理/网格缺口保留。

## EXP-023 — binary64恢复与真实M1链：第二轮prevIter元数据失败

- 2026-10-18，DEC-027新授权，起点97563b8d0d56e93406a58d440146adcadf7fefea；授权/离线构建HEAD=8522a838ee6e64d9fe8bdb06b475e69c8a7a3081。报告：[位保真链验证](../validation/T_PHASE_BITEXACT_CHAIN_20261018.md)、[21行原生/部分独立残差](../validation/T_PHASE_BITEXACT_CHAIN_20261018-residuals.csv)、[逐轮验收/SHA](../validation/T_PHASE_BITEXACT_CHAIN_20261018-integrity.csv)、[来源/资源JSON](../validation/T_PHASE_BITEXACT_CHAIN_20261018-summary.json)。INCONCLUSIVE；PR #5保持Draft、不合并。
- 唯一窄原生构建PASS，29状态原始binary64逐分量memcpy恢复，原生对象建好后覆盖全部内部/patch/旧层/prevIter/冻结数组及标志；没有ScalarRead或符号零归一化。混合/均匀两组各102400分量/174数组全字节相同，9类不兼容/损坏负例拒绝。真实旧S完整before/after/矩阵/源/线性/事件与独立算术PASS；线上观察器二进制及库未改，复用EXP-022原19场/3 uniform/173事件证据，零新增S。EXP-022原失败记录不改。
- 唯一冻结M1采齐step738第一次TEqn原生21轮。原检查EXPLORATION_CHECKS_PASSED、issues=[]；190场/30 uniform/10时刻对三基线逐字节一致；完整T/p/epsilon事件/258个未收敛上限步轨迹不变，所选原生事件24491行三基线原字节一致。1000步/dt1e-8、方程、边界、材料、原生smoothSolver/symGaussSeidel/容差/退出规则不变。
- 连续21G只执行一次。第1轮全部状态/快照/矩阵/源/事件字节一致，独立算术/原线性/边界PASS。第2轮所有浮点数组、9个矩阵/源/初终值/指标/几何文件仍一致，但T_prevIter、epsilon1_prevIter在before/after的timeIndex原生0、回放738，前后各4字节不符。严格门槛FAIL，停止2–21轮独立残差及3–21轮完整验收，不再修复/重放。隐藏prevIter旧层/构造顺序只为待证解释，不宣称修复或完整C已验证。
- BUILD/NONCFD_FORMAT/BIT_EXACT_RESTORE/S_G_REPLAY/S_PARITY/M1_PARITY/PROVENANCE均PASS；G_CHAIN_REPLAY_21_FAIL，整链RESIDUAL_EVALUATION_NOT_RUN（仅首轮PASS）；NONLINEAR_CONVERGENCE_STATUS_FAIL仅依据原生终轮epsilon增量0.07114668063610671>1e-6，独立终态F_E/相变缺陷未知。首轮F_E最大固定缩放0.0049226720、L1 86.4566 W、相变/温度缺陷0.05380794，能量交叉2.1853e-16、真实线性加舍入3.8699e-12、边界0 K；不是第21轮值或收敛参考。
- 三工程循环/一次构建，完整保留两次控制器工程中止：制造cp正值假设错误套用原calculated patch零值（只修适用域，数值预算不变）；把MONITORED_ONLY数据警戒误作硬门槛（按原政策纠正，仅验收已有G，无CFD/G重跑）。最终真实元数据失败停止，无第四次修复。6468/6796保护SHA及消费来源、工具/冻结原版树和库不变。
- 同一绝对1200秒截止，主动起点至最终停止733.58 s；GNU26.31+389.08+25.90 s；构建18.44 s、M1 solver234.07 s、原检查95.3163 s、21G29.67 s、首轮同态无求解组装1.30 s。峰值853988 KiB（833.97 MiB）；rank1/thread1/CPU0。数据实际曾越3 GiB警戒至3.575 GiB，不隐瞒；仅本批新完成工件2688个SHA校验硬链接保留所有路径/原字节，末次逻辑3.889 GB/唯一709.30 MB/分配711.86 MB。8 GiB/3 GiB均MONITORED_ONLY，不冒充硬隔离。初始工具准备约169.72 s、最终报告/Git另计，修复间隔已含733.58 s。
- 本批结束，无延拓/第22G/传统加速器/AI。不具备独立收敛参考实验资格；唯一未来建议为另批零CFD复用本次真实快照修复prevIter生命周期并重验完整链，不能自动执行或新增S/M1。压力初值NO_GO、MAG关闭、258步和M1物理/网格缺口保留。

## EXP-024 — prevIter生命周期修复、真实21轮位保真及独立残差终验

- 2026-10-18，DEC-028新非CFD授权，起点1371a10d578939f30136af34a949b86b4c4de6e3；授权/唯一工具实际构建HEAD=69d662ec8c844f34c75751a6c40a3aa5fa8422bf。报告：[真实21轮终验](../validation/T_PHASE_PREVITER_FINAL_20261018.md)、[21轮残差](../validation/T_PHASE_PREVITER_FINAL_20261018-residuals.csv)、[11项逐轮完整性/SHA](../validation/T_PHASE_PREVITER_FINAL_20261018-integrity.csv)、[来源/费用JSON](../validation/T_PHASE_PREVITER_FINAL_20261018-summary.json)。全部技术门槛PASS，NONCONVERGED_OBSERVED；PR #5 Draft、不合并。
- 原生生命周期因果探针：旧恢复先oldTime再复制prev，prev带1层历史，metadata恢复索引0后真实storePrevIter触发storeOldTimes推进到738；新顺序先构造prev、再建父场oldTime，prev无历史，赋值保留原索引0。v2512命名复制构造/强制赋值/时间层分支与原TEqn/Euler顺序对应，原生prev在0建立无历史，后续赋值不复制父场历史。不是硬写timeIndex0或删元数据。原binary64/标志恢复、oneG/组装数值体不变。
- 一次原生构建、两次调试循环。首循环探针及第1轮完整回放PASS，第2轮独立case缺system/controlDict引用，G执行前退出；日志/源码保留。第二循环只建立只读上下文视图，复用相同C++和二进制，原快照不改。第1/2轮单G和连续两G全部完整状态/ASCII/矩阵/源/原事件字节相同（局部共4G）。随后唯一连续21G，每G立即比较11项完整二进制工件，21轮及42条原T/epsilon事件字节差0；22条生命周期记录保持prev无旧层、索引等于原捕获值。零新CFD/S/M1、Time推进或第22个链G。
- 全链通过后才对21个输出态做同态无求解组装和独立逐面Euler诊断；沿用原入口固定尺度及检查预算。最大能量交叉2.61058e-16、潜热交叉1.96184e-18，均<5e-12；真实线性残差加gamma256全链最坏2.23432e-11<原1e-9，零梯度边界0 K。原生均值和独立求和终态相差约2.95e-18，明确区分舍入与原事件字节合同。
- 第21轮仍未收敛：epsilon最大增量0.07114668063610671>原1e-6，原生平均4.4470602557926683e-6；同态F_E最大固定缩放0.000350211945696793>联合草案2e-9，L1 0.1752520366620431 W；相变/温度缺陷0.004970677026148695>草案1e-8，投影互补0.007930382176868655；潜热滞后L1 0.17521236636206405 W。第21次G输入态T增量1.97522081556 K，不冒充其输出态完整RG（未调用22G）。末17/19/21完整after状态SHA相同，18/20另一个相同SHA，观察窗口两种状态交替；不宣称延长原G必收敛或外推所有258步。
- 同一个600秒绝对GNU timeout截止，原起点至最终停止241.73 s，含修复间隔；两进程GNU50.28/69.82 s，构建18.75 s、完整21G3.294 s、21次同态无求解组装合14.409 s。峰值进程858524 KiB（838.40 MiB），非并发树合计；rank1/thread1/CPU0。预估新数据未去重1.519 GiB，阶段后实际分配峰值0.832 GiB，末次逻辑1.574 GB/唯一370.80 MB/分配372.18 MB；412个仅本批新完成工件SHA校验硬链接，保留路径/字节，不链接旧数据。8 GiB/3 GiB MONITORED_ONLY警戒未触发，非内存/磁盘硬隔离。工具准备测量范围约233.12 s（目录创建至首执行，先前源码审查另计），报告/Git另计。
- 10228/10351保护SHA、116项来源和工具不变，冻结原M1输入/原版Git树/原生库来源通过；EXP-014至023负结果/原失败工件与公开记录原样保留。额度结束，只具备申请独立收敛参考设计资格，不执行独立延拓参考、传统加速比较或AI。压力初值NO_GO、MAG关闭、258步未收敛及M1物理/网格缺口继续公开。

## EXP-025 — 独立收敛参考数学与受控实验设计（无数值执行）

- 2026-10-18，DEC-029设计授权，基准6363172da045af48b7c533bbf64e7b17208bc214。唯一新研究交付：[T–相变独立参考设计](T_PHASE_REFERENCE_DESIGN_20261018.md)。REFERENCE_DESIGN_READY仅指可申请未来受控离线实验，不是已取得根或批准新标准。零CFD/G/残差评价/数值求解/矩阵组装/构建、零算法实现或AI，PR #5 Draft、不合并。
- 复用EXP-024的21轮/周期SHA与独立能量/相变证据，不重扫原场或大日志；明确观测窗口after切面的双状态重复，未做扰动/谱分析，不证明吸引周期、根不存在或全局唯一。内部同态F_E/R_phi根、原T/epsilon边界及冻结入口物性/旧层构成精确定义；calculated cp patch为0时只保留原边界更新，不向patch擅加内部Gamma温度约束。
- 两路线为受保护外层阻尼原G与内部Gamma消元后的全局化半光滑Newton，均为已有传统技术，不选择AI或声称创新。核对原生API/字段操作及PETSc官方手册、Hintermüller–Ito–Kunisch DOI与Benson–Munson作者稿；其收敛条件不自动适用于本问题。
- 旧F_E2e-9/相变1e-8不升级为真值门槛；联合合同必须在未来经制造根/负例、舍入/线性误差及场值敏感性校准，预注册后失败即拒绝、不调宽。唯一拟议实验为同C两路线×两种子，先校准后有界求根/交叉复核；600秒/52G/400R/510Jv/24Jacobian准备仅为待批预算。现有费用外推约300秒只覆盖部分组装/G，新增Jacobian/Krylov/核验成本未知，不保证完成或加速。
- 25项约325.5 kB定向源码/摘要前后SHA不变，报告嵌入关键来源及入口/几何已核验SHA；不冒称本轮重验10351原始内容。生产Git树/冻结输入不变，全部旧验证报告及日志历史保留。压力初值NO_GO、MAG关闭、258步未收敛及M1物理/网格缺口继续公开。本轮设计结束，未来参考实验/传统求解器/AI仍须另行明确批准。

## EXP-026 — 冻结738步独立参考可行性：未取得可验收根

- 2026-10-18，DEC-030新离线授权，实际唯一构建/执行HEAD=fcd1a0d7f886fab13aed4dad8b1baa9bfbd84c7e。报告：[独立参考可行性](../validation/T_PHASE_REFERENCE_FEASIBILITY_20261018.md)；[预注册](T_PHASE_REFERENCE_PREREG_20261018.json)在构建/数值前冻结，公共SHA e93782640fdbeeef25c1b8576247021e66125317aa420d53b32d8fedd63d09c0，本地含路径清单版SHA e10b27f735b4f639363fa8b030cc9d49fd1252a309e49dcbe138c89e36bd5d13。[校准](../validation/T_PHASE_REFERENCE_FEASIBILITY_20261018-calibration.csv)、[四分支](../validation/T_PHASE_REFERENCE_FEASIBILITY_20261018-branches.csv)、[所有试步](../validation/T_PHASE_REFERENCE_FEASIBILITY_20261018-trials.csv)、[残差](../validation/T_PHASE_REFERENCE_FEASIBILITY_20261018-residuals.csv)、[费用](../validation/T_PHASE_REFERENCE_FEASIBILITY_20261018-costs.csv)、[来源/资源](../validation/T_PHASE_REFERENCE_FEASIBILITY_20261018-summary.json)全部脱敏。PR #5 Draft、不合并。
- BUILD/完整C字节重载/CALIBRATION/PROVENANCE均PASS；唯一构建19.236 s。校准R24请求/Jv6，复用原冷固/糊状/全液独立制造源，最大能量交叉2.02e-16、单侧Jv相对误差2.96e-9；温度/相变/patch/Euler旧层负例检出，重载一致。一个非法patch请求在原生组装前拒绝但计R；历史非零线性工件只读复核，无新校准G。原始oneG/组装/binary64恢复数值体不变。
- 四分支未取得合格根：A入口G7/R12、接受6步后五个阻尼全部拒绝；最后接受态F_E最大4.03690e-4、相变/温度缺陷0.0280281。A原21轮终态G2/R8，接受一次1/4阻尼后下一方向五步全拒；F_E最大1.75106e-4、相变/温度0.00291017。按预注册分类CYCLING_OR_STAGNATION，具体是线搜索拒绝，不宣称观察到新周期。该种子1/2试探虽使能量达5.97863e-15，仍有相变缺陷0.0107910，正确拒绝，不能用单一能量小认证根。
- B两初值各R1/准备1，完整非正交导数组合的保守逆敏感性充分界最小裕量−6.33779455e-4/−6.33778944e-4 W/K，未认证即停止；真实C的辅助Krylov/Newton更新/终点G均NOT_RUN。负裕量不证明Jacobian奇异/病态、Newton失败或根不存在；不换认证方法绕过原规则。四路根差/终点干净复核NOT_RUN，整体INCONCLUSIVE，REFERENCE未通过。
- 全批G9/R46/Jv6/准备2，45次原生R组装；其中求根G9/R22/准备2、无求根Jv。原生G真实线性加舍入最坏7.77990e-10<1e-9，全部已执行R能量交叉最坏2.73e-16。s固定为EXP-024入口，S_T=3710.4316126698473 K，P_ref=1224.53399598741 W；内部/patch/全场、绝对/有符号能量全部保留，未降低标准或把原21轮当真值。
- 统一600 s timeout下GNU主动57.27 s（控制器57.107 s）、CPU user52.92/system4.30 s；峰值子进程860808 KiB=840.63 MiB，阶段末观测分配峰值457105408 B≈0.426 GiB，无观察警戒触发。rank1/thread1/CPU0，RSS8 GiB/数据3 GiB MONITORED_ONLY而非硬隔离。新工具准备观测窗口616.59 s（更早源码阅读不含），报告/Git另计且未精确计时；原始源码、候选/矩阵/日志全部本地保留。2543保护项/14工具SHA前后不变，另批后SHA审计25个真实输入与EXP-024预期相同，不冒充本批前后重验全部三基线。
- 零新S/M1/CFD/Time推进/AI/生产修改，无构建重试/续跑/放宽阈值；额度结束。暂停将此C用于固定点加速比较，缺口为可信根及真实C条件认证，而不是已证明无根或所有传统方法无效。后续只提出另批只读数学审查认证是否过度保守，不自动求解。压力NO_GO、MAG NO_BENEFIT、258步非线性未收敛和物理/网格缺口保留。

## EXP-027 — Newton充分界与联合Merit只读数学审查

- 2026-10-19，DEC-031，起点8a8ff4b4286f3a4b109d4a755c4a8d26e75d281d；唯一研究交付为[条件认证与Merit审查](T_PHASE_CERTIFICATE_MERIT_REVIEW_20261019.md)。零CFD/G/R/Jv/求解/组装/构建/算法实现或AI，无新原场指标或数值实验；不改EXP-026及历史失败，PR #5 Draft、不合并。
- CURRENT_CERTIFICATE_CORRECT仅指点态Jacobian充分逆界；逐项核对Euler旧层、潜热、Sp对流、完整非正交扩散和源项导数的符号/单位。符号两单元例证明把整个正交扩散作为扰动会失去有利对角；非正交组合绝对上界和对流抵消亦可能损失。实际最坏行分项/谱/条件数未知，不从保存的两个负裕量虚构排序，亦不归咎未执行的预条件GMRES。
- 发现完整非线性误差认证尚不充分：点态逆界不能替代根存在/邻域包络；A的F_E(T,e)与H(T)差须计入潜热相变项。原endpoint未执行，此意见不追写成上轮失败或推翻其校准/INCONCLUSIVE记录。原五试步均Phi增大，不能说下降系数过严；原G方向尚未证下降，五点拒绝不证明新周期/极限停滞。
- 核实Varah DOI 10.1016/0024-3795(75)90112-3、Dembo等10.1137/0719025、Rump 10.1017/S096249291000005X及作者原文；区分真实线性残差、局部条件估计与经验证非线性后验包络。建议RESEARCH_CONTINUE限于另批最小线性方向认证（G0/R24/Jv48/准备2/120 s提案），不是现在批准求根、加速或AI。20项定向证据/源码SHA不变，4项治理/入口仅追加记录或更新状态，不重扫原场/大日志。原258步及全部科学缺口保留。

## EXP-028 — 有限Newton方向：入口认证、终态独立RHS检查未通过

- 2026-10-19，DEC-032新批次，实际执行HEAD=f3aef9b8b886e3c0ba65a1103ede4cd9a38c9a0f。[报告](../validation/T_PHASE_NEWTON_DIRECTION_20261019.md)、[预注册](T_PHASE_DIRECTION_PREREG_20261019.json)、[校准](../validation/T_PHASE_NEWTON_DIRECTION_20261019-calibration.csv)、[方向](../validation/T_PHASE_NEWTON_DIRECTION_20261019-directions.csv)、[步长诊断](../validation/T_PHASE_NEWTON_DIRECTION_20261019-diagnostics.csv)、[Jv费用](../validation/T_PHASE_NEWTON_DIRECTION_20261019-jv-costs.csv)、[原生费用](../validation/T_PHASE_NEWTON_DIRECTION_20261019-calls.csv)、[哈希/资源](../validation/T_PHASE_NEWTON_DIRECTION_20261019-summary.json)均脱敏。公共预注册SHA d73ac2ce1302ce4968ee7fbffbe42820eb3e073708d1a1e3e4605d2e9ab01fe6，本地清单版7cf4556f3e41a82f2b4463c2d3c4bfab25803f78b8a42ebfa3a3763ca3fd63e1。零新CFD/G/Time推进/原生构建/AI，零接受的T/epsilon更新；PR #5 Draft、不合并。
- CALIBRATION/PROVENANCE PASS，入口方向CERTIFIED，终态方向INCONCLUSIVE，独立联合TRUE_LINEAR_RESIDUAL FAIL（单独原生固定RHS两次均PASS），Merit诊断入口PASS/终态NOT_RUN。六制造/阈侧方向各两单侧步长通过，原生FD相对误差最大1.70e-8；完整C重载字节差0，1211保护项/7新源码SHA不变。原二进制f0571540...、Jv/GMRES及原guard保持，按新独立方法不以旧负裕量预拒方向。
- 两种子均6次辅助GMRES+1次独立直接Jv；原生固定RHS真实L1加gamma256为入口3.01258e-12、终态2.52826e-12，均<1e-9。原预注册另要求独立逐面H、同一原生RHS尺度的交叉验收：入口3.53427e-12通过，终态2.21598e-9失败。原生/逐面终态H差L1=5.28894e-10 W，超过固定RHS对应2.38759e-10 W；不能拿原逐单元尺度交叉2.25850e-16或较大入口RHS范数替代该门槛。与相消/舍入放大相容，未做高精度归因，不证明Jacobian错误、根不存在或GMRES无效。
- 入口方向最大28.9329912430 K；归一化方向1e-4/5e-5 K诊断无跨clip，Phi差分斜率−4.84341851e-10/−4.84342269e-10每K，与解析−4.84342688e-10相符；两条原生/逐面差分及边界/patch检查通过。采样不接受为状态，能量仍约5.1286e-3，非根。终态方向最大1.18003308650 K，严格独立门槛失败后不再做步长诊断，不重算/调参或用余额追加工作。
- 计费G0/R22/Jv20/准备2：校准18R/6Jv，入口3R/7Jv/准备1，终态1R/7Jv/准备1。统一120 s timeout下GNU7.07 s（控制器6.895 s）、CPU6.31/0.72 s；峰值RSS96768 KiB=94.50 MiB，阶段末分配峰值33013760 B≈31.48 MiB。rank1/thread1/CPU0，1 GiB/200 MiB MONITORED_ONLY未触警，非硬隔离。工具准备观测窗口174.83 s，更早审查/报告/Git另计且未独立精确计时。原始方向/矩阵/日志/源码本地保留，无清理或旧数据修改。
- 整体INCONCLUSIVE，有一个线性方向认证，非两方向共同通过或非线性参考。仅可申请独立根存在/后验误差认证设计，须首先解决终态固定尺度下独立RHS算术一致性；不自动求根/推进/AI。两方向均失败的暂停前提未成立，但本额度已结束。保留压力NO_GO、MAG关闭、原258步及物理/网格缺口、所有失败历史。
