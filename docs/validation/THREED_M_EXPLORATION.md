# 阶段1三维 M 分级探索：Ubuntu 执行与反馈

授权：[DEC-006](../research/DECISION_LOG.md)。这是探索工具开发与用户显式试运行的范围，不是正式M基准批准。阶段1仍IN_PROGRESS；无AI、物理精度或模块热点结论。M1原生求解成功并观察熔化，2026-10-17已回传修复后离线PASS，见[EXP-002及ADD-01](../research/EXPERIMENT_LOG.md)，原REVIEW历史保留。已有M1用户直接使用[M3预检与分阶段运行](M1_RECHECK_M3_PREFLIGHT.md)第1及3–5节，不重跑下面的M1首次执行步骤。M2暂缓，M3仍须匹配当前HEAD的新隔离构建/资源预检；Codex和CI不运行OpenFOAM。

## 固定负载与分级

| 配置 | 网格 | 固定dt / 步数 / 终时 | 写出间隔 | 求解器墙钟护栏 |
| --- | --- | --- | --- | --- |
| M1（优先） | 40×20×40=32000 | 1e-8 s / 1000 / 1e-5 s | 100步，共10时刻 | 1800 s |
| M2（条件性） | 同M1 | 1e-8 s / 3000 / 3e-5 s | 300步，共10时刻 | 2700 s |
| M3（条件性） | 80×40×80=256000 | 1e-8 s / 1000 / 1e-5 s | 100步，共10时刻 | 3600 s |

配置位于[threeD-exploration](../../benchmarks/threeD-exploration)。三组保持锁定上游3c93f265的600×300×600微米平基板、原材料、五激光/扫描/光学、方程、边界、格式和求解容差；仅按授权改变网格、演化/输出控制及执行预算。原版laserbeamFoam、MPI rank1、计算线程1，无粉末/DEM/续算。M1一次1000步自然写出第100/500步，不额外重复短跑。

原生输出时刻同时写射线VTK/series；保留并计入求解器墙钟，不静默关闭，也不把这些文件打进反馈包。对M1/M3不同网格的成本与观测差异，只称网格敏感性，不称AI加速或两级网格收敛证明。

## A. 更新、一次构建与环境核查

在现有仓库根目录执行。每块失败均先停止并保留日志；以下001目录均要求此前不存在，冲突则整体换新编号，不清理。不要在准备、mesh和solve之间更新HEAD。三套探索可使用同一提交的同一隔离构建，无需每组重新编译。

```bash
if git fetch origin && git switch feat/threeD-progressive-m-exploration && git pull --ff-only; then
    git rev-parse HEAD
else
    printf 'STOP: update failed; do not continue.\n'
fi
of2512
```

`of2512`由用户在交互终端加载；运行工具只检查已加载环境，不调用该alias/function。不升级系统、不Allwclean、不覆盖旧安装。

```bash
if bash scripts/validate_build.sh --jobs 8 \
    --report-dir validation/threeD-m-001/build; then
    cat validation/threeD-m-001/build/summary.txt
else
    rc=$?; printf 'STOP: build failed (%s); retain build.stdout-stderr.txt.\n' "$rc"
fi
```

核对BUILD_ARTIFACT_CHECKS_PASSED、v2512/WM_OPTIONS、完整project_commit=当前HEAD，以及安装/动态依赖来自该隔离构建。可复用wmake缓存；只有匹配记录的既有构建可替代本节新构建。源码S原运行7c094679不冒充本轮新构建提交。

## B. 优先 M1：准备、mesh、检查，再求解

准备只复制锁定输入和生成运行入口，不执行CFD。预检检查输入、构建、可用磁盘及案例资源；RSS/数据预算尚无测量时如实标未知。

```bash
if python3 scripts/prepare_m_case.py --experiment M1 \
    --run-dir runs/threeD-M1-001 \
    --build-dir validation/threeD-m-001/build; then
    printf 'Prepared M1 only; no CFD has run.\n'
else
    rc=$?; printf 'STOP: preparation failed (%s).\n' "$rc"
fi
```

