# 第一轮反馈：私下回传，不提交到公开 GitHub

请先发小文本摘要，必要时再发日志。环境审计做了路径掩码，但原始编译、OpenFOAM和GNU time日志可能含用户名、路径和主机名，请自行审阅。不要附加 `env` 全量输出、SSH配置、凭证、IP或仿真场文件。

新增入口的串行 A/B 请按 [PLATE2D_AB.md](PLATE2D_AB.md) 回传两组日志及 `comparison.txt/json`，不要只发其中一个程序的成功信息。原生 `98f99de8` 通过记录见 [RESULTS.md](RESULTS.md)。

复制下列格式为私有 `feedback.txt`：

```text
project_commit: (git rev-parse HEAD)
upstream_baseline: 3c93f2657e089e22e9a8298648292969e85a4bad
ubuntu/openfoam/WM_OPTIONS:
stage: audit | build | Plate2D-serial | Plate2D-4 | Plate2D-8
command:
exit_code:
mpi_ranks:
cells:
elapsed_wall_seconds:
maximum_resident_kib:
last_completed_simulation_time:
observed_status: failed | preparation_passed | short_run_passed
first_error_and_log_name:
notes:
numerical_accuracy: UNVERIFIED
```

CPU单核 GNU time 的 `Maximum resident set size` 可作为该次进程资源记录。MPI启动器的该值不能当作全部进程总内存；4/8核阶段应分别记录启动器指标及适当的进程级测量，并明确是否测得总量。本轮不据此得出并行加速结论。

## 按阶段返回

- **审计**：`audit_host.txt`。脚本不写文件；重定向写入用户自己选择的本地目录。
- **编译**：`build/summary.txt`、`build/build.stdout-stderr.txt`、`build/time.Allwmake.txt`；失败时加 `build/source-logs/`、`build/build-error-matches.txt`，链接问题加相应 `build/ldd.*.txt`。归档子日志名为 `log.Allwmake.txt`，不可改回确切名字 `log.Allwmake`。
- **首例**：案例 `feedback.txt`、所用 `system/controlDict`、`logs/blockMesh.log`、`logs/checkMesh.log`、`logs/setFields.log`、`logs/laserbeamFoam.log`、`logs/observed-steps.txt` 以及 `logs/<tag>.time`、`.exit`、`.command`；命令失败时发对应日志和真实退出码，不继续运行后续命令。

## 可选小包

在仓库根目录，以下步骤仅复制明确的文本日志，不自动收集场文件；目的目录和压缩包都已忽略。`REPORT_DIR` 指向本轮目录。案例日志按需手动复制到 `feedback-stage/`，不要复制整个案例目录。

```bash
FEEDBACK_DIR=$(mktemp -d "$PWD/validation/feedback.XXXXXXXX")
cp "$REPORT_DIR/audit_host.txt" "$FEEDBACK_DIR/"
if [ -d "$REPORT_DIR/build" ]; then
    mkdir "$FEEDBACK_DIR/build"
    find "$REPORT_DIR/build" -type f -name '*.txt' -print0 |
    while IFS= read -r -d '' f; do
        rel=${f#"$REPORT_DIR/build/"}
        mkdir -p "$FEEDBACK_DIR/build/$(dirname "$rel")"
        cp "$f" "$FEEDBACK_DIR/build/$rel"
    done
fi
du -sh "$FEEDBACK_DIR"
# 先审阅上述文本，再执行；不会上传任何文件。
tar -czf "${FEEDBACK_DIR}.tar.gz" -C "$FEEDBACK_DIR" .
```

数据较大时优先发送摘要和首个错误附近日志；不要通过 GitHub issue/PR 上传主机报告。提交者只在确认反馈后更新“编译通过/运行通过”状态，不把短跑升级为数值或实验验证。
