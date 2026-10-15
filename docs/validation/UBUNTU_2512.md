# Ubuntu 22.04 / OpenFOAM.com v2512：首轮验证

本页保留首轮引导步骤。原生求解器在 `98f99de8` 的工作站编译与 Plate2D 串行短跑已由用户回传通过；`fa039e70` 的两个求解器也已编译通过，见 [RESULTS.md](RESULTS.md)。当前新增入口请改按 [PLATE2D_AB.md](PLATE2D_AB.md) 执行；实际运行与一致性尚未验证。官方源码和 `Allwmake` 不改动。

## 1. 新目录检出与只读审计（先做这一组）

在 **Ubuntu 的交互式 Bash 终端**执行。已有同名目录时 `git clone` 应失败；不要删除或覆盖旧安装，换一个新目录名。

```bash
of2512
set -euo pipefail
mkdir -p "$HOME/CFD"
cd "$HOME/CFD"
test ! -e AI-Accelerated-LaserbeamFoam
test ! -L AI-Accelerated-LaserbeamFoam
git clone --branch chore/bootstrap-ubuntu2512 https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam.git
cd AI-Accelerated-LaserbeamFoam
mkdir -p validation
REPORT_DIR=$(mktemp -d "$PWD/validation/round1.XXXXXXXX")
bash scripts/audit_host.sh --repo "$PWD" --disk "$PWD" > "$REPORT_DIR/audit_host.txt"
printf 'Local report directory: %s\n' "$REPORT_DIR"
```

`of2512` 由用户在交互式终端加载，失败时不要继续；在它加载后才开启 `set -u`，避免用户的环境加载函数受未定义变量检查干扰。脚本不调用 alias/function、不读取 shell 配置、不尝试加载其他版本。若用户希望核对既有 laserbeamFoam checkout，可另加 `--repo /明确的/旧源码目录`；不指定就不搜索。报告保留在本机，审阅后回传，不上传 GitHub。

若 `WM_PROJECT_VERSION` 不是 `v2512`、`wmake` 不可用或报告显示环境未加载，停止在此，回传审计。只审计不编译时不影响原有可执行文件。

## 2. 原版编译（审计环境正确后）

在同一个仓库根目录、同一个已加载 `of2512` 的终端执行，保留上节 `REPORT_DIR`：

```bash
bash scripts/validate_build.sh --report-dir "$REPORT_DIR/build" --jobs 8
```

这是显式编译操作，会使用最多8个编译作业并写入本 checkout 的对象文件与上游构建日志；不要同时启动其他构建。需要时可改为12，不直接使用48或无参数 `-j`。不运行 `Allwclean`。

若该命令失败且终端因 `set -e` 退出，重新开终端后只读取已生成的日志；不要直接重跑到同一个目录。默认报告目录已存在时脚本会拒绝覆盖。

封装只调用原版 `./Allwmake -j 8`，临时把 `FOAM_USER_APPBIN`、`FOAM_USER_LIBBIN` 指向该次报告目录下全新的 `install/bin` 和 `install/lib`，不覆盖以前用户目录中的安装。脚本退出不会永久改变父终端环境。源码目录下旧的 `log.Allwmake` 会被官方构建覆盖，但其本次副本保存在报告目录。

预期：`build/summary.txt` 记录本次 SHA、`WM_OPTIONS`、作业数、真实返回码及新安装产物。只有返回码、产物和动态依赖检查通过，才输出 `BUILD_ARTIFACT_CHECKS_PASSED`；仍必须查看日志，状态不代表案例运行或精度验证。上游有嵌套 `tee`，不能只看最后一行成功提示或 PATH 里的旧程序。

当前分支的完整构建会通过原版 `wmake all solvers` 自动发现 `aiLaserbeamFoam/Make/files`。验证封装要求两个独立可执行文件存在，记录其哈希，并检查两者自定义动态库均来自本次隔离安装、解析依赖来源一致。已有同名库在 `LD_LIBRARY_PATH` 后部并不作为正确来源的证据。

若只需单独构建某个入口，在已建立本次隔离库、并 source 对应 `env.sh` 后，可以使用标准命令 `wmake -j 8 applications/solvers/laserbeamFoam` 或 `wmake -j 8 applications/solvers/aiLaserbeamFoam`。这不会编译缺失的所有共享库；首轮 A/B 推荐完整 `Allwmake` 同次构建，不复制或重命名旧二进制。

完整输出为 `build/build.stdout-stderr.txt`；归档子日志以 `.txt` 结尾。不要把它们改名成 `log.Allwmake` 放在 checkout 内：官方构建会递归搜索这个确切名字，历史失败报告可能干扰下一次判断。

失败时保留整个 `build/` 中的文本日志，不清理、不重试不同优化参数，不把旧程序的可执行性作为本次成功证据。首个错误、编译器和 MPI 信息将决定是否需要最小兼容补丁。

## 3. 选择本次安装，再开始官方小例

仅在编译报告通过且日志已审查后：

```bash
source "$REPORT_DIR/build/env.sh"
hash -r
command -v laserbeamFoam
```

路径应是本次 `validation/round1.*/build/install/bin/laserbeamFoam`。之后按 [OFFICIAL_CASES.md](OFFICIAL_CASES.md) 创建一个**全新隔离副本**，先网格/初始场，再单核10步短跑；本轮不直接运行完整 `Allrun`，不执行 `Allclean`、DEM或长时段。

若重新开终端，先 `of2512`，再设置此前输出的 `REPORT_DIR`，再 `source` 本次 `env.sh`。不要仅凭旧 PATH 判断安装来源。

## 4. 反馈

按 [FEEDBACK.md](FEEDBACK.md) 回传审计、编译摘要和日志。原始日志可能含本机绝对路径，应先审阅；不公开提交。后续真实结果再更新兼容状态，静态检查、编译、短跑、数值收敛及实验验证分开记录。
