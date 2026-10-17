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
