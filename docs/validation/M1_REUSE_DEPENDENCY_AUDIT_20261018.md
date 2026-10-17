# 固定M1重复计算与数据依赖审计

2026-10-18；DEC-015 / EXP-011；起点`de4c959457b3bceb1a6b5af8bda88aa43b8f551c`。**ONE_CONDITIONAL_CANDIDATE_PROPOSED**：仅建议测试“单次TEqn内复用原生mag(gradAlpha)”；数值等价与收益尚未验证。零新增CFD、不实现优化、不改原版/热校正次数/容差、不开发AI。复用[已通过的内部计时](M1_TP_INTERNAL_TIMING_20261018.md)，不重读大日志。

## 简短依赖表

“不变量”只针对指定局部调用范围及冻结M1，不能跨物理步、外层校正或推广到任意边界/模型。

| 范围/量 | 结论 | 复用条件及失效点 |
| --- | --- | --- |
| T：alpha、gradAlpha、几何 | 单次TEqn内有条件不变 | VOF/mesh更新在前，UEqn生成gradAlpha并修正其边界；T不写它。每次TEqn重新建立缓存；任何alpha/梯度/几何/边界写入或外部回调使证明失效 |
| T：cp/kappa/LatentHeat；rhoCp/rhophicp/em | 当前算法内冻结，部分已移到循环外 | updateProps先于T；rhoCp/rhophicp/em本来就位于do-while外，不宣称已有提取是新收益。em随入口epsilon确定后保持滞后，不能擅自每轮更新来“改善物理” |
| T：T、epsilon1、prevIter、TRHS | 随热校正变化 | solve、相变校正和storePrevIter改变下一轮输入，不能缓存跨轮结果 |
| T：Qrad、Qv、thermalDamper、gradAlphaDamper | 随T等变化 | 辐射T³/T⁴、蒸发exp/pow(T)、阻尼polycp(T)；即使gradAlpha固定，整个阻尼乘积也不固定 |
| T：完整矩阵/预条件器 | 不能证明可复用，当前否决 | 辐射对角项、源项、边界/relax/solve状态变化；cp/kappa固定不代表完整矩阵及RHS固定 |
| p三校正：alpha/rho/热状态/几何 | 固定M1内有条件不变 | 热/VOF阶段在前，p不重算这些物性；新外层/物理步、模型或边界回调必须失效 |
| p：A/rAU/rAUf、固定力源片段 | 结构上可能不变，但本轮不选 | A读取D()/V且调用边界修正；插值/约束、rAU.clear与临时量生命周期仍需证明，不能由“只组装一次UEqn”直接判定安全 |
| p：UEqn.H、HbyA、phiHbyA | 不能整体复用 | 原生H显式读取当前psi(U)及边界源；p每轮更新U/phi，预测量还有ddtCorr、constrainHbyA、adjustPhi依赖 |
| p：压力矩阵/RHS/参考/求解状态 | 整体复用未证明 | 即使部分Laplacian系数不变，预测通量RHS、压力边界约束/参考与当前求解状态仍须更新 |
| p：p_rghEqn.flux、phi、U、p、连续性 | 随校正变化，必须保留 | 新压力解和更新通量/速度影响后续校正及诊断，不能跳过投影或守恒更新 |

依据为原版[主程序](../../applications/solvers/laserbeamFoam/laserbeamFoam.C)、[UEqn](../../applications/solvers/laserbeamFoam/UEqn.H)、[TEqn](../../applications/solvers/laserbeamFoam/TEqn.H)、[pEqn](../../applications/solvers/laserbeamFoam/pEqn.H)、[updateProps](../../applications/solvers/laserbeamFoam/updateProps.H)及[updateKappaCp](../../applications/solvers/laserbeamFoam/updateKappaCp.H)。还核对本机v2512 `fvMatrix.C` 的A/H、GeometricField mag/临时量/边界操作源码及冻结配置。M1的T边界为zeroGradient，未配置coded/function回调或temporary缓存；这不是对任意OpenFOAM案例的证明。

## 唯一候选与证据等级

**候选：T_LOCAL_NATIVE_MAG_GRADALPHA。** 在原来第一次求mag的位置计算完整原生体场及patch结果，存为拥有存储的只读局部值，仅在同一次TEqn的后续热校正复用；退出TEqn即销毁。保留每次thermalDamper计算、原输入顺序的乘法、gradAlphaDamper构造、所有源项/边界/残差/热校正。缓存不是gradAlphaDamper，也不跨时间步复用；本轮不写优化代码或补丁。

选择理由是依赖范围窄：gradAlpha由UEqn在T之前赋值及修正边界，TEqn只有一次mag读取，循环不改变其输入。v2512原生mag计算内部场、patch和orientation并执行局部边界操作，因此不能只缓存内部数组或手写新的sqrt公式。

**必须处理的临时量风险：** 原生tmp乘法可能复用并重写mag临时存储。把可复用tmp直接当“共享缓存”可能缓存成被thermalDamper乘过的结果，后续反复乘错。候选必须保存独立、只读、不会被消费的完整结果；不注册/写出新增场，核对temporary缓存与边界副作用。原乘法仍会分配/处理结果，不能把此方案说成消除了所有分配。若这些生命周期/边界条件无法证明，则禁用或否决候选，不扩大重构。

