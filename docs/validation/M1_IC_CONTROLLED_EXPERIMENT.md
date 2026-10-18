# M1-IC：单次初始 alpha 受控探索

授权：[DEC-007](../research/DECISION_LOG.md)。阶段1，正式M仍PROPOSED，PR #4继续Draft。已有原场空间诊断见[EXP-003-ADD-01](../research/EXPERIMENT_LOG.md)；Codex引用用户提供的ChatGPT核验，没有独立取得该反馈包/原场。本工具及配置仅经合成检查；实际OpenFOAM初始化、运行和三方物理结果均UNVERIFIED。

## 变量、假设和适用范围

新独立案例M1-IC：原版laserbeamFoam，40×20×40，固定dt=1e-8 s，300步至3 μs，每100步输出，串行/计算线程1。材料、五激光、光学、边界条件规律、方程、格式、容差和原生VTK保持M1。controlDict只改变终时，writeInterval仍100；不更改原M1/M3目录或旧报告。配置见[M1-IC.json](../../benchmarks/threeD-exploration/M1-IC.json)。

干预是**新初态alpha**：原生M3的`0/alpha.metal`按8个细单元的正体积加权平均，限制到原生M1位置。准备时核对原生坐标、体积、质心、完整覆盖及相同域，不依赖单元编号；应用时再次匹配新blockMesh的原生粗格位置。逐父单元除以子体积和，保证凸平均且常量不越界；子体积和必须与父体积满足既有几何rtol=1e-10，金属积分也核对，不裁剪alpha或全局归一。源alpha必须严格在[0,1]且有限。

`setFields`先按原流程执行，随后独立`restrictAlpha`阶段仅替换新案例的`0/alpha.metal`。保留BC类型、规定入口值；zeroGradient面的派生value缓存由新owner alpha重算，不是改变边界条件规律。原初场和网格前后逐文件SHA记录，除该场外必须完全不变；不伪装为原box中心选择初始化PASS。独立checker profile的初始化方法是`M3_NATIVE_ALPHA_VOLUME_RESTRICTION_8_TO_1`，而原M检查器仍拒绝M1-IC身份。

