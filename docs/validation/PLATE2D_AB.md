# Plate2D：原版与新求解器入口的串行 A/B 检查

本轮 A 为 `laserbeamFoam`，B 为 `aiLaserbeamFoam`。**B 当前只新增命名隔离的求解器入口，没有学习模型、AI 控制或加速算法。** 目的仅是检查新增入口是否保持原版行为，为以后独立开发建立回归基线；不能据此宣称 AI 加速、物理验证通过或三维 LPBF 可用。

用户已回传 `fa039e70` 两个程序编译通过。旧 `Plate2D-ab-001/A` 在输入清单行序比较处退出，尚未调用 OpenFOAM；保留整个旧目录作为证据。修复统一 C locale，并按相对路径与 SHA256 的完整对应关系核验，不要求原始清单行序相同。下述新报告、新案例仍遵守构建记录与当前 Git HEAD 一致的要求；重新调用 `Allwmake` 可使用现有对象缓存，不运行清理，也不复制旧二进制冒充本次构建。

以下步骤供用户在 Ubuntu 22.04 工作站的交互式 Bash 中运行。编译、案例运行及比较结果均待实机回传；本页不承诺通过。不使用 MPI，不执行 DEM，不运行官方长算例。报告保留本机，公开提交中不放主机信息、用户绝对路径或计算场数据。

## 1. 同次构建、同套库

先取得包含本功能的源码，进入其仓库根目录。用户先加载 `of2512`，成功后再启用严格检查；脚本不自行加载其他 OpenFOAM 安装。原版环境审计与依赖要求见 [UBUNTU_2512.md](UBUNTU_2512.md)。

```bash
of2512
set -euo pipefail
test "${WM_PROJECT_VERSION:-}" = v2512
test -n "${WM_OPTIONS:-}"
test -f scripts/prepare_plate2d_ab.sh
test -f scripts/compare_plate2d_ab.py
export AB_REPO="$(pwd -P)"
mkdir -p validation
REPORT_DIR=$(mktemp -d "$PWD/validation/plate2d-ab.XXXXXXXX")
bash scripts/audit_host.sh --repo "$PWD" --disk "$PWD" \
    > "$REPORT_DIR/audit_host.txt"
bash scripts/validate_build.sh --report-dir "$REPORT_DIR/build" --jobs 8
```

构建失败时停止并保存报告，不调用清理、不覆盖原安装、不用 PATH 中旧程序代替缺失产物。新目录中的两个求解器必须来自本次同一源码、OpenFOAM 版本、`WM_OPTIONS` 和构建环境；本次构建必须实际产出两个程序并通过各自产物检查，不能只看上游构建的退出码。

构建摘要与日志经检查后，在同一终端选择这次隔离安装：

```bash
source "$REPORT_DIR/build/env.sh"
hash -r
export AB_BUILD_DIR="$(realpath "$REPORT_DIR/build")"
test -x "$AB_BUILD_DIR/install/bin/laserbeamFoam"
test -x "$AB_BUILD_DIR/install/bin/aiLaserbeamFoam"
test "$(command -v laserbeamFoam)" = "$AB_BUILD_DIR/install/bin/laserbeamFoam"
test "$(command -v aiLaserbeamFoam)" = "$AB_BUILD_DIR/install/bin/aiLaserbeamFoam"
grep -Fx "WM_OPTIONS=$WM_OPTIONS" "$AB_BUILD_DIR/summary.txt"
command -v python3
```

检查 `build/binary.sha256`、`build/custom-libraries.sha256`、`build/dependencies.laserbeamFoam.tsv`、`build/dependencies.aiLaserbeamFoam.tsv` 及对应 `ldd.<solver>.txt`：记录各二进制及其依赖库的哈希与来源；两者使用同一套本次 `install/lib` 中的自定义库，OpenFOAM 系统库来自同一已加载安装，不能出现 `not found` 或回落到以前用户安装的同名自定义库。两个求解器二进制哈希可以不同，不要求二进制本身相同。

`env.sh` 将本次库目录放到 `LD_LIBRARY_PATH` 前部；不要在 A、B 之间重新加载其他安装、替换库或重新编译。若重开终端，先加载同版本环境，再重新设置既有 `REPORT_DIR`、`AB_REPO`、`AB_BUILD_DIR` 并 source 本次 `env.sh`，不新建或覆盖旧报告。

## 2. 一次准备两个全新副本

准备命令只生成配置与运行脚本，不启动 CFD。`--run-dir` 必须不存在；失败或已有结果时换新的末尾编号，不删除、清理或复用旧目录。

