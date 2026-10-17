# M1 离线复核与条件性 M3 准备

最新状态（2026-10-17）：M3已由用户运行并检查PASS，见[EXP-003](../research/EXPERIMENT_LOG.md)。**已有M1/M3不要重跑本页CFD指令**；当前下一步是[原场只读空间比较](M1_M3_SPATIAL_COMPARISON.md)。以下保留为首次运行操作参考，不代表需要再次执行。

授权与限制见[DEC-006](../research/DECISION_LOG.md)；完整执行惯例见[M 探索说明](THREED_M_EXPLORATION.md)。2026-10-17已收到M1修复后实机PASS，来源及边界见[EXP-002-ADD-01](../research/EXPERIMENT_LOG.md)。**M1无需重跑；M2暂缓；下列M3构建、准备、mesh、solve由用户分阶段执行，Codex/CI不启动真实CFD。** 不改变正式阶段、基准或检查标准。

## 1. 更新工具，不重新编译 M1

在仓库根目录执行。每块失败后停止，不继续下一块；不要在交互终端直接启用 `set -e`。下文以原目录 `runs/threeD-M1-001` 为例，实际名称不同时先调整。

```bash
if git fetch origin &&
   git switch feat/threeD-progressive-m-exploration &&
   git pull --ff-only; then
    git rev-parse HEAD
else
    rc=$?; printf 'STOP: update failed (%s); preserve existing results.\n' "$rc"
fi
```

原运行/构建提交保持 `1d32b6fda86d730b8e18b1d9f50e1752fffa5416`。离线复核允许读取旧 manifest，不要求它等于新工具 HEAD；不能编辑旧构建记录或用新工具版本替代原运行版本。

