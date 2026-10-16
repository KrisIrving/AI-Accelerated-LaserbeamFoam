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
