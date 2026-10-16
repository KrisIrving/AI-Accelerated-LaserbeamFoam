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

外层GNU time在Allrun返回后才写完；因此再显式运行一次**纯离线**检查和反馈导出，汇入完整wrapper计时，不重跑CFD。若要保留已有smoke.txt/json，先备份（下方另有复用002的完整说明）：

```bash
if python3 scripts/check_smoke_case.py --case-dir runs/threeD-smoke-002 --feedback-bundle; then
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

**SMOKE_CHECKS_PASSED只代表本探针的运行/基本数值检查；不代表物理精度、稳态熔池、网格收敛、MPI或AI效果。** 本轮已按用户实测摘要登记[EXP-001](../research/EXPERIMENT_LOG.md)，原始归档未交给Codex，完整SHA待补；未据此批准M。

## 复用现有002：一次离线检查并导出反馈

本节仅用于已经完成mesh/solve的`runs/threeD-smoke-002/`。不再运行Allrun、编译、初始化或更改计算场；离线工具读取原manifest，不要求其版本等于修复工具后的HEAD。实际构建/求解版本从原记录提取，缺失时保留UNVERIFIED / PROVENANCE_PENDING，不能补写当前HEAD。新建案例时的严格构建匹配契约不变。

在仓库根目录更新PR #3分支，更新失败先停止：

```bash
if git fetch origin && git switch feat/research-plan-smoke-benchmark && git pull --ff-only; then
    git rev-parse HEAD
else
    printf 'STOP: code update failed; retain existing results.\n'
fi
```

覆盖旧smoke报告前建议备份。该操作只复制旧报告，使用全新目录；失败先停止，不删除或清理原结果：

```bash
python3 - <<'PY'
from pathlib import Path
import shutil
import uuid
case = Path('runs/threeD-smoke-002')
backup = case / ('report-backup.' + uuid.uuid4().hex)
backup.mkdir()
for name in ('smoke.txt', 'smoke.json'):
    source = case / name
    if source.is_symlink():
        raise SystemExit('STOP: symlinked report: ' + name)
    if source.is_file():
        shutil.copy2(source, backup / name)
print('Saved previous reports:', backup)
PY
```

之后显式离线检查并导出。使用if捕获非零码，适用于已启用set-e的交互终端：

```bash
if python3 scripts/check_smoke_case.py \
    --case-dir runs/threeD-smoke-002 --feedback-bundle; then
    check_rc=0
else
    check_rc=$?
fi
printf 'Offline check exit: %s (0=smoke pass, 1=FAIL, 2=REVIEW_REQUIRED)\n' "$check_rc"
```

stdout给出归档**绝对路径及字节数**，位于`runs/threeD-smoke-002/feedback/threeD-smoke-feedback.<UTC+UUID>.tar.gz`，每次唯一，不覆盖旧包。同目录生成`.files.txt`清单和归档`.sha256`校验文件；可在feedback目录执行`sha256sum -c <对应文件>.sha256`。不自动上传。

`Allrun solve`内部检查仍不默认打包；最终归档必须等外层solve计时结束后显式生成。归档内`bundle.json`分别记录检查状态/退出码、导出状态、收集完整性和计时完整性。缺失/未完整写出的外层计时或准备计时标`INCOMPLETE_TIMING`，不改变原数值检查结果。完整只指当前白名单和记录范围，不包含编译、Git、人工等待或本次离线检查本身。

若求解失败或只有mesh日志，可独立导出现有证据，不检查场、不运行CFD、不改旧smoke报告：

```bash
if python3 scripts/export_smoke_feedback.py \
    --case-dir runs/threeD-smoke-002 --diagnostics-only; then
    printf 'Diagnostic archive exported; original check may still be FAIL or unknown.\n'
else
    export_rc=$?; printf 'Archive FAILED (%s); keep original diagnostics locally.\n' "$export_rc"
fi
```

独立导出命令退出0仅表示打包成功；保存的检查状态不变，缺少smoke.json则UNVERIFIED，按报告推得的检查退出码注明INFERRED_FROM_SAVED_REPORT，非本次检查结果。联合命令始终返回原检查码：即使数值PASS而归档失败仍返回0，并明确输出`archive_status=FAILED`；因此上传前还须确认归档导出成功，不能仅看shell退出码。打包失败不能把FAIL/REVIEW_REQUIRED变成PASS。

白名单仅包括smoke报告、solver.exit/time、preparation.time、mesh/solve外层计时、blockMesh/checkMesh/setFields及两种支持求解器的log/exit/time。不存在的文件列为缺失，异常/过大/非文本/符号链接文件列为omitted，收集状态PARTIAL；不将部分包说成完整反馈。单文件上限4 MiB、文本总量16 MiB、压缩包8 MiB；超过归档上限则导出失败，无有效归档交付。

不递归收集0、时间目录、polyMesh、processor或VTK，不打包原manifest/build summary。`provenance.json`只取必要配置与原记录版本，交叉检查源/构建SHA；它不重新认证已执行二进制。build summary丢失或移出本仓库validation时不探测其他目录，记录缺口；config哈希为规范化JSON哈希，不代替输入文件哈希。工具版本为smoke-feedback-v1。

归档使用脱敏副本：尽力移除绝对路径、用户名/主机提示及IP，原日志不改；打包后会重新打开并核对内容。内含`FILES.txt`与`SHA256SUMS`（后者覆盖其余归档文件，不自校验），哈希针对**归档中的脱敏字节**。脱敏不是匿名性保证，上传ChatGPT前请查看包内文本；不要将包或原日志自动提交公开GitHub。若失败，先回传smoke状态、bundle.json中的omitted/missing_required及首个问题，不必上传原始场。