依据[OpenFOAM.com v2512 setFields源码](https://api.openfoam.com/2512/setFields_8C_source.html)第190–197行，原工具在设置内部值后还按patchInternalField处理边界。初始化器先检查干预前alpha匹配原M1，再应用限制值；边界数值采用展开后的语义检查，允许等值的uniform/nonuniform与0/0.0写法，不把格式差异当作物理改变。当前模板atmosphere在y=0且规定inletValue=0，保留其数值及类型。

预期90–105 μm粗层alpha约0.5、更高层1、金属体积约7.29e-11 m³；这是待实机核对的预期，检查器从源原场计算期望，不硬编码体积造PASS。分数alpha不能单独证明VOF重构界面精确位于97.5 μm。报告对该界面保留UNVERIFIED，不在alpha=0.5处武断指定平面。

可检验假设：同粗网格初态干预是否改变早期沉积位置、局部功率密度、温升及首次保存非零液相率。M1与M1-IC在相同前300步比较；M1-IC与M3仍有网格、源分配和相变离散差异。即使IC更接近M3，也不能独立解释全部早期温差或宣称收敛/物理准确性。第一次保存非零不等于连续时间的精确起熔时刻。

## 1. 更新与隔离构建

以下命令分块执行，上一块失败就停；在已有仓库根目录，普通交互终端不启用`set -e`。若终端已启用，命令也用if捕获非零，避免因正常的FAIL/REVIEW关闭终端。不更新原场，不重新运行M1/M3。

```bash
if git fetch origin &&
   git switch feat/threeD-progressive-m-exploration &&
   git pull --ff-only; then
    git rev-parse HEAD
else
    rc=$?; printf 'STOP: Git update failed (%s).\n' "$rc"
fi
```

单独执行以下变量设置；示例M1/M3路径按已有目录实际名称核对。不指定新的M1/M3运行目录。

```bash
PROJECT_DIR=$(git rev-parse --show-toplevel)
M1_CASE_DIR="$PROJECT_DIR/runs/threeD-M1-001"
M3_CASE_DIR="$PROJECT_DIR/runs/threeD-M3-001"
IC_CASE_DIR="$PROJECT_DIR/runs/threeD-M1-IC-001"
IC_BUILD_DIR="$PROJECT_DIR/validation/build-m1-ic-001"
IC_REPORT_DIR="$PROJECT_DIR/validation/m1-ic-spatial-001"
of2512
```

源码差异只读核对；下面命令无输出且返回0才继续，文档/工具提交不当作相同二进制。

```bash
if git diff --exit-code 1d32b6fda86d730b8e18b1d9f50e1752fffa5416 HEAD -- applications src Allwmake &&
   git diff --exit-code 8f60695ac39dd7c5ce096ad5781528c229f08ce3 HEAD -- applications src Allwmake; then
    printf 'Solver/library/build source unchanged; new build record still required.\n'
else
    rc=$?; printf 'STOP: source difference (%s); request review.\n' "$rc"
fi
```

```bash
if bash scripts/validate_build.sh --report-dir "$IC_BUILD_DIR" --jobs 8; then
    cat "$IC_BUILD_DIR/summary.txt"
else
    rc=$?; printf 'STOP: build failed (%s); retain summary/build.stdout-stderr.txt.\n' "$rc"
fi
```

这是匹配当前HEAD的新隔离构建，底层仍Allwmake/wmake；不Allwclean、不覆盖旧安装。会消耗8个编译作业并写构建产物；不宣称本轮已实机编译。准备到求解期间不要更新HEAD。旧M1/M3 manifest仍保留原运行/构建版本，离线检查不要求它们等于新HEAD。

## 2. 只读源证据与新案例准备

先本地看`df -h "$PROJECT_DIR"`与`free -h`，避免竞争负载；不用回传主机详情。准备器要求当前可用磁盘至少3 GiB，并重新校验源输入/初始化哈希、原完整PASS记录、版本、日志、坐标与alpha。不会重跑原完整检查器或改其报告。原M1/M3输入除blockMeshDict不得不同。源solver/library/Allwmake与当前HEAD有差异时拒绝。

```bash
if python3 scripts/m1_ic.py prepare \
    --run-dir "$IC_CASE_DIR" --build-dir "$IC_BUILD_DIR" \
    --m1-case-dir "$M1_CASE_DIR" --m3-case-dir "$M3_CASE_DIR"; then
    cat "$IC_CASE_DIR/preflight.json"
else
    rc=$?; printf 'STOP: IC preparation failed (%s); retain diagnostics.\n' "$rc"
fi
```

准备会读取两个已有mesh、初态和日志，生成新案例私有`ic-data/restriction-reference.json`（坐标、体积、alpha及消费源哈希）；完整参考不公开或打包。后续阶段按SHA复查源文件，无需重复解析细网格。准备开销UNVERIFIED，不计为solver时间。已有运行目录拒绝覆盖。

仅一次CFD尝试：solve前原子创建checkout级`runs/.m1-ic-solve-attempt/`，失败也保留，禁止通过删除标记或换目录重试。第二次运行需负责人另行批准；此标记不阻止已完成案例的只读检查和归档。

## 3. mesh 与专用初始化，审阅后再 solve

```bash
if [[ ! -e "$IC_CASE_DIR/time.workflow.mesh.txt" && ! -L "$IC_CASE_DIR/time.workflow.mesh.txt" ]] &&
   LC_ALL=C /usr/bin/time -v -o "$IC_CASE_DIR/time.workflow.mesh.txt" \
   bash "$IC_CASE_DIR/Allrun" mesh; then
    cat "$IC_CASE_DIR/mesh-check.txt"
else
    rc=$?; printf 'STOP: mesh/IC initialization failed (%s); retain logs.\n' "$rc"
fi
```

必须检查：32000个Cartesian正体积六面体、Mesh OK、setFields成功、restrictAlpha退出0、所有初场及边界通过、受控初态PASS、金属积分与原M3相符、`.mesh-complete`存在。详细alpha层及初始化证据见`mesh-summary.json`、`ic-initialization.json`；`box_centre_selection=NOT_APPLICABLE`，不能套用原M1的20800个二值金属单元检查。失败不进入solve。

```bash
if [[ ! -e "$IC_CASE_DIR/time.workflow.solve.txt" && ! -L "$IC_CASE_DIR/time.workflow.solve.txt" ]] &&
   LC_ALL=C /usr/bin/time -v -o "$IC_CASE_DIR/time.workflow.solve.txt" \
   bash "$IC_CASE_DIR/Allrun" solve; then
    solve_rc=0
else
    solve_rc=$?
fi
printf 'IC solve/check exit: %s; do not rerun if nonzero.\n' "$solve_rc"
```

检查实际可执行文件、二进制/共享库SHA、ldd真实依赖路径、v2512/WM_OPTIONS/HEAD、线程和MPI环境。原生solver超时600 s，TERM后10 s kill宽限；mesh每命令180 s。源码没改也不跳过版本契约。RSS8 GiB和数据3 GiB为MONITORED_ONLY，非强制隔离。外层含前置检查/后检查，可能超过600 s。

成本情景：按M1 214.50 s×300/1000为64.35 s，因原M1后期变慢，早期300步的实际成本可能较低，也可能受新alpha影响，均UNVERIFIED。不是600 s内完成的保证。3个输出的可变场数据约原M1的3/10，加静态mesh、参考与报告，不能把总目录也简单乘0.3。记录solver、restrictAlpha、prepare、mesh/solve包装、离线检查和归档各自范围，不混加嵌套时间，不称AI收益。

## 4. 离线全场复核和反馈包

在solve包装结束后执行，以纳入完整工作流计时。先备份新IC旧报告；不触碰旧M1/M3报告。以下子shell即使非零也由外层if捕获，不退出交互终端。

```bash
if bash -s -- "$IC_CASE_DIR" <<'BASH'
set -euo pipefail
case_dir=$1
backup=$(mktemp -d "$case_dir/report-backup.before-export.XXXXXXXX")
for name in m.txt m.json observations.csv execution_times.csv mesh-summary.json; do
    if [[ -f $case_dir/$name && ! -L $case_dir/$name ]]; then
        cp -- "$case_dir/$name" "$backup/"
    fi
done
git rev-parse HEAD > "$backup/checker-commit.txt"
if python3 scripts/m1_ic.py check --case-dir "$case_dir" --feedback-bundle; then
    check_rc=0
else
    check_rc=$?
fi
printf 'IC offline exit: %s (0=PASS, 1=FAIL, 2=REVIEW_REQUIRED).\n' "$check_rc"
exit "$check_rc"
BASH
then
    printf 'Review EXPLORATION_CHECKS_PASSED and archive COMPLETE separately.\n'
else
    rc=$?; printf 'IC offline/backup failed (%s); retain all evidence.\n' "$rc"
fi
```

检查300步/3 μs、3个预期时刻、全部实际及必要场、internal/boundary、uniform、非有限值/alpha/正温度及完整日志；额外严格验证受控初态与源哈希。缺失/不支持/超范围仍FAIL或REVIEW_REQUIRED，不字节自比较放行。保存初态证据不等于独立物理精度验证。

白名单反馈使用独立`m1-ic` profile，包括新初始化证据及restrictAlpha log/exit/time，不含原生场/mesh/私有manifest/完整限制参考。打印tar.gz及外部SHA256路径，核对EXPORTED、COMPLETE和检查退出码；脱敏是尽力处理，分享前请审阅。失败也可只打包现有诊断（不重跑CFD）：

```bash
if python3 scripts/export_smoke_feedback.py --profile m1-ic \
    --case-dir "$IC_CASE_DIR" --diagnostics-only; then
    printf 'Inspect archive completeness; export does not convert a failed check to PASS.\n'
else
    rc=$?; printf 'Export failed (%s).\n' "$rc"
fi
```

## 5. 三方只读空间对照

IC全场检查PASS且3个时刻存在后再运行，新的validation报告目录拒绝覆盖。无需重编译或启动CFD。

```bash
if python3 scripts/compare_m1_ic.py \
    --m1-case-dir "$M1_CASE_DIR" --m3-case-dir "$M3_CASE_DIR" \
    --ic-case-dir "$IC_CASE_DIR" --report-dir "$IC_REPORT_DIR"; then
    compare_rc=0
else
    compare_rc=$?
fi
printf 'Three-way exit: %s (0=COMPARISON_COMPLETED, 1=FAIL, 2=REVIEW_REQUIRED).\n' "$compare_rc"
```

回传两个小包：IC运行反馈tar.gz+SHA256，以及`validation/…/m1-ic-comparison-feedback.tar.gz`+对应SHA256。新三方报告包含JSON/CSV、FILES及内部哈希，消费源文件读取窗口前后SHA检查。原M1/M3源/构建版本、新IC运行/构建版本和比较工具提交分别保留。不以“COMPARISON_COMPLETED”冒充数值相等或物理PASS。

| 对照与输出 | 含义和限制 |
| --- | --- |
| initial / controlled_initialization | 初始金属量、alpha y层、分数单元；M1/M3二值面定义保留，IC不指定精确重构面 |
| metrics.csv | 1/2/3 μs各自原生沉积总功率/峰值/质心/有效支撑体积、金属/液态体积、温度/速度/alpha/epsilon1 |
| profiles_y / laser_profiles_y | 初态及保存时刻y层/最近名义激光轴列剖面，含采样偏移；没有原生t=0 Deposition就不杜撰初始沉积 |
| M1_to_IC | 相同粗网格前300步的初态干预响应，IC按原生坐标重新排序 |
| IC_to_restricted_M3 | 与8→1限制M3的L1/L2/L∞及相对范数；仍耦合网格/源分配/相变离散，不能单独归因 |
| positive_deposition_overlap | 同粗格上∫min(Qa+,Qb+)dV / min(Pa+,Pb+)，任一正功率为0时null；不是原生亚单元重叠 |
| alpha_times_epsilon1 | 先乘后限制，避免平均乘积与乘积平均混淆；液态量为∑alpha×epsilon1×V |
| T_common_metal_alpha_weighted | 细T以alpha加权限制，在双方alpha>0.5交集上比较；不是焓/能量守恒证明，须同看原生峰值和全域差异 |
| first_observed_melting_s | 保存时刻首次非零；同时列alpha>0.5与alpha>0，后者可能包含数值尾迹，不互相替代 |
| source_records / resources | 各原始版本、迭代摘要、solver与工作流成本，离线诊断单列；不是热点归因或AI性能 |

范数定义与源采样限制沿用[跨网格说明](M1_M3_SPATIAL_COMPARISON.md)。不额外引入物理差异PASS阈值；大差异原样报告，工具完成不保证假设成立。解析失败需返回首个路径/原因，不调容差。

## 失败反馈及后续判断

- 构建失败：新build的summary.txt、build.stdout-stderr.txt；不改旧构建记录。
- mesh/初始化失败：console首个阶段、log.checkMesh/log.setFields/log.restrictAlpha、exit/time及mesh-check；不要直接手改原生场后续跑。
- solve失败：solver.exit.txt、log.laserbeamFoam、solver.time.txt；不重试、不续算、不调物性/功率/dt/容差。
- 离线失败：m.txt/json首个问题或comparison.txt/json中的路径；必要时只提供涉及文件的小型头部/结构，避免直接上传大量原场。

收到真实IC反馈后先核验来源/初始化/完整检查，再判断同粗网格是否移动了沉积层、增大了早期温升或提前观察到熔化。没有改变或只部分接近M3，同样是有效否决/约束证据；仍不能排除热源采样、空间分辨率或其他源项。是否需要下一组受控实验由负责人另批，不自动扩规模、合并PR或宣布阶段1完成。
