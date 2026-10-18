# 基准设计与实验原则

2026-10-16。S/M/L用途与预算目标已批准；具体网格、粉末选择和正式M定义仍为 **PROPOSED / UNVERIFIED**。执行候选实验不等于批准正式基准。Plate2D继续作为独立串行底层回归。

2026-10-17批准补充（DEC-011）：原M1完整32000单元/1000步配置已正式确定为固定性能开发负载M1_NATIVE_PERFORMANCE_V1，冻结文件为benchmarks/performance/M1-stage2.json；物理准确性/网格收敛参考仍UNVERIFIED。旧探索配置的PROPOSED标签和历史输入保持，不能将新用途批准追溯改写为旧物理验证已完成。阶段2本批仅三次新M1及权限允许时最多一次外部采样，不自动运行M2/M3、改变物理或开发AI。

## 分级与候选

| 级别 | 用途/案例 | 初始规模与演化（提案） | 预算目标 / 实测 |
| --- | --- | --- | --- |
| S | fiveLasersOnSubstrate三维平基板探针，五激光原样 | 16×8×16=2048单元，dt1e-8，10步至1e-7，串行 | ≤约2分钟 / UNVERIFIED |
| M-A | 同一三维平基板，先标定再建立原版参考 | 40×20×40=32000与原80×40×80=256000作候选；先100步，再按实际熔化/迭代活动决定时长 | 约5–15分钟 / UNVERIFIED |
| M-B | LPBF_small既有固定颗粒，短程 | 原40×60×80=192000单元或经批准的裁剪；不能粗化至颗粒不可辨识 | 约5–15分钟 / UNVERIFIED |
| L | 代表性固定粉末、必要分辨率与长演化 | 按最终模块/研究问题批准；不是日常自动任务 | 不自动启动 / UNVERIFIED |

S输入从上游3c93f2657e089e22e9a8298648292969e85a4bad的跟踪文件复制，保留物性、五激光、边界、离散和求解容差，只在隔离副本改变网格单元数、应用名称及短程推进/输出控制。几何600×300×600微米，没有empty物理方向。粗网格不能解析真实熔池细节，短跑不保证熔化、小孔或多次反射代表性。配置为 benchmarks/threeD-smoke/config.json，状态PROPOSED。

## 无粉末与固定粉末

| 方案 | 初始化/成本 | 覆盖与缺口 | 当前判断 |
| --- | --- | --- | --- |
| A 平基板 | blockMesh/checkMesh/setFields，无DEM；网格/步数可控 | 调用射线/热源、能量、VOF、PIMPLE；困难相变需温度/液相率证据。削弱颗粒遮挡、孔隙和复杂曲率反射。此官方案例使用钛合金参数，并非316L | 推荐先作便宜探针；非最终M/LPBF选择 |
| B 固定颗粒 | 复用LPBF_small/location、setSolidFraction采样后旋转；初始化可能昂贵须单列 | 更接近颗粒遮挡/间隙/反射；是否构成热点待测。单一布局不代表统计泛化 | PROPOSED，不必每次DEM |

实际Make/options链接原生libgeometricVoF及MTHD/laserHeatSource，不能用另编译但未链接的libgeometricVoFLMFOAM推断瓶颈。S使用isoAdvector、静态网格、电磁默认关闭，因此不覆盖MULES、AMR、电磁活动或MPI。后续确需这些路径时另设计探针，不为覆盖率无依据改物理。

### 固定颗粒的源码核查

静态读取官方LPBF_small/constant/location：头部47颗粒、实际47行，均为四列有限值且半径为正，半径范围5.965e-6至1.88315e-5米（按工具直接读入的SI解释）。这只证明文件基本结构，不证明颗粒重叠、边界截断或初始化正确。setSolidFraction直接读取x/y/z/半径，读取bedPlateDict并按z初始化基板，之后官方transformPoints将网格转到激光坐标。选择B前仍须核查单位/范围、哈希和前后坐标关系，并用alpha范围/金属体积及几何切片确认初始化。不能用其setFieldsDict代替颗粒初始化。

**不执行LPBF_small/Allrun**：它检测到liggghts会运行DEM_small。本轮只确认固定布局候选和必要检查，未验证其合法初始化，也不实现B运行工具。

## S工具与首次执行

准备工具不执行OpenFOAM；原生Allrun分mesh/solve两次调用；Allclean拒绝清理。显式 --accept-proposed-config 仅表示试运行候选，不批准M定义。两阶段只能顺序运行，失败先定位，不自动继续。

