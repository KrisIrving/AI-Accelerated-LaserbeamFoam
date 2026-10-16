# 三维S首次实测：执行前核对与最小反馈

2026-10-16；所属已批准阶段1。S定义不变：fiveLasersOnSubstrate衍生三维平基板，2048单元、固定dt1e-8、10步至1e-7，串行，无DEM。仍是PROPOSED探针，真实运行UNVERIFIED。本页为操作说明，不修改章程、计划、正式基准或验收要求。

## 工具链核查结论

| 环节 | 当前契约与待验证内容 |
| --- | --- |
| build | 标准Allwmake，8/12作业，新的隔离安装；summary记录project_commit/WM_OPTIONS/状态。无Allwclean；不覆盖旧安装。真实编译由用户执行。 |
| prepare | 必须BUILD_ARTIFACT_CHECKS_PASSED且build commit=HEAD；从锁定上游Git blob取输入，不复制已演化目录。只改短跑网格/控制参数，逐路径哈希。无网格/求解执行。 |
| mesh | 环境/程序/库来源和哈希检查后，initial→0，再blockMesh、checkMesh、setFields；Mesh OK与阶段退出0后记.mesh-complete和初始化快照。不自动solve。 |
| solve | 要求.mesh-complete，全量初始化路径/哈希一致，新求解尝试、无旧时间/processor目录；仅指定安装中的求解器。CPU单进程、数值库线程1，超时默认120秒。 |
| failure evidence | 本轮补齐solver失败时也保存solver.exit.txt和solver.time.txt；每阶段log/exit/time均保留。失败后不重用案例。 |
| offline check | 继续原有有限值、场/显式边界、alpha/温度/沉积、日志、步数/终时、uniform检查；本轮仅补运行指标报告，不改通过门槛。 |

没有真实OpenFOAM时不能证明网格、初始化或热源工作。GNU time、字典读取、场写出及实际路径仍待Ubuntu。本轮不改求解器、共享库、官方教程、S配置JSON或物理参数。

## 1. 更新代码与选择构建

在现有项目仓库根目录执行，保留全部旧数据。以下002只是新名字；若已有则换003等，禁止清理重用。先完成更新，之后不要在mesh与solve之间更新HEAD。

```bash
if git fetch origin && git switch feat/research-plan-smoke-benchmark && git pull --ff-only; then
    git rev-parse HEAD
else
    printf 'STOP: code update failed; do not proceed.\n'
fi
of2512
```

如果已有构建summary的project_commit恰等于当前HEAD且状态通过，可用其原目录；否则保持现有严格版本契约，用新报告构建，可复用wmake缓存。构建时间不计入S预算，不改优化等级，不自动升级环境。

```bash
if bash scripts/validate_build.sh --jobs 8 --report-dir validation/threeD-smoke-002/build; then
    printf 'BUILD passed; verify summary before preparation.\n'
else
    rc=$?; printf 'STOP: build failed (%s); retain build.stdout-stderr.txt.\n' "$rc"
fi
```

每段失败都先停止，不继续下一段；命令使用if捕获，避免set-e交互终端被比较器非零返回码关闭。

## 2. 准备并只运行mesh

```bash
if python3 scripts/prepare_smoke_case.py \
    --run-dir runs/threeD-smoke-002 \
    --build-dir validation/threeD-smoke-002/build \
    --solver laserbeamFoam --accept-proposed-config; then
    printf 'Prepared only; no CFD has run.\n'
else
    rc=$?; printf 'STOP: preparation failed (%s).\n' "$rc"
fi
```

```bash
if [[ ! -e runs/threeD-smoke-002/time.workflow.mesh.txt && ! -L runs/threeD-smoke-002/time.workflow.mesh.txt ]] && \
    LC_ALL=C /usr/bin/time -v -o runs/threeD-smoke-002/time.workflow.mesh.txt \
    bash runs/threeD-smoke-002/Allrun mesh; then
    cat runs/threeD-smoke-002/log.checkMesh
    cat runs/threeD-smoke-002/log.setFields
else
    rc=$?; printf 'STOP: mesh/initialization failed (%s); retain case/logs.\n' "$rc"
fi
```

确认blockMesh/checkMesh/setFields退出0，Mesh OK，网格2048且三维，setFields实际设置金属区域，无Fatal/NaN及.mesh-complete，再继续。若不确定，先回传这一步，**不要启动solve**。源码推测不能代替此确认。

## 3. mesh通过后，单独solve

```bash
if [[ ! -e runs/threeD-smoke-002/time.workflow.solve.txt && ! -L runs/threeD-smoke-002/time.workflow.solve.txt ]] && \
    LC_ALL=C /usr/bin/time -v -o runs/threeD-smoke-002/time.workflow.solve.txt \
    bash runs/threeD-smoke-002/Allrun solve; then
    cat runs/threeD-smoke-002/smoke.txt
else
    rc=$?; printf 'STOP: solve/check failed (%s); inspect solver log/exit/time.\n' "$rc"
fi
```

外层GNU time在Allrun返回后才写完；因此再运行一次**纯离线**检查，汇入完整wrapper计时，不重跑CFD：

```bash
if python3 scripts/check_smoke_case.py --case-dir runs/threeD-smoke-002; then
    cat runs/threeD-smoke-002/smoke.txt
else
    rc=$?; printf 'Offline report status is non-PASS (%s); retain smoke.txt/json.\n' "$rc"
fi
```

离线命令更新smoke.txt/json；需要保存先前报告时先备份。不会写计算场。运行中或缺少外层计时则整体预算UNVERIFIED；不会把它伪装为通过。

## 报告字段与预算口径

- 实际初始化完成标记、网格数、正常End/退出、10步与终时；全部必要场和其他写出顶层场的解析/有限值/尺寸，显式边界及uniform。
- T与alpha/Deposition范围；仅alpha>0.5金属主导单元的最高T/液相率，避免把气相的液相率当成金属已经熔化。
- path_evidence：日志中激光名称/种子数、VOF、温度/压力和液相迭代诊断、正沉积。缺少某类证据如实报告；没记录反射事件不能据正沉积宣布多次反射被验证。
- resources：每阶段GNU time墙钟和最大RSS（KiB），solver是否约120秒内；有完整外层计时后，另给“准备主体+mesh wrapper+solve wrapper”的预算状态。它包括各wrapper内前置检查，不包括Git/编译/人工等待、准备Python启动和最后离线重报。不能用solver一项替代整个测量范围。
- 超过约2分钟是预算证据，不自动降低数值要求，也不把数值通过改成物理失败；反之快并不证明物理有效。

默认mesh每步骤180秒、solver120秒，准备时可用 --mesh-timeout / --solver-timeout 显式配置并记录；超时和预算目标是两件事。内存当前只测RSS，没有强制上限，不假定GPU存在或需要GPU。

## 最小回传

先mesh：log.checkMesh、log.setFields、exit.blockMesh/checkMesh/setFields.txt、相应time记录和网格数。失败补首个阶段日志，不清理。

solve后：smoke.txt/json、solver.exit.txt、time.laserbeamFoam.txt、time.workflow.mesh/solve.txt、preparation.time.txt；如日志/字段不支持或异常，再给log.laserbeamFoam及具体错误路径。输入/构建/工具SHA按manifest原记录，公开回传先脱敏；完整manifest有私有路径，不直接上传GitHub。

**SMOKE_CHECKS_PASSED只代表本探针的运行/基本数值检查；不代表物理精度、稳态熔池、网格收敛、MPI或AI效果。** 未收到用户实测前不追加成功实验记录。
