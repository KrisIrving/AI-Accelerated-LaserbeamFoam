# 官方案例的隔离短程验证

> 历史操作备忘录：2026-10-16负责人已取消固定MPI矩阵及其LPBF前置条件。本页旧的4/8进程顺序不是当前必经计划；以[正式计划](../research/DEVELOPMENT_PLAN.md)和[基准设计](../research/BENCHMARK_DESIGN.md)为准，勿将旧命令当作本轮执行要求。

本页只规定原版求解器的首次运行检查，不是物理验证、收敛研究或性能基准。静态核对对象为上游提交 `3c93f2657e089e22e9a8298648292969e85a4bad`。**尚未在 OpenFOAM 实机执行，以下步骤不能视为已经通过。** 不修改 `tutorials/`、求解器源码或物性字典；运行仅发生在新副本中。

## 1. 首例选择与官方脚本行为

网格数来自各案例 `system/blockMeshDict` 的有效块，而非目录名称。

| 案例 | 有效块划分 | 预期初始单元数 | 准备与选择 |
| --- | --- | ---: | --- |
| `tutorials/laserbeamFoam/Plate2D` | `(1 40 80)` | 3,200 | **首例**：复制 `initial`，`blockMesh`，`setFields`；无需 DEM、颗粒映射或网格旋转 |
| `tutorials/laserbeamFoam/checkReflections` | `(40 40 80)` | 128,000 | 后续光学检查；不是最小例，默认光线参数 `nRadial=50`、`nAngular=180` |
| `tutorials/laserbeamFoam/LPBF_small` | `(40 60 80)` | 192,000 | 后续三维粉床例；复用已有 `constant/location`，需要 `setSolidFraction` 与旋转 |

`Plate2D` 的 `(1 160 320)` 行已被注释，不能用它计算当前网格数。该例为薄层二维设置，不能用于宣称三维 LPBF 正确或并行可扩展。

官方脚本只供核对，不直接运行：

- `Plate2D/Allrun` 与 `checkReflections/Allrun` 均复制 `initial` 到 `0`，依次调用 `blockMesh`、`setFields`、`laserbeamFoam`，不会自动缩短计算。原始 `endTime` 分别为 `0.01`、`0.9` 秒。
- `LPBF_small/Allrun` 复制初始场；如果 PATH 中有 `liggghts`，**会自动运行 `DEM_small/Allrun` 并重新生成布局**；随后执行 `blockMesh`、`setSolidFraction -subDivisions 6`、`transformPoints -rotate '((0 1 0) (0 0 1))'`，再求解。传入 `parallel` 时还执行分解、并行求解及重构；其原始分解设置是 32 进程，不能直接当作本机配置。
- `Plate2D/Allclean`、`checkReflections/Allclean` 会调用 `cleanCase`，并删除 `0`、`VTKs`。`LPBF_small/Allclean` 还会调用 DEM 清理脚本，删除 DEM 日志和 `post`。**本流程不调用任何 `Allclean`，不自动删除失败副本。**

`checkReflections` 和 `LPBF_small` 的 `controlDict/application` 保留了旧求解器名字；官方 `Allrun` 实际明确运行 `laserbeamFoam`。下文同样明确调用该可执行文件，不通过 `application` 字段推断命令，也不借此修改物理输入。

## 2. 先检查 Ubuntu 工作站中的运行环境

以下是供用户在 **Ubuntu 22.04 交互式 Bash 终端**执行的命令。先进入工作站上本仓库根目录，按 `UBUNTU_2512.md` 加载 `of2512` 并选择本次隔离编译的安装。Codex 不连接工作站，也不在 Windows 中执行 OpenFOAM。

```bash
set -euo pipefail
export LBF_REPO="$(pwd -P)"
test -d "$LBF_REPO/tutorials/laserbeamFoam/Plate2D/initial"
test -n "${WM_PROJECT_DIR:-}"
for tool in blockMesh checkMesh setFields foamDictionary laserbeamFoam timeout; do
    command -v "$tool"
done
test -x /usr/bin/time
/usr/bin/time --version
timeout --version
```

要求 `/usr/bin/time` 支持 GNU `-v`，`timeout` 来自 GNU coreutils。工具缺失时先解决环境或编译，不用其他同名软件替代。OpenFOAM 版本和动态库环境应与构建记录一致；这里不自行选择另一套安装。

## 3. 创建拒绝覆盖的首个串行副本

每次尝试使用新的目录名。下面的 `mkdir` 本身也会在目标已存在时失败，防止重复执行把 `initial` 嵌套复制到旧 `0` 中。