在仓库根目录先加载of2512。已有构建只在project_commit与当前HEAD相同时可复用；否则用新的隔离报告进行标准Allwmake构建，8作业、可复用缓存、不Allwclean。没有绕过现有版本契约，编译时间不计入S求解预算。

```bash
of2512
if bash scripts/validate_build.sh --jobs 8 \
    --report-dir validation/threeD-smoke-001/build; then
    printf 'Inspect BUILD_ARTIFACT_CHECKS_PASSED before continuing.\n'
else
    rc=$?; printf 'BUILD failed: %s; retain build.stdout-stderr.txt\n' "$rc"
fi
```

```bash
if python3 scripts/prepare_smoke_case.py \
    --run-dir runs/threeD-smoke-001 \
    --build-dir validation/threeD-smoke-001/build \
    --solver laserbeamFoam --accept-proposed-config \
    --mesh-timeout 180 --solver-timeout 120; then
    printf 'PREPARED only; no CFD utility has run.\n'
else
    rc=$?; printf 'Preparation failed: %s\n' "$rc"
fi
```

```bash
if bash runs/threeD-smoke-001/Allrun mesh; then
    printf 'Inspect log.checkMesh and log.setFields before solve.\n'
else
    rc=$?; printf 'Mesh/initialization failed: %s; retain case.\n' "$rc"
fi
```

```bash
if bash runs/threeD-smoke-001/Allrun solve; then
    cat runs/threeD-smoke-001/smoke.txt
else
    rc=$?; printf 'Solve/check failed: %s; inspect stage log and smoke.txt if present.\n' "$rc"
fi
```

仅用户显式执行启动真实计算，Codex/CI不跑CFD。每个mesh步骤默认180秒、solver120秒，准备时可配；这是超时上限而非总耗时保证。CPU串行/线程1，GNU time记录墙钟/RSS，当前没有强制内存上限。超预算保留实测并调整候选，不降精度。所有运行目录必须全新，失败后也不清理重用。

## 数值检查与参考

S成功仅称SMOKE_CHECKS_PASSED：正常End/退出0、10步终时、2048单元、Mesh OK、必需字段和全部顶层场的解析/有限值/边界尺寸、alpha范围、正温度、正沉积及uniform检查。复用解析器的场“自比较”仅检查格式/有限值/尺寸，**不构成独立参考或数值等价验证**。未知输出返回REVIEW_REQUIRED，不当PASS；未做能量闭合，也不保证熔化。

M参考NOT_ESTABLISHED。批准候选后固定原版输入、重复运行，再比较同负载AI入口。不能拿写死十步的Plate2D比较器宣称验证任意M。记录全部时刻/边界、金属体积、沉积积分、温度/液相率及熔池指标，分别控制迭代、网格/时间离散和物理预测误差。无参考不写“精度保持”。

## 性能测量

先原版无埋点：GNU time分阶段墙钟/RSS、逐步ExecutionTime/ClockTime及迭代/调用事件；单列准备、网格、初始化、求解/I/O。ClockTime是累计量且分辨率有限，不能当单步时间；差分须检查单调性，短S不用于模块排名。当前工具保留累计时间样本，不据此分配射线/VOF/压力/温度耗时。

M标定后固定构建、负载、输出频率、亲和与线程，分开冷启动/后续重复，建议至少3次报中位数和范围。I/O成本用批准的成对实验隔离，不混淆输出变化和算法收益。普通用户能用perf才采样；保留事件/调用栈能力/开销，不sudo、不改系统权限。无符号或采样不足时再讨论可关模块计时，先保留无埋点基线并测自身开销。

覆盖表逐项登记射线/多次反射、VOF、PIMPLE、温度/相变、电磁、动态网格、通信、I/O是否激活；未激活标NOT_EXERCISED，不能填0%证明可忽略。若M初始化支配或未出现所需熔化/反射，保留结果、调整提案并请求批准，不先定AI模块。

## 数据和回传

运行目录保存manifest/config、输入/初始化SHA、二进制/库校验、ldd、stage log/exit/time、execution与smoke.txt/json。manifest含私有绝对路径，不能直接公开。首次回传smoke.txt/json、checkMesh摘要、各exit/time摘要；失败加首个阶段日志，不必传大场或完整主机环境。

源码/构建/采集工具版本、工作负载、资源和实测追加EXPERIMENT_LOG；当前所有三维计时与运行状态UNVERIFIED。