```bash
cd -- "$AB_REPO"
export AB_RUN_DIR="$PWD/runs/Plate2D-ab-002"
test ! -e "$AB_RUN_DIR"
test ! -L "$AB_RUN_DIR"
bash scripts/prepare_plate2d_ab.sh \
    --run-dir "$AB_RUN_DIR" --build-dir "$AB_BUILD_DIR"
```

来源为原版 `tutorials/laserbeamFoam/Plate2D`。`blockMeshDict` 的有效块为 `(1 40 80)`，预期 3,200 个单元；注释中的其他划分不计入。此时 A、B 都不应已有 `0`、演化时间目录或 `constant/polyMesh`。初场由各自 `Allrun` 从同一份 `initial` 复制，不能从另一组最终结果启动。

核对根目录 `manifest.txt` 与两组 `inputs.sha256`：除运行入口、`controlDict/application` 及本地溯源记录外，物理输入保持一致。尤其 `initial`、`constant`、网格、离散格式、求解容差和初场设置应相同；不能把减少迭代容差或改变物理参数混入 B。

```bash
test ! -e "$AB_RUN_DIR/A/0"
test ! -e "$AB_RUN_DIR/B/0"
test ! -e "$AB_RUN_DIR/A/constant/polyMesh"
test ! -e "$AB_RUN_DIR/B/constant/polyMesh"
diff -ru -- "$AB_RUN_DIR/A/initial" "$AB_RUN_DIR/B/initial"
diff -ru -- "$AB_RUN_DIR/A/constant" "$AB_RUN_DIR/B/constant"
```

两组 `controlDict` 均应固定 `deltaT=1e-8 s`、`adjustTimeStep no`、`startTime=0`、`endTime=1e-7 s`，预期 10 步；采用 ASCII 输出、`writePrecision=17` 并在一致时刻写场。A 的 `application` 为 `laserbeamFoam`，B 为 `aiLaserbeamFoam`。检查时保留该预期差异，不能要求两个 `controlDict` 原始字节完全相同。

## 3. 用户依次运行 A、B

环境保持不变，先 A 后 B。每组 `Allrun` 使用 OpenFOAM `RunFunctions` 依次执行 `blockMesh`、`checkMesh`、`setFields`，随后通过 GNU time 与 timeout 明确调用相应求解器，保存资源和退出码。不要用官方 `Allrun` 覆盖生成脚本。

```bash
(cd -- "$AB_RUN_DIR/A" && bash ./Allrun --strict)
(cd -- "$AB_RUN_DIR/B" && bash ./Allrun --strict)
```

首组失败就停止，不继续把第二组或比较结果当作有效对照。每组检查：

普通 `Allrun` 保留环境、指定程序及库来源、全新目录、输入完整性和失败报告检查。正式 A/B 使用上面的 `--strict`，额外核对 Git 提交/源码状态、全量程序和自定义库哈希及完整动态依赖来源。准备阶段始终要求构建记录与 HEAD 一致；严格校验没有被绕过。A/B 跨案例输入及结果比较仍由独立比较器完成。

所有清单均在 C locale 下生成；输入辅助脚本另对完整记录按路径规范排序后比较，保留 `sha256sum -c`。清单重新排列可通过；改内容、丢文件、额外文件或重复记录均失败。不要手动重写哈希以使失败案例通过。

| 证据 | A | B |
| --- | --- | --- |
| 准备日志 | `log.blockMesh`、`log.checkMesh`、`log.setFields` | 同名日志 |
| 求解日志 | `log.laserbeamFoam` | `log.aiLaserbeamFoam` |
| 求解资源与退出码 | `solver.time.txt`、`solver.exit.txt` | 同名文件 |

检查实际网格是否均为 3,200 单元、边界及初始场是否一致，两个求解器是否都从零推进至相同终点、完成 10 步并正常结束。求解程序的墙钟限制为 120 秒，收到终止信号后最多再给 10 秒退出；该限制不是整个准备流程的总时间。超时、非零退出码或日志中的异常都需保留现场，不能改成“通过”。资源记录包括 GNU time 的 elapsed wall-clock、CPU 时间和最大 RSS。本轮只有串行短跑，启动与输出开销占比可能很大，时间差不构成加速结论。

前置失败会在终端报告 `ERROR [阶段] 原因`。需要保留终端输出时可用 `(cd "$AB_RUN_DIR/A" && bash ./Allrun --strict) 2>&1 | tee "$AB_RUN_DIR/A/allrun.console.txt"`；B 同理。当前终端已启用 `pipefail`，`tee` 不会掩盖失败。输入错误先回传该输出及 `inputs.verify.txt`、`inputs.runtime.diff.txt`；库错误先回传 `ldd.runtime.txt` 和 `dependencies.runtime*.tsv`。OpenFOAM 准备工具失败回传对应 `log.<工具>`；求解阶段失败回传求解日志和 `solver.exit.txt`。

