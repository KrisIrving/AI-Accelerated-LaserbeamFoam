# 保留的 MPI 审计资料

2026-10-16；审计源码 baeb8107；未运行MPI；本轮撤销矩阵不撤销风险。

- laserRayParticle.C 的 escapingInterface/escapeHops/escapeRedirects 为 move 局部状态，未随跨处理器粒子序列化。跨rank时状态不持久是源码事实；对具体案例数值影响尚未实测。
- 边界种子本地findCell归属未见逐射线唯一拥有者的全局断言；全局候选数不能代替实际粒子数。不同分解改变种子/求和顺序。
- 射线VTK段按rank顺序拼接不一定是路径行进顺序；该可视化不回流沉积计算。不可将跨分解ID差异直接归为物理错误。
- 原生Make/options链接libgeometricVoF，仓库libgeometricVoFLMFOAM不同名；以实际ldd确认。温度收敛和多个诊断使用全局归约，不等于所有模块已正确并行。
- v2512 RunFunctions 的 OpenMPI runParallel 自动 oversubscribe；有资源约束时不能照搬。reconstructPar 从processor0读取FV清单/复制uniform，必须另查各rank完成和输出。

今后修改通信、并行数据结构或射线迁移时做定向验证；实际运行故障须调查。旧仓库外审计报告保留，不清理。本文件保存其关键结论，避免依赖聊天记忆；不是MPI验收通过记录。
