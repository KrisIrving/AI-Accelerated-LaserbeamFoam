# T–相变固定点：数学、回放与文献前置审查

2026-10-18；DEC-022 / EXP-018。原版基准main `a8861ea9c0d4514f10606da5d3fb9568b4c86f92`；证据起点PR #5 `9f658caaf3170b29c9bf82fc26f0d0424c29cccf`，消费原版源与main一致。仅源码/数学/原文研究；零CFD、构建、回放、训练及算法实现，未改原版、输入或标准。结论 **NOT_READY**：可定义有条件封闭的内层问题，但完整状态回放及独立数值参考尚未验收；不选择AI方法，不改变压力初值NO_GO。

## 1. 原始映射与源码对应

令n为当前物理时间步，k为**同一次TEqn调用**的热校正，e为TEqn入口。令`l=epsilon1`、`c=rhoCp`、`h=rhophicp`、`L=LatentHeat`、`a(T)=mag(gradAlpha)*thermalDamper(T)`。固定上下文C包含下表时间层、入口字段、网格、材料与边界/求解配置。`D_t`、`D_f`、`L_kappa`均指原生有限体积算子，不能换成连续导数后当作已定义的离散系统。

| 源码位置（原版laserbeamFoam） | 严格语义/映射组成 |
| --- | --- |
| [主程序](../../applications/solvers/laserbeamFoam/laserbeamFoam.C) 142–183；[updateProps](../../applications/solvers/laserbeamFoam/updateProps.H)；[updateKappaCp](../../applications/solvers/laserbeamFoam/updateKappaCp.H) | VOF→物性→激光沉积→UEqn/MTHD→TEqn→压力校正。cp/kappa按入口T/alpha更新后在热循环内滞后；L用alpha_filtered混合，在updateProps更新，不在热循环更新 |
| [TEqn](../../applications/solvers/laserbeamFoam/TEqn.H) 8–15 | 初始化TRHS，`c=rho*cp`及c边界，`h=interpolate(cp)*rhoPhi`，`em_e=l_e*emL+(1-l_e)*emS`；em_e不随k更新 |
| TEqn 26–38 | 先复制当前完整T/l到prevIter；`Q_L(l^k)=L*[D_t(rho,l^k)+D_f(rhoPhi,l^k)]`；按原顺序赋值TRHS并修正边界；计算Qv(T^k)及其边界 |
| TEqn 40–61 | `q_ex(T)=SB*em_e*(TRef^4+3*T^4)`；`q_in(T)=-4*SB*em_e*T^3`。damperSwitch=true时内部`d(T)=2*c/[rho1*polycp_m(T)+rho2*polycp_g(T)]`再更新zeroGradient边界；false时保持已有d（本配置初值1），不得擅自重置 |
| TEqn 62–83 | Joulesource为已完成MTHD求解的只读字段或零场；沉积已在外部更新。组装下式，TEqn.relax，再用当前T作初值调用原生smoothSolver/symGaussSeidel |
| TEqn 85–103 | solve内部也修正T边界，随后原代码再次修正；`Tcorr=Ts+(Tl-Ts)*l^k`及其边界；完整场clip更新l，再修正l边界。Tcorr用**更新前**l |
| TEqn 105–133；[readControls](../../applications/solvers/laserbeamFoam/readControls.H) | 仅内部l增量的max与体积加权mean入日志，mean不参与停止；末尾gradT不反馈本次热循环。min=1/max=20、epsilonTol=1e-6、epsilonRel=0.9；循环尾组合可执行21次，次数耗尽不是收敛 |

每次k的未松弛线性方程为（省略C下标）：