两组 `Allclean` 仅提示并拒绝自动清理。不要通过它删除现场，也不要重复运行同一组 `Allrun` 来覆盖日志或演化场；重新试验应另建 A/B 根目录。

## 4. 比较原生输出，不重跑案例

`compare_plate2d_ab.py` 使用 Python 3 标准库，只读取结果与准备记录，不启动 OpenFOAM、不重建案例、不修正计算场。两组正常结束后执行，并保留比较器退出码：

若 `Plate2D-ab-002` 已完成，仅更新离线比较器即可复查，不重新编译、准备或运行 A/B。运行时的版本仍以原 `manifest.txt` 和构建记录为准，不要求等于比较器更新后的 Git HEAD。正常的完整 `trapFpe: Floating point exception trapping enabled (FOAM_SIGFPE).` 启动行不会当作异常；真实异常会记录 A/B、日志文件、行号及匹配原文。先在运行根目录中备份旧报告，再重新比较：

```bash
AB_REPO="$(pwd -P)"
AB_RUN_DIR="$PWD/runs/Plate2D-ab-002"
OLD_REPORTS=$(mktemp -d "$AB_RUN_DIR/comparison-before-fix.XXXXXXXX")
cp -- "$AB_RUN_DIR/comparison.txt" "$AB_RUN_DIR/comparison.json" "$OLD_REPORTS/"
```

下面的比较命令只更新 `comparison.txt/json`，保留输入、网格、原求解日志、manifest、场及 `uniform/` 字典；不修改容差来取得通过。

```bash
cd -- "$AB_REPO"
if python3 scripts/compare_plate2d_ab.py --run-dir "$AB_RUN_DIR" \
    --atol 1e-12 --rtol 1e-10; then
    AB_COMPARE_RC=0
else
    AB_COMPARE_RC=$?
fi
printf 'comparison_exit_code=%s\n' "$AB_COMPARE_RC"
cat "$AB_RUN_DIR/comparison.txt"
```

不要在交互式终端随后用 `test "$AB_COMPARE_RC" -eq 0` 或 `exit "$AB_COMPARE_RC"` 结束会话。上面的 `if` 保留比较器的0/1/2退出码，同时避免 `set -e` 因数值不通过而关闭终端；非零结果仍需调查。

查看根目录的 `comparison.json`、`comparison.txt`。比较范围包括输入与准备网格一致性、时间步和输出时刻、残差/迭代记录及连续性信息、体积分数范围，以及最终相同时刻的原生 ASCII 场数值。必需场为 `T`、`p_rgh`、`U`、`alpha.metal`、`epsilon1`、`Deposition`、`phi`；官方 Plate2D 启用了电磁场，因此也要求 `H`、`pH`、`B`、`J`、`Joulesource`、`JcrossB`。其他对应的自动写出场也应比较，不能只取两组文件的交集。标量、矢量和表面场的 `uniform`/`nonuniform` 表示先归一化，避免把等值的不同存储形式误判为不同解。相体积分数和连续性日志只作 A/B 对照，当前不计算独立的质量或热能闭合误差。

`PASS` 的退出码为0；缺少必需场、非有限值、非零求解退出码或超容差差异返回 **`FAIL`**（1）；无法支持的格式或无法确认的记录返回 **`REVIEW_REQUIRED`**（2）。两种非通过状态均需调查，不能跳过后假通过，也不自动等同物理模型故障。

首次比较优先检查是否逐位一致；上面的绝对/相对容差只用于发现和定位数值差异。即使差异很小且落在容差内，也先调查其来源，包括输入、库、编译选项、输出精度与计算顺序，不自动放宽容差来获得通过。若数据解析器能力不足，应修复比较方法或提交明确记录，不转换结果来掩盖差异。

数值统计中的 `exact_equal` 表示解析后的数值完全相等；文件级 `byte_identical` 表示原始字节完全相等，两者分别记录。所有对应输出时刻、全部自动写出场的集合、internalField 和 boundaryField 都要检查，不能只比较预选的13个文件。

`uniform/` 递归记录相对路径、目录（包括空目录）和文件类型，拒绝符号链接。已支持的原生字典与场使用 `NUMERICAL_SEMANTIC` 比较；未知状态文件只有原始字节一致时才可按 `BYTE_IDENTICAL` 明确通过，字节不同则要求审查。已知物理场不使用字节回退，非有限值和真实语义差异不能被字节相同掩盖。状态目录的问题会保留具体路径并继续比较物理场，不静默忽略 `functionObjects/`。