```bash
export LBF_SOURCE="$LBF_REPO/tutorials/laserbeamFoam/Plate2D"
export LBF_RUN_ROOT="$LBF_REPO/runs/official-smoke"
export LBF_CASE="$LBF_RUN_ROOT/Plate2D-serial-001"
test -d "$LBF_SOURCE/initial"
test ! -e "$LBF_SOURCE/0"
test ! -e "$LBF_SOURCE/constant/polyMesh"
if [[ -e "$LBF_CASE" || -L "$LBF_CASE" ]]; then
    printf '拒绝覆盖已有目标：%s\n' "$LBF_CASE" >&2
    exit 1
fi
mkdir -p -- "$LBF_RUN_ROOT"
mkdir -- "$LBF_CASE"
cp -a -- "$LBF_SOURCE/." "$LBF_CASE/"
cd -- "$LBF_CASE"
mkdir logs
cp -a -- initial 0
cp -- system/controlDict logs/controlDict.upstream
{
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    printf 'case=%s\nmpi_ranks=1\nexpected_cells=3200\n' "$LBF_CASE"
    printf 'WM_PROJECT_VERSION=%s\nWM_OPTIONS=%s\n' \
        "${WM_PROJECT_VERSION:-unset}" "${WM_OPTIONS:-unset}"
    git -C "$LBF_REPO" rev-parse HEAD
    uname -srmo
    command -v laserbeamFoam
    /usr/bin/time --version
    timeout --version
} > logs/environment.txt 2>&1
```

如果来源目录已经有运行产物，停止并核对来源；不要调用清理脚本来绕过检查。记录源码提交时还应结合构建日志确认当前可执行文件确由该提交编译。

## 4. 逐步记录退出码、计时与短程设置

在刚创建的副本中定义以下函数。每条命令单独保存 stdout/stderr、GNU time 记录、命令及退出码；不会通过管道丢掉求解器退出码。若一步失败或超时，立即停留在失败现场。

```bash
run_logged() {
    local tag="$1" budget="$2"
    shift 2
    local prefix="logs/$tag" rc
    if [[ -e "$prefix.log" || -e "$prefix.time" || -e "$prefix.exit" ]]; then
        printf '拒绝覆盖已有步骤日志：%s\n' "$prefix" >&2
        return 1
    fi
    printf '%q ' "$@" > "$prefix.command"
    printf '\n' >> "$prefix.command"
    if /usr/bin/time -v -o "$prefix.time" \
        timeout --signal=TERM --kill-after=10s "$budget" "$@" \
        > "$prefix.log" 2>&1; then
        rc=0
    else
        rc=$?
    fi
    printf '%s\n' "$rc" > "$prefix.exit"
    if [[ "$rc" -ne 0 ]]; then
        printf '步骤 %s 失败，退出码 %s；检查 %s.log\n' "$tag" "$rc" "$prefix" >&2
        return "$rc"
    fi
}

set_control() {
    run_logged "control-$1" 30s \
        foamDictionary system/controlDict -entry "$1" -set "$2"
}

set_control startFrom startTime
set_control startTime 0
set_control stopAt endTime
set_control deltaT 1e-8
set_control maxDeltaT 1e-8
set_control adjustTimeStep no
set_control endTime 1e-7
set_control writeControl timeStep
set_control writeInterval 10
set_control runTimeModifiable no
run_logged control-readback 30s foamDictionary system/controlDict
```

只修改**副本**的 `controlDict`：固定 `deltaT=10^-8 s`，从 0 到 `10^-7 s`，预期 10 个物理时间步。这里没有虚构 `maxSteps` 命令行选项；最大步数由固定步长和终止时间约束，并须用实际日志核对。该短程只检查启动与推进，不代表已经形成熔池。若求解器实际没有遵循固定步长，停止调查，不延长终止时间。

首轮保持官方的网格、物性、边界、热源、离散格式和求解容差不变；极小固定步长也不是稳定性的证明。读取失败时保留日志，不能为了让算例运行而静默修改这些字典。

## 5. 首次仅运行串行

```bash
run_logged blockMesh 120s blockMesh
run_logged checkMesh 120s checkMesh
run_logged setFields 120s setFields
run_logged laserbeamFoam 120s laserbeamFoam
awk '/^Time = / { n++ } END { print "observed_steps=" n+0 }' \
    logs/laserbeamFoam.log > logs/observed-steps.txt
```

`120s` 是每个步骤的墙钟上限，超时后最多再给 10 秒退出；正常超时常见退出码为 124，升级到强制结束时也可能为 137。必须保留原始退出码，不能把它归类为“通过”。单步内部迭代卡住仍由该墙钟限制终止。

运行后逐项记录：

- `blockMesh`/`checkMesh` 报告的实际单元数是否为 3,200；网格检查是否成功。
- 求解器是否正常结束，是否实际推进了 10 步、到达预期终止时间，是否有 Fatal Error、NaN、异常温度、VOF 越界或明显不收敛；有限体积求解器允许的正常容差必须结合日志判断。
- 各步骤 `.exit`，`.time` 中的 elapsed wall-clock、user/system CPU time、maximum resident set size，及 CPU、可用内存、OpenFOAM 版本和 MPI 数。GNU time 的最大 RSS 是该命令报告的进程资源指标，不能在并行时直接当成各 rank 内存之和。
- 保留 `0/`、最终时间目录、所有日志及原始 `controlDict`，失败也不清理。退出码为零只代表程序结束，不等同物理验证。