```text
[D_t(c,·) + D_f(h,·) - Sp(D_t(c)+D_f(h),·)
 - L_kappa(·) - Sp(q_in(T^k)*a(T^k),·)] T_hat
 = Qlaser + QJ + [q_ex(T^k)-Qv(T^k)]*a(T^k) - Q_L(l^k).

Qv(T) = 0.82*Lv*Mm*p0*exp[Lv*Mm*(T-Tvap)/(R*T*Tvap)]
        /sqrt(2*pi*Mm*R*T).
T_next = B_T(Solve_native(Relax(A_k,b_k;T^k), initial=T^k)).
Tcorr_k = B_corr(Ts+(Tl-Ts)*l^k).
l_next = B_l(clip(l^k + beta*(T_next-Tcorr_k),0,1)), beta=0.9*cp/L.
G_native,C(T^k,l^k) = (T_next,l_next).
```

上式是操作顺序定义，不是浮点重排实现。B表示各自真实patch操作；不能把所有B替换成内部值外推。冻结配置为Euler、T对流Gauss upwind、潜热对流Gauss linear、扩散Gauss linear corrected。非正交修正可读取当前T梯度，必须保留，即使原生规则网格上该贡献可能很小。`fvMatrix::relax(1)`仍执行对角占优修正及`source+=(D-D0)*T^k`，不能因因子为1就宣称恒等。辐射用了局部切线，其他项滞后；原迭代是分裂固定点/部分线性化，并非全部源项显式冻结的纯Picard。

**时间与状态分层：** Euler热方程读取`c^n,T^n,c^(n-1),T^(n-1)`；潜热读取`rho^n,l^n,rho^(n-1),l^(n-1)`；连续性修正还读c旧值。静态M1只需一个旧时间层，不是上一热校正。cp/kappa/L/rho/rhoPhi/h/c、Ts/Tl、gradAlpha、em_e、沉积/Joule及材料常数属C；T/l及其patch值属k状态。prevIter在每轮入口覆盖，因此在规范“一轮入口→下一轮入口”切面上不是独立未知量；若在solve后/相变更新前暂停，则必须另存prevIter和执行位置。iter只控制整段退出，不改变该单次G；要复现完整调用仍须保存iter及min/max/退出原因。

**封闭性结论：** 不带C的两个场不能定义跨时间步的统一自治映射：相同当前T/l配不同旧T会改变ddt源，配不同入口em_e也会改变辐射。固定C后，取z为**完整体场T/l（内部+patch）**，逐项读依赖均为z/C或当轮派生量，故可条件定义`G_C`；本机原生solve每次创建线性solver，prevIter覆盖，不需要额外的历史加速向量。仅取两个内部数组不够：保存的l patch实际为`calculated`，值由场运算赋予，不保证等于当前内部值的外推；T为zeroGradient，其evaluate会外推并重置patch更新标记。若允许动态网格、外部/自定义有状态边界或回调，最小扩展必须再含相应模型/registry/几何历史状态，否则拒绝宣称封闭。本结论限冻结串行M1已审查路径，不泛化到任意OpenFOAM配置。

另区分精确线性求解的理想`G_*`与有限精度/有限线性容差的`G_native`。后者的停止分支随初值变化，不能默认光滑；smoothSolver默认归一化N依赖当前线性初值，实际tol=1e-9/relTol=0仍不等于固定绝对能量误差。工作域须T>0、cp/L有限且正、矩阵求解有效；全域可解性、固定点存在/唯一性、压缩性及非扩张性均**未证明**。

## 2. 独立收敛与能量验收草案

活动集由`w=l+beta*(T-Ts-(Tl-Ts)*l)`决定：w≤0为下饱和，0<w<1为内部，w≥1为上饱和；阈点不可微。若beta>0、Tl>Ts，固定点相变条件等价于：l=0时T≤Ts；0<l<1时T=Ts+(Tl-Ts)l；l=1时T≥Tl。因此全固/全液单元不应强求T=Tcorr。clip本身非扩张不推出完整G非扩张。

以下均以同一个候选终态z重新评价；不能拿用l^k组装的矩阵在T^(k+1)上的小残差，认证更新l后的耦合状态。

