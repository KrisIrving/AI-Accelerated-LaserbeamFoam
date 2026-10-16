# 实验记录（追加）

原始日志/场保留在忽略的 runs/、validation/；公开记录不包含主机私有路径、完整环境或大数据。更正用追加条目链接旧ID，不覆盖历史。

## EXP-000 — Plate2D串行A/B（历史用户证据）

- 状态：USER_REPORTED_PASS；本轮未重跑。
- 求解器：laserbeamFoam / aiLaserbeamFoam，无AI。比较器baeb8107；原运行/构建commit待原manifest和summary补录。
- 环境：OpenFOAM.com v2512，linux64GccDPInt32Opt；串行；案例Plate2D-ab-002。
- 规模/时间：3200单元，10步，0至1e-7，最终输出1e-7。
- 证据：30/30场语义及边界、263日志事件、21输入/5网格、uniform全部通过，Issues=0；已比较误差0；atol1e-12/rtol1e-10。
- 墙钟：该次完整A/B计时未提供，UNVERIFIED；不挪用此前单次原版0.67秒作为这次性能基线。
- 结论：串行重命名数值等价；物理精度/MPI/AI性能未验证。原始结果保留。

## 后续追加模板

- 实验ID/日期/状态（PLANNED、RUNNING、PASS、FAIL、REVIEW_REQUIRED）：
- 问题/可否决假设及所属批准阶段/决策：
- 源码commit、构建commit、比较/采集工具commit、dirty状态：
- 求解器/开关/共享库和依赖来源：
- OpenFOAM、WM_OPTIONS、编译优化：
- 案例配置版本/输入哈希/网格量/网格质量：
- dt、实际步数、终止时间和全部输出时刻：
- 资源（进程、线程、CPU亲和、内存预算；公开记录去隐私）：
- 初始化/推进/I/O/整体计时、最大RSS、重复次数和波动：
- 性能工具/权限/采样设置/采集本身开销：
- 数值/物理检查、原版差异、误差/守恒/失败或回退：
- 日志索引（仓库相对路径，不上传大数据）：
- 结论、局限、下一步候选；是否需要批准计划变更：