## 6. 串行通过之后才安排 4 / 8 进程

这是后续步骤，本轮首例不启动 MPI。分别从**同一个原版来源**创建 `Plate2D-mpi4-001`、`Plate2D-mpi8-001` 新副本，重复上文拒绝覆盖、初场、短程控制、网格、`checkMesh`、`setFields`；不能复制已经跑完的串行目录或带 `processor*` 的旧目录。

每个新副本各自记录 `mpi_ranks`。原版 `Plate2D` 是 `method simple`，4 进程划分 `(1 2 2)`；8 进程可用 `(1 2 4)`，保持单层方向不分解。仅在各自副本内修改分解字典，并单独保存修改记录：

```bash
# 4 进程副本（8 进程副本将 4 改为 8，n 改为 (1 2 4)）
run_logged decomp-count 30s foamDictionary system/decomposeParDict \
    -entry numberOfSubdomains -set 4
run_logged decomp-shape 30s foamDictionary system/decomposeParDict \
    -entry simpleCoeffs -set '{ n (1 2 2); }'
run_logged decomp-readback 30s foamDictionary system/decomposeParDict
run_logged decomposePar 120s decomposePar
run_logged laserbeamFoam-mpi4 120s mpirun -np 4 laserbeamFoam -parallel
run_logged reconstructPar 120s reconstructPar
```

8 进程命令相应使用 `mpirun -np 8` 和不同日志名。MPI 的可执行文件与库必须匹配构建环境；资源不足则不运行，不加入超额分配或 root 绕过选项。并行结果应与串行在相同输出时刻比较；3,200 单元仅适合 MPI 功能检查，不适合测强扩展或声称加速。

## 7. 后续条件步骤：复用官方 LPBF 粒子布局

只有首例串行及必要的 MPI 检查完成后，才另建 `LPBF_small-serial-001`。沿用相同的新目录拒绝覆盖和记录规则；**不执行顶层或 DEM 的 `Allrun`，不安装/调用 LIGGGHTS 来重建粉床**。

已核对的依赖与顺序：

1. 来源为 `tutorials/laserbeamFoam/LPBF_small`，`initial/alpha.metal` 初始值为零；必须从新副本复制一次到 `0`。
2. 布局为 `constant/location`，当前文件声明 **47 个粒子**。实现在第 4 行读数量，跳过 9 行头后按 `x y z radius` 四列读取；不是任意 CSV，也不是 `DEM_small/post/location` 直接被求解器读取。保存该文件的哈希和行数，并核对声明数量与四列有效数据行一致。
3. `system/bedPlateDict` 是 `setSolidFraction` 的必读字典；当前 `Bed true`、`zmax=0.0001`。映射还需要 `blockMesh` 生成的网格及已复制的初始场，不依赖 DEM 可执行文件。
4. 在**旋转之前**执行官方的 `setSolidFraction -subDivisions 6`，再执行官方旋转 `transformPoints -rotate '((0 1 0) (0 0 1))'`。`-subDivisions` 控制每个单元方向的采样数（6³），不会增加 CFD 网格单元数。当前块为均匀 2.5 微米立方体；不得在此流程自行修改网格。
5. 工具会读取已有 `alpha.metal`，粉粒区域采用累加赋值；**不能在同一初场上重复调用**，也不能重复旋转网格。失败后保留副本，用新名字重建。

完成相同的短程 `controlDict` 设置、确认 `setSolidFraction` 与 `transformPoints` 均来自本次编译环境后，在 LPBF 新副本中采用以下准备顺序；不要运行 `setFields` 来覆盖粉床映射：

```bash
command -v setSolidFraction
command -v transformPoints
test -s constant/location
test -s system/bedPlateDict
sha256sum constant/location > logs/location.sha256
run_logged blockMesh 120s blockMesh
run_logged setSolidFraction 300s setSolidFraction -subDivisions 6
run_logged transformPoints 120s transformPoints -rotate '((0 1 0) (0 0 1))'
run_logged checkMesh 120s checkMesh
# 上述检查及初场检查通过后，另行决定是否执行：
# run_logged laserbeamFoam 120s laserbeamFoam
```

实际单元数应由旋转后的 `checkMesh` 确认为 192,000；先检查金属体积分数范围及基板/粉粒方向，再进行有墙钟限制的短程求解。`setSolidFraction` 的实机可用性、初场正确性和 LPBF 求解均仍待验证。原版 LPBF 终止时间为 `100e-6 s`，本页不自动运行该完整算例。