| 指标 | 独立定义与验收草案 | 仅既有日志能否完成 |
| --- | --- | --- |
| 原增量 | `r_inc=max_internal|l^(k+1)-l^k|`，保留原≤1e-6标准；原生链上只是G的l分量，冷固态clip可使其为零而T仍变化 | 可复用既有解析摘要；258步失败已确认。日志打印的有限精度值不替代临界值原数组 |
| 真正固定点残差 | 从候选z的干净副本再做一次G_native，`R_G=G_native,C(z)-z`，同时报告T/l及patch分量；不可用AA/Aitken自身步长代替它。T按预先固定温度尺度S_T无量纲化 | 不可；缺完整当轮状态。一次额外G有真实费用 |
| 相变/温度一致性 | `R_phi=l-clip(l+beta*(T-Ts-(Tl-Ts)*l),0,1)`；另算`R_cons=l-clip((T-Ts)/(Tl-Ts),0,1)`。后者避免小beta把温度不一致隐藏在小增量里；Ts=Tl须另立等温互补式，当前M1不属此例 | 不可；输出时刻可定向查R_cons，不能代表未保存热校正或完整收敛 |
| 离散能量缺陷 | 重建**未松弛、所有项同态**的F_E（下式），显式计边界、旧层、潜热与非正交修正。原生组装结果与独立逐面/Euler记账交叉核对 | 不可；线性日志残差仅针对当轮已线性化、已松弛系统 |
| 潜热滞后缺陷 | `delta_Q_L=Q_L(l_next)-Q_L(l)`，另报告空间L1/max及有符号积分；它不是能量残差的替代项 | 不可；缺rhoPhi、旧层及连续迭代l |
| 约束/失败 | 内部及patch有限、T>0、0≤l≤1，材料正性，原patch赋值/零梯度及其通量一致；任一原线性门槛失败、非有限、迭代/资源上限耗尽且联合标准未过，记REFERENCE_FAILED并停止 | 日志可否决部分异常/上限；不能证明全部场/边界及能量合格 |

同态有限体积能量残差（单位体积功率）定义为：

```text
F_E(T,l) = D_t(c,T)+D_f(h,T)-[D_t(c)+D_f(h)]*T-L_kappa(T)
           +L*[D_t(rho,l)+D_f(rhoPhi,l)]-Qlaser-QJ
           -a(T)*[SB*em_e*(TRef^4-T^4)-Qv(T)].
```

精确算术下，重新组装的辐射切线在同一T代入可合并为TRef^4−T^4；逐位核验仍保留原乘加顺序，独立重排计算须报告舍入界而不能暗改容差；矩阵relax修正只在固定点上抵消，不能混入物理离散缺陷。**全局守恒不只看相消积分**：同时报告`max|F_E,i|/s_i`、`sum(V_i*|F_E,i|)/sum(V_i*s_i)`与`|sum(V_i*F_E,i)|/sum(V_i*s_i)`；s_i由C和预先固定的温度/热源尺度确定，不能用候选自身放大归一化。额外线性核验亦保留原初值尺度，不重复压力研究中的归一化漏洞。

必须保留原式的非保守修正`-[D_t(c)+D_f(h)]T`及L在导数/散度**外**的次序。空间变化的L和时间变化的cp下，不能擅自把它简化为`d(rho*(cp*T+L*l))/dt`并据此声称物理总能量守恒；须单列对应交换/滞后项和边界通量。通过F_E只认证冻结内层离散问题，不认证外层物性全隐式耦合、时间/网格收敛或实验预测。

联合验收设计：保留原r_inc≤1e-6及线性tol1e-9/relTol0，并增加R_G的T分量、R_phi/R_cons、局部/全局F_E、潜热与边界检查；全部通过才可称内层数值参考。新增`tau_T/tau_cons/tau_E/tau_budget`尚**未赋值/批准**：先用独立制造解与线性/舍入底校准，再按误差预算预注册，不能观察失败后放宽。没有压缩常数/逆Jacobian界，小残差也不是严格前向解误差界。参考拟要求从原生入口与另一可行初值重复收敛至相同容许解，并接受独立F检验；这仍不是唯一性证明。额外迭代只可能属于将来另批的离线参考，不改生产max=20/原258步记录，更不能把上限结果当标签。