```bash
if [[ ! -e runs/threeD-M1-001/time.workflow.mesh.txt && ! -L runs/threeD-M1-001/time.workflow.mesh.txt ]] && \
    LC_ALL=C /usr/bin/time -v -o runs/threeD-M1-001/time.workflow.mesh.txt \
    bash runs/threeD-M1-001/Allrun mesh; then
    cat runs/threeD-M1-001/log.checkMesh
    cat runs/threeD-M1-001/log.setFields
else
    rc=$?; printf 'STOP: mesh/initialization failed (%s); retain case.\n' "$rc"
fi
```

要求32000三维单元、Mesh OK、初场初始化和离线mesh检查通过。新网格的金属单元数不等于S的1280；体积变化以本次自己的初始0场为基准。mesh失败不启动solver。必要时可单独执行纯离线`python3 scripts/check_m_case.py --case-dir runs/threeD-M1-001 --mesh-only`并用if捕获退出码。

确认mesh后单独执行以下块；一次运行推进1000步，不在每个输出时刻暂停等待批准。超时、崩溃、NaN等保留现场；不重用失败目录或自动改dt。

```bash
if [[ ! -e runs/threeD-M1-001/time.workflow.solve.txt && ! -L runs/threeD-M1-001/time.workflow.solve.txt ]] && \
    LC_ALL=C /usr/bin/time -v -o runs/threeD-M1-001/time.workflow.solve.txt \
    bash runs/threeD-M1-001/Allrun solve; then
    solve_rc=0
else
    solve_rc=$?
fi
printf 'M1 solve/check exit: %s; retain all logs if nonzero.\n' "$solve_rc"
```

外层GNU time结束后，**显式**离线检查与打包。成功或失败都可执行；不重跑CFD，也不修改场。命令更新m.txt/json与观测CSV；重复检查前若需保留旧报告，先另存副本。

```bash
if python3 scripts/check_m_case.py --case-dir runs/threeD-M1-001 --feedback-bundle; then
    check_rc=0
else
    check_rc=$?
fi
printf 'M1 offline status: %s (0=checks passed, 1=FAIL, 2=REVIEW_REQUIRED)\n' "$check_rc"
```

最终应有m.txt/m.json、observations.csv、execution_times.csv、mesh-summary.json以及反馈目录中的唯一tar.gz、清单和SHA256记录。命令显示归档绝对路径、大小和检查/归档各自状态；查看脱敏文本后再上传ChatGPT，不上传原始字段、VTK或完整私有manifest到公开GitHub。

## C. M1分析后，用户分别启动 M2 / M3

两组均不自动运行。根据本次M1实测反馈，优先M3同物理时间空间敏感性，M2暂缓；以下M2命令仅保留为后续条件选项，不是当前下一步。先确认M1全部检查真实通过、原场未在复核中变化、实际计时/RSS/数据量可接受且构建匹配。M2用于有依据的更长热积累/后续演化；M3用于同物理时间的网格敏感性，不能以两级网格证明收敛。

```bash
if python3 scripts/prepare_m_case.py --experiment M2 \
    --run-dir runs/threeD-M2-001 --build-dir validation/threeD-m-001/build \
    --m1-case-dir runs/threeD-M1-001 \
    --reason 'Inspect longer thermal and liquid-fraction evolution after reviewing M1'; then
    printf 'Prepared conditional M2; inspect cost/resource preflight before running mesh.\n'
else
    rc=$?; printf 'STOP: conditional M2 preparation blocked (%s).\n' "$rc"
fi
```

```bash
if python3 scripts/prepare_m_case.py --experiment M3 \
    --run-dir runs/threeD-M3-001 --build-dir validation/threeD-m-001/build \
    --m1-case-dir runs/threeD-M1-001 \
    --reason 'Compare M1 temperature, liquid volume and deposition at the same physical times'; then
    printf 'Prepared conditional M3; inspect cost/resource preflight before running mesh.\n'
else
    rc=$?; printf 'STOP: conditional M3 preparation blocked (%s).\n' "$rc"
fi
```

`--reason`应由用户改为基于M1结果的真实目的，不把示例文字视为研究证据。各自准备成功后，按B节的mesh→检查→solve→离线打包顺序，将目录替换为M2或M3；不要写自动三组串跑循环。预检结果有超预算、M1失败、溯源/输入变化或磁盘不足时先停止，不用force绕过。成本推算仅为M1实测规模比例的粗估，复杂相变、I/O与迭代可能非线性增长；不作为完成时间承诺。

