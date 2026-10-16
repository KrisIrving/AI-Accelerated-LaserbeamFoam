# M1 离线复核与条件性 M3 准备

授权与限制见[DEC-006](../research/DECISION_LOG.md)；完整执行惯例见[M 探索说明](THREED_M_EXPLORATION.md)。本页只更新检查工具、复核已有结果并在条件满足后准备 M3。**不重跑 M1，不在本轮启动 M2/M3 CFD，不改变正式阶段或基准。**

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

格式依据是官方v2512的[UniformDimensionedField.C](https://gitlab.com/openfoam/core/openfoam/-/blob/OpenFOAM-v2512/src/OpenFOAM/fields/UniformDimensionedFields/UniformDimensionedField.C)和[initContinuityErrs.H](https://gitlab.com/openfoam/core/openfoam/-/blob/OpenFOAM-v2512/src/finiteVolume/cfdTools/general/include/initContinuityErrs.H)：前者写出`dimensions`/`value`，后者声明`cumulativeContErr`、`uniform`目录、`dimless`及`AUTO_WRITE`。以下是源码派生的合成格式，**不是从本次归档读取的真实字段**；实际class由旧报告确认，原文件的object/量纲/value仍须工作站检查。

```text
FoamFile { version 2.0; format ascii;
           class uniformDimensionedScalarField; object cumulativeContErr; }
dimensions [0 0 0 0 0 0 0];
value -1.25e-12;
```

检查器严格支持七个有限数值量纲指数及单个有限标量；此状态必须无量纲、对象名匹配文件名且每个输出时刻存在。未知语法/附加项继续REVIEW_REQUIRED，错误声明、缺少状态或非有限值FAIL；符号单位语法未支持。不使用与自身字节相同比较代替语义验证。

## 2. 备份、全时刻复核并导出反馈

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

## 3. M3 版本与资源预检，仅准备

仅在上述真实 M1 复核 PASS、快照一致、资源记录完整后执行。M2暂缓。M3沿用已授权的256000单元、1000步、固定 dt=1e-8 s、终时10微秒；不调功率、材料、方程或容差来改善高温。新构建可能产生不同二进制，源码相同不能代替二进制一致性证明。

先在**交互终端**执行 `of2512`，然后以下单块只做源码差异核查、隔离构建与案例准备。目录必须全新；冲突就换新编号，不能清理旧目录。构建可复用 wmake 缓存但须生成匹配当前 HEAD 的新记录，使用8个编译作业；它会耗费CPU及磁盘，不执行CFD。

```bash
if bash <<'BASH'
set -euo pipefail
git diff --exit-code 1d32b6fda86d730b8e18b1d9f50e1752fffa5416 HEAD -- applications src Allwmake
git diff --quiet HEAD -- applications src scripts benchmarks
git rev-parse HEAD
free -h
df -h .
bash scripts/validate_build.sh --jobs 8 --report-dir validation/threeD-m3-001/build
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

准备器会重新执行M1的完整离线检查并更新其报告；之后M3每次mesh/solve的前置检查也会复核M1。它不重跑M1求解，但有额外检查成本，因此先保留第2节备份，不把这部分成本计入求解器或AI收益。输入和初始化哈希仍必须通过；资源失败不使用force绕过。

M1实测214.50秒、240452 KiB RSS、121054926字节，按现有预检的网格量×8情景：M3求解约1716秒（28.6分钟）、RSS约1.83 GiB、数据约0.902 GiB。这只是比例情景，细网格CFL、非线性及I/O可能使成本超线性增长。3600秒是求解器墙钟护栏；8 GiB RSS/3 GiB数据为 MONITORED_ONLY，非运行时强制上限。当前可用磁盘至少须满足3 GiB预检，并保留旧M1和构建的空间；检查当时可用内存并避免竞争负载。`free`/`df`输出仅供本地查看，不要求公开主机路径。

准备成功不代表M3运行通过；后续由用户按[M探索说明](THREED_M_EXPLORATION.md)分别执行mesh、审阅初始化、再单独solve及离线归档，不自动串跑。M1/M3是同物理时间的空间敏感性探索，不能由两级网格宣布收敛或物理精度。

## 检查成本与物理观察的解释

代码审计确认每个物理场当前被读取/解析3次、内部数组展开3次；网格owner/neighbour各解析2次，日志有完整检查及事件提取两轮。对归档内真实4.95 MB日志的Windows本地带剖析解析约2.26秒；合成32000单元标量场验证了3次调用。这不构成Ubuntu约95.90秒检查耗时的真实热点排名，也未实现或测得工具提速。完整原场未提供时，保留语义范围，待相同离线案例剖析后再决定单次检查内缓存。

`mixed_cells_count` 的原定义为严格数学区间0<alpha<1，可能包含接近端点的数值尾迹，不能直接解释为可分辨界面体积。新增较窄区间观察值只帮助解释，不改变数值验收门槛。熔化、高于案例汽化温度、阈值区域层数、显著界面运动与多次反射必须分别记录；当前没有独立实验、收敛、热点或AI加速证明。