## 3. 完整回放状态缺口

| 最小独立状态/上下文 | 必需内容与快照切面 | 现有证据 |
| --- | --- | --- |
| 迭代未知量z | T/l内部、每patch类型/值/字典/布局；TEqn入口及每次G入口/出口；若分段暂停，增加prevIter、iter与执行位置 | 仅每100物理步的10组终态，缺热校正快照；l为calculated patch |
| Euler旧时间层 | T_old、l_old、rho_old、c_old完整场；当前rho/c、dt、物理timeIndex及各字段存储时间标记 | 输出间隔100步，不能当n−1；rhoCp等NO_WRITE。不能通过重启再算物性来冒充内存旧层 |
| 入口冻结量 | cp/kappa/L、rho/c/h/rhoPhi、Ts/Tl、gradAlpha、em_e、沉积/Joule、材料多项式和常数；damper=false还存d | 有若干输出/材料字典，但cp/kappa/L/em/c/h等多数NO_WRITE；em_e不能从最后l倒推 |
| 几何/边界上下文 | 原生owner/neighbour/patch拓扑，V、Sf及插值/非正交系数；所有参与场的patch状态与更新标记重置规则；静态/非耦合支持声明 | 原网格存在，不足以补全当轮字段/BC内存状态；不能把epsilon改成zeroGradient |
| 规则与模型 | 完整fvSchemes/fvSolution、relax及T/TFinal选择、PIMPLE final标志、MELTING、材料/模型开关；不支持有状态回调即拒绝 | 冻结字典有SHA，可复用；模型/运行选择须随新快照自证，不能仅凭版本号 |
| 派生审计记录（不是新增独立未知量） | TRHS/Qv/q_ex/q_in/d/a/Tcorr；未松弛矩阵/RHS、relax后矩阵/RHS、实际边界diag/source贡献、线性原初值/终解/原N与停止元数据；l更新前/后 | 30套已存系统是p_rgh，不能用来回放T；无热矩阵/源项链 |

数学最小量按依赖闭包理解，不是要求重复编码每个派生数组：当前c/h若能由rho/cp/rhoPhi及原生边界操作逐位重建，可只存独立输入；T的zeroGradient patch在一致入口可由内部值重建，而calculated的l patch须保留。表中冗余c/h、源项和矩阵用于独立逐位核验，不充当额外非线性未知量。

**现有保存场不足以回放。** 最小未来真实采集能力应只支持固定M1的一个TEqn调用（可预定首个失败步738），保存入口C一次、该步每次G的前后z/派生审计，最终l前后与原21次事件；旧层在第一次G前冻结，不在回放时让lazy oldTime错误滚动。矩阵记录用于交叉验证，不能仅靠一个已组装矩阵声称重建了非线性映射。此为状态接口设计，**本轮不实现、不采集，也未授权新M1**；单步不能验证时间推进误差或覆盖全部258步。

溯源应含主仓库提交/原版Git树、隔离观察源码投影、工具/二进制/动态库SHA、WM_OPTIONS/标量与label宽度、输入/网格、每字段旧/当前/patch与每矩阵文件SHA、维度/顺序/架构、事件和前后保护清单。原始内容留本机，公开只留脱敏汇总/内容SHA。G重放先逐字节复现当次原生输出及日志，再讨论独立参考；恢复后旧层或patch不同即失败，不以宽容差掩盖。

## 4. 传统算法、原文证据与创新边界

以下DOI和结论均核对出版方/作者原文，访问日期2026-10-18；不使用二手自动摘要作方法证据。可访问范围如实列出：Walker–Ni作者PDF全文；Zhang等作者预印本全文及出版方摘要/最终PDF可检索段；Tóth–Kelley出版方摘要（未取得全文）；Kang出版方摘要/引言及节选（§2具体迭代公式、完整§4表格未取得）。因此不声称已逐式复现后两篇。成本/失效列中对本问题的判断是本轮推论，不是文献在M1上的测量。