## 数值状态、物理活动和成本的解释

- 基础检查：三维网格/质量、退出0与End、精确预期时间步和全部输出时刻；全部实际字段的internal/boundary解析、尺寸、有限性，alpha边界/有界性、必要字段与uniform。未知格式不得静默略过。自比较只是解析与有限性检查，不是独立原版A/B或物理验证。
- M的uniform状态必须有可解析的原生字段/字典语义；支持OpenFOAM函数状态的无FoamFile头字典，以及v2512的uniformDimensionedScalarField。后者要求对象名匹配文件名、七个有限数值量纲指数和单个有限value；cumulativeContErr按官方AUTO_WRITE定义要求存在且无量纲。符号单位表达式等未支持语法仍REVIEW_REQUIRED；未知格式不跳过，单文件与自身逐字节相同没有验证意义。不改变S或独立A/B比较器行为。
- 每时刻观测：全域及alpha>0.5金属区域T、液相率、速度、金属体积及相对初始变化、液态金属体积估计、Deposition量纲与积分；保留日志中的激光/射线、VOF、温度、压力、相变及残差/迭代证据。不按未知阈值宣称已收敛或无界面误差。
- 热沉积、温升、达到1928.15 K固相线、非零金属液相率、可辨液相区域、显著自由面运动、多次反射分别记录。液相线1978 K。无熔化可以是有效探索结果，不通过改功率/材料/容差制造熔池；也不能只因T超过固相线就宣布形成可信熔池。
- 积分由实际网格体积和原字段dimensions解释；Deposition最大值不是总吸收功率，快照的体积积分不是累计吸收能量或能量闭合。粗网格包围盒/液态体积只是观测，不是实验熔池尺寸验证。
- 资源：每阶段GNU墙钟/RSS、累计ExecutionTime/ClockTime与可用差分、案例输出数据量和原生I/O、离线检查与打包成本分别记录；零/粗分辨率差分注明不可用，不能把调用次数换成模块占比。没有直接模块计时或充分采样，不能宣布热点。
- 8 GiB最大RSS和3 GiB案例数据是MONITORED_ONLY观察预算，不能保证运行中强制停在该值；阶段墙钟timeout才是执行护栏。超预算记录并阻止后续分级，保留失败数据，不sudo/升级/清理。首轮每组1次，无自动重试或续算。

## 失败诊断和最小反馈

无求解结果或只有mesh失败日志时也可导出已有诊断，不要求PASS：

```bash
if python3 scripts/export_smoke_feedback.py --case-dir runs/threeD-M1-001 \
    --profile m --diagnostics-only; then
    printf 'Diagnostics exported; this does not mean numerical PASS.\n'
else
    export_rc=$?; printf 'Archive FAILED (%s); retain original logs.\n' "$export_rc"
fi
```

反馈优先使用新生成包。定位顺序：m.txt/json的首个问题→对应阶段log/exit/time→mesh-summary与每时刻CSV→provenance与输入/构建记录。数值FAIL/REVIEW_REQUIRED的退出码不会因打包成功改为0；独立导出器退出0只代表归档生成成功。缺少外层计时为INCOMPLETE_TIMING，不伪称完整流程预算。

反馈白名单只扩展M报告/CSV/摘要及原生诊断文本，保留S实机验收过的脱敏、符号链接拒绝、限额、唯一命名、归档重读和SHA256机制。检查状态、归档状态、来源版本分开；不以最新工具HEAD替代原始运行/构建提交。若日志超限或文件缺失，明确PARTIAL/omitted，不静默截断。工具不上传数据。

M文本单文件上限16 MiB、归档负载64 MiB、压缩包16 MiB；S的4/16/8 MiB默认限额不变。归档内m.json记录离线检查成本，bundle.json记录主体诊断数据压缩的计时及排除项；包含压缩、核验、归档和哈希/清单写出的导出计时另存同名`.export.json`，不把最后写入该摘要的成本伪装成已包含。若需审查完整导出范围，可同时回传这一小型脱敏sidecar；这些后处理时间不计作solver时间或AI收益。