`surfaceScalarField` 额外支持顶层 `oriented oriented;`。属性必须为单个枚举词 `unknown`、`oriented` 或 `unoriented`，显式值不同返回 `FAIL`。其他未知顶层属性仍返回 `REVIEW_REQUIRED` 并列出名称和字段路径；体场等其他类没有新增属性白名单。方向属性一致后仍完整比较尺寸、内部/边界面数量、边界条件、有限值及数值，不能仅因文件字节一致就通过。

JSON 中 `fields/<time>/<name>/orientation` 分别记录 A/B 的 `present` 和 `value`。两侧均缺省时保留 `false/null`，不假定某个运行时方向值；一侧缺省另一侧显式时要求审查。依据：[v2512 orientedType.C](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2512/src/OpenFOAM/orientedType/orientedType.C) 的枚举表及 `read`/`writeEntry` 规定缺省读取为 UNKNOWN、仅 ORIENTED 写出条目；但 [DimensionedFieldIO.C](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2512/src/OpenFOAM/fields/DimensionedFields/DimensionedField/DimensionedFieldIO.C) 的 `readField` 允许保留构造时已有的 ORIENTED。离线比较器无法仅由缺省条目恢复这一构造上下文，因此不把缺省与显式枚举直接合并。比较器也不沿用枚举读取对非法词的 failsafe 回退。

简明文本报告增加实际时间步数、日志事件数、输入/网格文件数、输出时刻、物理场已比较/发现数量及状态、字节一致数、语义通过数、仅按字节通过数、uniform 嵌套目录状态，以及首个问题的相对路径。完整清单、所有问题及字段最大绝对/相对误差、L2误差仍在 JSON。文件数量按“对应文件对 × 输出时刻”计数；字节一致与语义通过可重叠，不能相加。`NOT_CHECKED` 表示该部分尚未检查，不表示通过。

只有总体 `PASS`、物理场及 uniform 均通过且没有待审查项，才可登记当前 Plate2D 串行短程的数值等价性；不外推到物理精度、收敛性、MPI、三维 LPBF 或 AI 加速。

## 5. 私下回传的最小证据

先回传源码 SHA、OpenFOAM/`WM_OPTIONS`、构建摘要、A/B 两组退出码、实际网格数、完成步数/终点、比较摘要及首个差异。需要时再补充 `manifest.txt`、二进制/依赖哈希记录、对应准备/求解日志、`solver.time.txt`、`solver.exit.txt` 和比较报告。

原始日志、`ldd` 和报告可能包含本机路径，分享前审阅。不要公开提交整个 `validation/`、`runs/`、全环境、用户路径、真实工作盘路径或全部计算场。只有收到实际证据后才更新“编译通过”或“短程 A/B 一致”的状态；数值收敛、物理正确性和净加速仍需后续独立验证。

以下可选命令仅收集明确的文本证据，不收集计算场，也不上传。若前面失败，可先回传首个错误及对应日志，再按实际存在的文件打包。

```bash
cd -- "$AB_REPO"
FEEDBACK_DIR=$(mktemp -d "$PWD/validation/ab-feedback.XXXXXXXX")
mkdir "$FEEDBACK_DIR/build" "$FEEDBACK_DIR/A" "$FEEDBACK_DIR/B"
for file in summary.txt build.stdout-stderr.txt time.Allwmake.txt \
    binary.sha256 custom-libraries.sha256 dependencies.ab.diff.txt \
    ldd.laserbeamFoam.txt ldd.aiLaserbeamFoam.txt \
    dependencies.laserbeamFoam.tsv dependencies.aiLaserbeamFoam.tsv; do
    test ! -f "$AB_BUILD_DIR/$file" || cp "$AB_BUILD_DIR/$file" "$FEEDBACK_DIR/build/"
done
for file in manifest.txt comparison.txt comparison.json; do
    test ! -f "$AB_RUN_DIR/$file" || cp "$AB_RUN_DIR/$file" "$FEEDBACK_DIR/"
done
for variant in A B; do
    for file in log.blockMesh log.checkMesh log.setFields \
        log.laserbeamFoam log.aiLaserbeamFoam solver.time.txt solver.exit.txt \
        observed-steps.txt execution.txt allrun.console.txt ldd.runtime.txt dependencies.runtime.tsv \
        inputs.verify.txt inputs.runtime.diff.txt \
        inputs.sha256 mesh.sha256; do
        test ! -f "$AB_RUN_DIR/$variant/$file" || \
            cp "$AB_RUN_DIR/$variant/$file" "$FEEDBACK_DIR/$variant/"
    done
done
du -sh "$FEEDBACK_DIR"
# 审阅目录中的本机路径及日志后再执行；压缩包仍只保存在本机。
tar -czf "${FEEDBACK_DIR}.tar.gz" -C "$FEEDBACK_DIR" .
```