| 方法/原文与DOI | 原文支持的假设/范围 | 本问题额外成本、失效与对照条件 |
| --- | --- | --- |
| 原生分裂校正/阻尼；Voller & Prakash 1987，[10.1016/0017-9310(87)90317-6](https://doi.org/10.1016/0017-9310(87)90317-6)，[作者机构条目](https://experts.umn.edu/en/publications/a-fixed-grid-numerical-modelling-methodology-for-convection-diffu/) | 固定网格对流扩散/糊状区相变；与本代码对应关系由源码重建，不宣称直接逐式继承 | 原生G中已有epsilonRel=0.9；矩阵relax与相变阻尼不是同一操作。传统延拓至联合残差是首个参考对照；clip可能掩盖未收敛温度 |
| Aitken动态松弛；Küttler & Wall 2008，[10.1007/s00466-008-0255-5](https://doi.org/10.1007/s00466-008-0255-5)，[作者机构摘要](https://portal.fis.tum.de/en/publications/fixed-point-fluid-structure-interaction-solvers-with-dynamic-rela/) | 摘要直接讨论Aitken Δ²及最速下降的FSI固定点动态松弛；不是本热问题收敛定理 | 对无量纲全z残差r=G(z)−z，用向量Δ²更新一个外层权重；O(N)向量/内积及历史，分母小/噪声、负或过大权重需预定保护。不能暗调原epsilonRel来替代此对照 |
| Walker & Ni 2011，[10.1137/10078356X](https://doi.org/10.1137/10078356X)，[作者全文](https://users.wpi.edu/~walker/Papers/Walker-Ni%2CSINUM%2CV49%2C1715-1735.pdf) §1 Algorithm AA、§2、§4 | 残差历史约束最小二乘；特定线性条件下无截断AA与GMRES关联，讨论病态与实现；不是任意非线性全局保证 | m条历史O(Nm)存储/向量工作，小最小二乘/QR；病态、系数大、非物理混合、活动集变化及inexact G误差。温度/l须固定尺度；候选验证/拒绝额外G不能免费 |
| Tóth & Kelley 2015，[10.1137/130919398](https://epubs.siam.org/doi/10.1137/130919398)，原摘要 | 压缩映射及组合系数有界下局部r线性结果；摘要另述AA(1)/线性情形q线性；不是“必加速”定理 | 这里完整G压缩性/光滑性未证；clip与线性停止分支使直接套用不成立。有限历史和系数保护是已有技术，不能冒充创新 |
| Zhang/O'Donoghue/Boyd 2020，[10.1137/18M1232772](https://epubs.siam.org/doi/10.1137/18M1232772)，[作者最终PDF](https://web.stanford.edu/~boyd/papers/pdf/scs_2.0_v_global.pdf)，[预印本](https://arxiv.org/abs/1808.03971) Algorithm 3及全局证明 | 非扩张固定点且存在解；Powell型正则、独立性重启及保护，与averaged基础步交替；最终版扩展需相应闭性/准非扩张条件 | 重启、正则及回退并非新想法；本G未证非扩张，原生Picard也未证可靠回退。历史向量、保护检测及被拒绝G仍收费，不能仅“加保护”就继承定理 |
| Newton/半光滑Newton；Ulbrich，[10.1137/S1052623400371569](https://epubs.siam.org/doi/10.1137/S1052623400371569)，[作者技术报告](https://repository.rice.edu/bitstreams/d03f9534-0706-4385-982f-a34f204365f7/download)摘要 | 半光滑算子在正则解附近的局部超线性结论；clip/互补条件属相关结构，不是本系统正则性证明 | 应针对F_E/F_phi求根而非对有限容差solver分支直接求导。活动集固定时普通Newton可作局部对照；跨clip需广义导数。Jacobian/预条件/线搜索费用与奇异活动集风险明显；不能复用压力PCG当耦合块求解器 |
| Kang, Wang & Zhu 2025（卷208），[10.1016/j.ijthermalsci.2024.109492](https://doi.org/10.1016/j.ijthermalsci.2024.109492)，[出版方原文节选](https://www.sciencedirect.com/science/article/abs/pii/S1290072924006148) | TEM的ITEM液相率迭代处理焓/液相率不一致；解析例与纯物质熔化实验、网格/时间依赖；摘要报告Fo>1费用快速上升及松弛相关性 | 本代码以T及潜热源求解，已有l–T校正，不等同于ITEM/TEM；其Fo/松弛建议不能直接迁移或用来改M1的dt/0.9。未取得完整公式，方法同异与适用界进一步UNVERIFIED |

可信传统对照应同一C、同一原始可行初值、同一固定评价尺度/联合残差、相同线性精度，并计G次数、源项/组装、QR/内积、状态复制、独立核验、拒绝/回退及完整墙钟。Aitken示意为`omega_k=-omega_(k-1)*<r_(k-1),delta_r>/||delta_r||²`；具体界限/近零分母与历史重置须预注册；AA已有带正则/重启/保护版本应作为强基线，不与未经保护的弱实现比较。这里只设计对照，不实现/调参。

**创新性仍UNVERIFIED。** 普通AA、Aitken、Newton、clip投影、重启或将它们用于LPBF均不是新算法。可能值得论证的是：入口滞后物性与活动集切换、inexact原生求解同时存在时，能否给出同态离散能量/相变残差认证并减少昂贵评估的可证明条件与净成本优势；它首先是待检验的问题。若不能优于上述传统对照，或只是套用已有保护方法，就没有当前算法创新证据，也没有AI必要性证据。

## 5. 唯一最小后续实验提案（未批准、未实现、未运行）

**零CFD的原生单次热映射/独立残差制造解门槛**，不直接新跑M1/采集器或加速算法。一个全新隔离工具、一次构建；失败不修补重建/重试。用8单元静态非正交网格、Euler单旧层、T零梯度/l计算型patch、原M1材料与活跃辐射/蒸发/阻尼形式构造冷固、内部糊状、饱和三类可行状态；冻结输入源字段，制造平衡热源，不调用激光/VOF/动量时间推进。它是代数制造数据，不冒充真实M1物理工况，不改生产方程或配置。

独立逐面/Euler记账以指定解析离散状态制造源，检查原生未松弛及relax后有效矩阵（含边界）与独立F_E/F_phi一致；已知根只在预定舍入/线性误差预算内可接收。人为扰动T、旧层、patch或l应被对应残差拒绝，特别覆盖“clip使delta_l=0而能量/T未收敛”。完整快照往返后单次G结果、原归一化/线性停止与原生直接路径逐字节一致，prevIter覆盖与oldTime不混用。只评估G，不做Aitken/AA/Newton实现、不训练模型；若工具投影/格式/残差独立性不成立即停止。

拟主动批次300 s硬截止，rank1/thread1/CPU0，RSS1 GiB/新增200 MiB为MONITORED_ONLY；原件保护、日志落盘、结束后集中验收，不高频轮询，不sudo/安装。阈值先在预注册误差预算中明确，不因失败调宽；本轮只是设计，连这次非CFD构建也未获执行授权。通过只建立申请真实状态采集/数值参考设计的前置证据，不证明M1收敛、AI收益或物理准确性。

成本动机仍仅为既有T_ASSEMBLY+T_OTHER 62.071852 s/205.01 s=30.2775%包围区域；约2%历史solver净收益尺度为4.1192 s，需扣掉所有验证/回退。不能把该区域全算可省，也不由7244次调用推算算法收益。

## 6. 最终判断与溯源

**NOT_READY**，指尚不能提交已验收的完整状态、定量联合收敛合同及可靠数值参考；不是否认参数化固定点定义。当前能完成的是上述定义/缺口/传统对照设计，不能证明根存在/唯一或已收敛。258步热校正未达原残差门槛继续公开，M1物理准确性与网格收敛UNVERIFIED，压力初值NO_GO及MAG关闭均不改。PR #5保持Draft/unmerged；不合并、不恢复任何旧运行额度。

以下34项约405 kB源码/小型证据在本轮归档核对窗口前后SHA一致；只定向读取一个已保存epsilon1的patch类型，不重扫大日志/旧原场。OpenFOAM路径以安装根的相对逻辑名脱敏；SHA限定本机实际v2512实现，不以网页其他版本代替。无新增二进制/实验原始数据；报告实际提交由git log追溯。

| 逻辑来源 | SHA256 |
| --- | --- |
| `applications/solvers/laserbeamFoam/TEqn.H` | `8542f190581444d0be58cc497ae6a7f1d524eed0998958abb35cd777940c92f2` |
| `applications/solvers/laserbeamFoam/readControls.H` | `64da838052840665f30f49280dfcccaf60e8dc40f86245698d951bd8b654e3da` |
| `applications/solvers/laserbeamFoam/createFields.H` | `69a36578b1f99b468c4d34aff0529e751d591bd8c3b25f9afb2d041e8c8f7ea6` |
| `applications/solvers/laserbeamFoam/laserbeamFoam.C` | `ebbb6768fb47c5940d7253c7285a9fc5a34095d7100d49a5db0cd701977e9110` |
| `applications/solvers/laserbeamFoam/updateProps.H` | `c8f260a46675cca76729aaff0b168f55e617d11cc8ccbdf47a17ff4f024c2d8b` |
| `applications/solvers/laserbeamFoam/updateKappaCp.H` | `521971158e6d3ff4ea54a45de42359412b8721bc6532551ac0b2006be3793c8e` |
| `applications/solvers/laserbeamFoam/UEqn.H` | `586cc973acc489390ba3e2079d39be16d6d7f5137ff80dd76852c71db179082d` |
| `src/MTHD/mthdModel.H` | `5f5b1a291ceb5ea5aa06de994a917fac8feb82b0422e0b2d499a6567f1809221` |
| `benchmarks/performance/M1-stage2.json` | `a3b5801452c9f54391b65998174f7e0b6837e328bc5c366b6cfe17db43a1c6d0` |
| `docs/research/STAGE3_DIRECTION_REASSESSMENT_20261018.md` | `41130cd891d58b58a287356c48dfdc0d85d96b295e6869a43e1feff1078a7820` |
| `docs/validation/M1_TP_INTERNAL_ANALYSIS_20261017.md` | `e4177b43261dffcaef1e909f4d41fcaf8979721fc8554b9658c52ef94f3badef` |
| `docs/validation/M1_TP_INTERNAL_TIMING_20261018-summary.json` | `7262c05e1bd9e4c17afb891de3aab7b583af9cc54a0f9a2e74d3e98fe4c2f753` |
| `docs/validation/M1_REUSE_DEPENDENCY_AUDIT_20261018.json` | `a2b2934cd8ff4f0b8106778bc801783163b61189ea006c3965887aef4db94bb5` |
| `docs/validation/REAL_PRESSURE_REPLAY_20261018.md` | `8e43e33c5e0c63cd41e60582e42ce107fc41f8d76d756025f86a409e579393ae` |
| `OpenFOAM-v2512/src/finiteVolume/fvMatrices/fvMatrix/fvMatrix.C` | `f833cc39d86039f47ebb6d7685939df1af50ff1b4395c86a7dace863ecc3b192` |
| `OpenFOAM-v2512/src/finiteVolume/fvMatrices/fvMatrix/fvMatrixSolve.C` | `9065053a1bde494de9c9d0f6959767c84eadce709c81c5673dbb46b676c557f3` |
| `OpenFOAM-v2512/src/finiteVolume/finiteVolume/ddtSchemes/EulerDdtScheme/EulerDdtScheme.C` | `7c13af1cf0d954a802d742e32d97c74fb9a6b3fecb8cff49a474d856bacff2e9` |
| `OpenFOAM-v2512/src/finiteVolume/finiteVolume/laplacianSchemes/gaussLaplacianScheme/gaussLaplacianScheme.C` | `63f000224c0c7717d9d113d293d576065cae5623fbb115a1308f1e3aff8f96fc` |
| `OpenFOAM-v2512/src/finiteVolume/finiteVolume/convectionSchemes/gaussConvectionScheme/gaussConvectionScheme.C` | `c2f081ce742fd332511e9251b970c4f850d94239edf3343b11d410ec4394d276` |
| `OpenFOAM-v2512/src/finiteVolume/finiteVolume/snGradSchemes/correctedSnGrad/correctedSnGrad.C` | `2d3684bd5e8fbe2ea66fa5138f03ba124566c133c09b36a910816bb3fdc78e3c` |
| `OpenFOAM-v2512/src/finiteVolume/finiteVolume/fvm/fvmSup.C` | `e72a39bc126226ceaa0995ec5a40521c33de1f49486c6c1a6967b7b712384119` |
| `OpenFOAM-v2512/src/OpenFOAM/fields/GeometricFields/GeometricField/GeometricField.C` | `b1de340737a0d928ce88cbfb12409ec4ee0889d1cc97aae042caa8d0bd71160d` |
| `OpenFOAM-v2512/src/OpenFOAM/matrices/lduMatrix/solvers/smoothSolver/smoothSolver.C` | `b23dafc9e5b71ab3e355beca0334aaac51d68e22cecd747361050476f4af14ea` |
| `OpenFOAM-v2512/src/OpenFOAM/matrices/lduMatrix/lduMatrix/lduMatrixSolver.C` | `862fe16f0069b21e199298c43771d486794cdf0ae2588bedf69b9dfeb9baface` |
| `OpenFOAM-v2512/src/finiteVolume/fields/fvPatchFields/basic/zeroGradient/zeroGradientFvPatchField.C` | `db7b8565d03e6c26e02d46d35c923c0278732789e5933805fe37ec4ebb1b6cca` |
| `OpenFOAM-v2512/src/finiteVolume/fields/fvPatchFields/basic/calculated/calculatedFvPatchField.H` | `8a6c50a8d3ce20f4110c98f4ee3e2c4abb9faa02b8410598d85322b9678acfd9` |
| `OpenFOAM-v2512/src/finiteVolume/fields/fvPatchFields/fvPatchField/fvPatchField.C` | `9988af71cd206a1030bde37adbc03cabf32ee168aa98ee608f9f45826a6da16a` |
| `M1/system/fvSolution` | `b4e2690ad8abfc920e259318f7aff974639b3c104a9c913c4c85613e58f101f9` |
| `M1/system/fvSchemes` | `bc9603132c27e48553db8f1bfc23b73bcaee89cda185843a175b8bc6db19e70c` |
| `M1/system/controlDict` | `8dfd63b337c8be18f9d082e9017334530e5ef8f052e69e8e32fbc60de2f89c8a` |
| `M1/constant/transportProperties` | `f5ce7aa1481e3c7652b24c16e07667e50c8daaa535b5c2c788f7e9f68b03db47` |
| `M1/0/T` | `5512b73c789cfca475adb9c6bfc6e0f47e8093d99073bcd794b5f252e3490e63` |
| `M1/saved-1us/epsilon1` | `d7236011686d47ac36c9ec9f03e86022301dbb5a36d8b41246f7ac0105a74c56` |
| `OpenFOAM-v2512/src/OpenFOAM/matrices/LduMatrix/LduMatrix/SolverPerformance.C` | `43aa81c7d127632fa7281aecdf5deed88a364d594abf02828ea1bc357ef7c910` |