| 证据 | 等级 | 边界 |
| --- | --- | --- |
| T_OTHER30.805863 s/15.0265%；晚期重复集中 | 已有真实观测EXP-010 | 是包围阶段，包含源项、控制/析构等，不是mag成本 |
| gradAlpha在单次T调用内不写、原生mag读完整场；H读取当前U | 有条件静态源码证据 | 依赖固定源码/配置及无外部写入；不是运行等价证书 |
| 缓存命中正确性、字节等价、净收益 | **UNVERIFIED** | 没实现、没编译优化版、没运行新CFD |

按既有热循环次数推导，T内原生mag表达式执行7244次；候选预计1000次首次计算、6244次复用，减少86.195%的**表达式求值次数**，不是减少86.195%的T_OTHER时间。前2 μs每步仅一次T校正，零复用机会；后3 μs预计减少5298次，占全部减少次数84.85%。这是源码次数推导，不是新增mag计时或调用探针。

本候选的耗时份额g和维护开销均未测。只能给极松包围界：0≤g≤T_OTHER的15.0265%；把整个T_OTHER归零的1.17684×是包围上限，**不是候选可加速份额或收益预测**。实际乘法/分配/源项仍存在，禁止把30.806 s或后期T_OTHER23.144 s全部算为可节省时间。缓存标量值载荷按32000单元+6400外边界面估计约307200字节（0.293 MiB），另有对象/patch开销，不是实测RSS。

这是值得一次低成本可证伪测试的工程候选，尚不足以成为AI研究方向。更大矩阵/预测量复用均未进入本次测试候选。

## 唯一下一次最小实验：PROPOSED，未批准、未运行

**一个协议：非CFD缓存/场运算预检→一次S启用门槛→同一隔离二进制顺序一次M1 OFF、一次新M1 ON。** 原版源/二进制/冻结输入/旧结果只读；只在未来经批准的独立副本实现此唯一缓存，默认关闭，OFF保留原表达式路径。不得改变热校正次数、容差或支持范围，不自动重试/续算。

1. 非CFD预检先覆盖非均匀内部/patch、不同thermalDamper以及重复使用：原生结果逐元素字节一致，缓存前后不被乘法改写，无注册/写出副作用；不支持的模型/边界/temporary缓存设置直接拒绝。S原生每步仅一次热校正，**不能单独覆盖缓存命中**，所以不能省去命中/临时量测试；随后S需19场/3 uniform及原检查一致。
2. OFF和ON均采用冻结32000单元/1000步/原输出。各自190场/10时刻/30 uniform对三原版及彼此字节一致，复用原完整检查、输入/初态/源码/二进制/动态库SHA守卫。T/p/epsilon1完整事件及258个未满足相变残差的步/位置也必须一致；ON计算/命中次数应为1000/6244，不逐循环打印。任何不一致停止，不用容差掩盖差异。
3. 两模式采用相同观察布局，保留既有父子/10箱闭合；只为完整gradAlphaDamper构造及缓存管理增加一个互斥累加测量区间。不要只计省下的sqrt而漏掉保存、查找、复制、分配/边界工作；缓存最终析构等未包入该区间的费用仍计T_OTHER与完整solver。累计数据只在退出导出；若观察改动破坏tmp生命周期或无法解释费用，不发布收益。
4. 报告OFF/ON完整solver及案例墙钟、RSS/数据、目标区间及T_OTHER的净差和分箱差，另对205.96 s及原CV0.3866%参照。不把单次配对当统计显著性证明。提议以**完整solver快>2%且目标净差方向一致**作为是否继续投入的保守筛选，未达或方向不一致记无收益/INCONCLUSIVE，不自动追加重复实验。2%是待批准的研究筛选，不是改变数值验收或已批准收益承诺；即使通过，稳定收益仍未由一对运行证明。

配对OFF/ON是为了隔离新编译布局/计时框架与缓存本身的区别；既有三原版继续作数值和历史性能参考。不以新片段占比预测全阶段收益；未来仅用实测g、局部加速和全部维护成本计算Amdahl，片段不能消除的乘法/边界/管理费用保留。

预算提案：rank1/thread1/CPU0，S120 s、每M11800 s求解上限，整次主动构建→两例最终检查1200 s截止（剩余总预算优先），RSS8 GiB/新数据3 GiB MONITORED_ONLY。按既有成本预计约11–13分钟而非保证；批次超时/警戒或任一检查失败立即停止后续，不缩短物理配置。Ubuntu独立进程负责超时、退出与日志，结束后集中检查，不高频轮询。只有负责人后续明确批准才实施该协议，本轮不启动。

258步相变非线性未收敛风险继续保留：即使未来OFF/ON完全一致，也只是保留原版数值轨迹，不能当已收敛物理真值、训练真值或AI准确性依据。本提案不修复或加速热校正退出策略。

## 来源与保护

26项消费源码/配置/既有计时摘要和CSV读取前后SHA一致；没有读取大日志或重做CFD统计。原版src/applications/tutorials/benchmarks/scripts/profiling没有改动。小型[证据JSON](M1_REUSE_DEPENDENCY_AUDIT_20261018.json)含逻辑源码路径/完整SHA、分类、唯一候选及协议，原始本机路径不公开。源与本机OpenFOAM版本是证据范围，数据依赖结论不泛化到其他版本/模型。

DEC-015与EXP-011为本轮追加记录，旧决定/结果保留；PR #4保持Draft、不合并。阶段2仍为性能研究，AI未启动。