格式依据是官方v2512的[UniformDimensionedField.C](https://gitlab.com/openfoam/core/openfoam/-/blob/OpenFOAM-v2512/src/OpenFOAM/fields/UniformDimensionedFields/UniformDimensionedField.C)和[initContinuityErrs.H](https://gitlab.com/openfoam/core/openfoam/-/blob/OpenFOAM-v2512/src/finiteVolume/cfdTools/general/include/initContinuityErrs.H)：前者写出`dimensions`/`value`，后者声明`cumulativeContErr`、`uniform`目录、`dimless`及`AUTO_WRITE`。以下是源码派生的合成格式，**不是从归档读取的原始字段**。现已回传10个状态语义解析PASS、量纲全0且value有限；Codex未直接读取原字段。

```text
FoamFile { version 2.0; format ascii;
           class uniformDimensionedScalarField; object cumulativeContErr; }
dimensions [0 0 0 0 0 0 0];
value -1.25e-12;
```

检查器严格支持七个有限数值量纲指数及单个有限标量；此状态必须无量纲、对象名匹配文件名且每个输出时刻存在。未知语法/附加项继续REVIEW_REQUIRED，错误声明、缺少状态或非有限值FAIL；符号单位语法未支持。不使用与自身字节相同比较代替语义验证。

## 2. M1复核历史命令：当前无需重复执行

本节保留用于未来确有需要时的复查，当前M1已PASS，直接进入第3节。新反馈包未包含前后SHA快照，不能把本节示例当作已经执行或独立证明原场未变。

下面的单块命令先建立唯一备份，保存旧报告、检查工具提交及原生时间目录的 SHA256 快照；再运行离线检查和归档；最后重新计算快照。它不调用 OpenFOAM，不写原生场。SHA 快照包含 `0` 和全部非负数值时间目录内的文件及路径，包括嵌套 `uniform`。

```bash
if python3 - <<'PY'
import hashlib
import json
import math
import re
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path

case = Path("runs/threeD-M1-001").absolute()
if not case.is_dir() or any(p.is_symlink() for p in (case, *case.parents)):
    raise SystemExit("STOP: missing/symlinked case")
number = re.compile(r"[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")

def snapshot():
    result = {}
    roots = []
    for root in sorted(case.iterdir()):
        if not number.fullmatch(root.name) or not math.isfinite(float(root.name)):
            continue
        if root.is_symlink() or not root.is_dir():
            raise SystemExit("STOP: invalid time directory " + root.name)
        roots.append(root.name)
        result[root.name + "/"] = "DIRECTORY"
        for path in sorted(root.rglob("*")):
            mode = path.lstat().st_mode
            relative = path.relative_to(case).as_posix()
            if stat.S_ISDIR(mode):
                result[relative + "/"] = "DIRECTORY"
            elif stat.S_ISREG(mode):
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                result[relative] = digest.hexdigest()
            else:
                raise SystemExit("STOP: linked/special output " + relative)
    if "0/" not in result or not any(float(name) > 0 for name in roots):
        raise SystemExit("STOP: missing initial/output time trees")
    return result

before = snapshot()
backup = case / ("report-backup.M1-recheck." + uuid.uuid4().hex)
backup.mkdir()
for name in ("m.txt", "m.json", "observations.csv", "execution_times.csv", "mesh-summary.json"):
    path = case / name
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP: missing/nonregular old report " + name)
    shutil.copy2(path, backup / name)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
(backup / "checker-commit.txt").write_text(head + "\n", encoding="ascii")
(backup / "raw.before.json").write_text(json.dumps(before, indent=2) + "\n")
print("Backup:", backup, flush=True)
checked = subprocess.run([sys.executable, "scripts/check_m_case.py",
                          "--case-dir", str(case), "--feedback-bundle"], check=False)
after = snapshot()
(backup / "raw.after.json").write_text(json.dumps(after, indent=2) + "\n")
if before != after:
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    raise SystemExit("STOP: raw result changes during recheck: " + ", ".join(changed[:5]))
print("RAW_RESULTS_UNCHANGED_DURING_RECHECK; checker commit:", head)
raise SystemExit(checked.returncode)
PY
then
    check_rc=0
else
    check_rc=$?
fi
printf 'Offline wrapper exit: %s (checker: 0=PASS, 1=FAIL, 2=REVIEW_REQUIRED).\n' "$check_rc"
```

备份/快照步骤自身失败也可能返回1，须按明确的 `STOP` 原因处理。快照只能证明**本次复核期间**原始时间树没有变化，不能追溯证明自原运行结束后从未被改动。原归档和历史 REVIEW_REQUIRED 记录保留；新报告只代表当前检查工具的复核。

预期检查全部10时刻、190个物理场文件及各时刻的边界和 `uniform/cumulativeContErr`。只有真实返回 `EXPLORATION_CHECKS_PASSED` 才补录通过；不能提前宣称。另确认导出显示 `Archive: EXPORTED`，以及所需内容完整；导出失败不会改变检查器退出码。新归档在原案例的 `feedback/`，路径和大小由工具打印，唯一命名不覆盖旧包。上传前审阅脱敏文本，回传新归档及其 SHA256；不上传原生场到公开仓库。

## 3. M3版本、资源、隔离构建与准备

M1实机PASS前提已由用户回传；当前本地报告仍须满足原有准备器检查，原场及历史报告保留。没有随包提供快照，不独立认证历史或复核期间未变。M2暂缓。M3沿用已授权的256000单元、1000步、固定dt=1e-8 s、终时10微秒；不调功率、材料、方程或容差。新构建可能产生不同二进制，源码相同不能代替二进制一致性证明。

先在**交互终端**执行 `of2512`，然后以下单块只做源码差异核查、隔离构建与案例准备。目录必须全新；冲突就换新编号，不能清理旧目录。构建可复用 wmake 缓存但须生成匹配当前 HEAD 的新记录，使用8个编译作业；它会耗费CPU及磁盘，不执行CFD。

```bash
if bash <<'BASH'
set -euo pipefail
git diff --exit-code 1d32b6fda86d730b8e18b1d9f50e1752fffa5416 HEAD -- applications src Allwmake
git diff --quiet HEAD -- applications src scripts benchmarks
git rev-parse HEAD
free -h
df -h .
[[ ! -e validation/threeD-m3-001/build && ! -L validation/threeD-m3-001/build ]]
[[ ! -e runs/threeD-M3-001 && ! -L runs/threeD-M3-001 ]]
m1=runs/threeD-M1-001
backup=$(mktemp -d "$m1/report-backup.before-M3.XXXXXXXX")
cp -- "$m1"/{m.txt,m.json,observations.csv,execution_times.csv,mesh-summary.json} "$backup/"
git rev-parse HEAD > "$backup/m3-preparation-tool-commit.txt"
printf 'M1 reports preserved: %s\n' "$backup"
bash scripts/validate_build.sh --jobs 8 --report-dir validation/threeD-m3-001/build
cat validation/threeD-m3-001/build/summary.txt
python3 scripts/prepare_m_case.py --experiment M3 \
    --run-dir runs/threeD-M3-001 --build-dir validation/threeD-m3-001/build \
    --m1-case-dir runs/threeD-M1-001 \
    --reason 'Assess spatial resolution of M1 single-layer melt region at equal physical times'
cat runs/threeD-M3-001/preflight.json
BASH
then
    printf 'M3 prepared only. Inspect preflight/build records; no CFD started.\n'
else
    rc=$?; printf 'STOP: source/build/resource/conditional check failed (%s).\n' "$rc"
fi
```

准备器会重新执行M1的完整离线检查并更新其报告；之后M3每次mesh/solve的前置检查也会复核M1。这是原有安全契约，不重跑M1的1000步CFD；先用上面的唯一备份保留已验收报告/归档，不需另外再执行第2节。每次M1离线检查约96秒的已有记录不能承诺新耗时，不把它计入solver或AI收益。输入和初始化哈希仍必须通过；资源失败不使用force绕过。

M1实测214.50秒、240452 KiB RSS、121054926字节，按现有预检的网格量×8情景：M3求解约1716秒（28.6分钟）、RSS约1.83 GiB、数据约0.902 GiB。这只是比例情景，细网格CFL、非线性及I/O可能使成本超线性增长。3600秒是求解器墙钟护栏；8 GiB RSS/3 GiB数据为 MONITORED_ONLY，非运行时强制上限。当前可用磁盘至少须满足3 GiB预检，并保留旧M1和构建的空间；检查当时可用内存并避免竞争负载。`free`/`df`输出仅供本地查看，不要求公开主机路径。

确认构建摘要为`BUILD_ARTIFACT_CHECKS_PASSED`、v2512及预期`WM_OPTIONS`，project_commit等于当前HEAD；准备器完成条件性M1检查、磁盘检查并输出`PREPARATION_PASSED`。实际二进制和同名库来源继续由原有哈希/ldd检查验证。不在准备与mesh/solve之间更新HEAD；若目录已占用，整套换新编号，不删除或续算。

## 4. 用户执行M3 mesh，审阅后才solve

以下每块均在仓库根目录执行。第3节成功且本地资源可用后，先单独mesh：

```bash
if [[ ! -e runs/threeD-M3-001/time.workflow.mesh.txt && ! -L runs/threeD-M3-001/time.workflow.mesh.txt ]] &&
   LC_ALL=C /usr/bin/time -v -o runs/threeD-M3-001/time.workflow.mesh.txt \
   bash runs/threeD-M3-001/Allrun mesh; then
    cat runs/threeD-M3-001/log.checkMesh
    cat runs/threeD-M3-001/log.setFields
    cat runs/threeD-M3-001/mesh-check.txt
else
    rc=$?; printf 'STOP: M3 mesh/initialization failed (%s); retain case/logs.\n' "$rc"
fi
```

只有确认256000个三维六面体单元、Mesh OK、setFields成功、5个必要初场检查及`MESH_INITIALIZATION_CHECKS_PASSED`，并存在`.mesh-complete`，才启动下一块。M3金属单元数不套用M1的20800；用自己的初场建立金属体积参考。

```bash
if [[ ! -e runs/threeD-M3-001/time.workflow.solve.txt && ! -L runs/threeD-M3-001/time.workflow.solve.txt ]] &&
   LC_ALL=C /usr/bin/time -v -o runs/threeD-M3-001/time.workflow.solve.txt \
   bash runs/threeD-M3-001/Allrun solve; then
    solve_rc=0
else
    solve_rc=$?
fi
printf 'M3 solve/check exit: %s; retain all results if nonzero.\n' "$solve_rc"
```

原版laserbeamFoam串行、计算线程1；原生solver墙钟护栏3600秒，TERM后10秒kill宽限。前置M1复核和M3离线检查在该solver护栏之外，外层工作流可能更长；8 GiB RSS/3 GiB数据仍为MONITORED_ONLY。超时或数值失败保留现场，不重试、不改dt、不续算。求解退出0不自动等同后续检查PASS。

## 5. 外层计时完成后，离线检查并打包

不重跑CFD。下列块保留已有M3报告（如有），重新检查全部预期时刻并生成唯一命名归档，安全捕获1/2退出码；检查和导出状态分别审阅。

```bash
if bash <<'BASH'
set -euo pipefail
m3=runs/threeD-M3-001
backup=$(mktemp -d "$m3/report-backup.before-export.XXXXXXXX")
for name in m.txt m.json observations.csv execution_times.csv mesh-summary.json; do
    if [[ -f $m3/$name && ! -L $m3/$name ]]; then
        cp -- "$m3/$name" "$backup/"
    fi
done
git rev-parse HEAD > "$backup/checker-commit.txt"
if python3 scripts/check_m_case.py --case-dir "$m3" --feedback-bundle; then
    check_rc=0
else
    check_rc=$?
fi
printf 'M3 offline exit: %s (0=PASS, 1=FAIL, 2=REVIEW_REQUIRED).\n' "$check_rc"
exit "$check_rc"
BASH
then
    printf 'Inspect EXPLORATION_CHECKS_PASSED and separate archive completeness.\n'
else
    rc=$?; printf 'M3 offline/backup failed (%s); inspect printed cause and preserve logs.\n' "$rc"
fi
```

预期1000步至1e-5 s、10个输出时刻；检查所有实际字段及必要字段的internal/boundary有限性、尺寸、体积分数和uniform状态，不预先承诺恰有190个文件。`EXPLORATION_CHECKS_PASSED`且issues为空才记基础数值检查通过。另核对`Archive: EXPORTED`、collection完整；打包成功不能改变FAIL/REVIEW_REQUIRED。

回传唯一新反馈tar.gz及SHA256（工具打印路径），必要时附同名`.export.json`，以及本次构建/工具完整SHA。失败时优先m.txt/json首个具体问题；构建失败返回`build.stdout-stderr.txt`和summary，mesh失败返回log.checkMesh/log.setFields及mesh-check，求解失败返回solver.exit、log.laserbeamFoam和阶段time。原生场/完整主机信息不公开上传，已有归档均保留。

M1/M3比较同物理时刻的T、金属速度/液相体积、阈值区域y层数、沉积、体积分数及资源范围，输出层数/中心跨度不直接当实验熔深。两级网格只做空间敏感性探索，不宣称网格收敛、物理准确性或AI性能。阶段1仍未完成。

## 检查成本与物理观察的解释

代码审计确认每个物理场当前被读取/解析3次、内部数组展开3次；网格owner/neighbour各解析2次，日志有完整检查及事件提取两轮。对归档内真实4.95 MB日志的Windows本地带剖析解析约2.26秒；合成32000单元标量场验证了3次调用。这不构成Ubuntu约95.90秒检查耗时的真实热点排名，也未实现或测得工具提速。完整原场未提供时，保留语义范围，待相同离线案例剖析后再决定单次检查内缓存。

`mixed_cells_count` 的原定义为严格数学区间0<alpha<1，可能包含接近端点的数值尾迹，不能直接解释为可分辨界面体积。新增较窄区间观察值只帮助解释，不改变数值验收门槛。熔化、高于案例汽化温度、阈值区域层数、显著界面运动与多次反射必须分别记录；当前没有独立实验、收敛、热点或AI加速证明。
