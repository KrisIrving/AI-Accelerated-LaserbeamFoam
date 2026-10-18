# Ubuntu 本机 Codex CFD 自动化实证

2026-10-17（Asia/Shanghai）；阶段1、DEC-008授权。结论：**LOCAL_CODEX_CFD_AUTOMATION_VERIFIED**。本次由Codex直接执行真实OpenFOAM构建、网格、初始化、唯一一次求解、检查、归档及GitHub同步；没有要求负责人手动运行命令。该结论仅验证本次S流程，不等于物理准确性、网格收敛或AI加速。

## 版本、环境与范围

- PR #4批准时远端HEAD：a5f53b9158871f363a669c16a2a1a631103674b9；分支feat/threeD-progressive-m-exploration。
- 先追加DEC-008并提交，再构建/准备/求解：源码、构建、工具SHA均为07496d15d1eebcb99f618d148a54af3729210669。后续证据文档提交不是运行SHA。
- Ubuntu22.04.5 LTS，OpenFOAM.com v2512，linux64GccDPInt32Opt，GCC11.4.0；48物理核/96逻辑CPU，RAM约93.026 GiB，所在盘可用约2.8 TiB。实际挂载与任务书路径不同，采用会话提供的现有空工作目录，不创建替代挂载或覆盖文件；绝对路径和主机名仅保留本地。
- 安全克隆时利用本机既有仓库的完整Git对象独立复制，再向GitHub fetch核对HEAD；没有复制旧运行数据。新checkout初始干净。HTTPS缺少终端凭据，已用本机现有SSH认证同步，无安装或账号配置要求。
- 原版laserbeamFoam，现有S配置16×8×16=2048单元，dt=1e-8 s，10步至1e-7 s。串行rank1、数值库线程1，mesh/solve wrapper限制CPU亲和为单逻辑CPU；solver墙钟120 s护栏，唯一一次尝试，无重试/续算/其他CFD。
- 新目录：runs/local-codex-S-20261017-001及validation/local-codex-S-20261017-001。原始网格/场、日志、清单、环境、安装、反馈包均留本地且被Git忽略。构建使用现有validate_build.sh允许的8作业；构建并行不代表求解并行。
- 与批准时HEAD相比，src、applications、tutorials、scripts、benchmarks和Allwmake的受跟踪内容完全未变；未改原版物理、容差、配置或既有实验。

## 真实执行与检查

隔离Allwmake退出0，BUILD_ARTIFACT_CHECKS_PASSED；所有预期程序和库存在。mesh和solve入口分别核对当前HEAD、manifest、输入、初始化快照、二进制/库哈希及实际ldd来源，项目库来自新隔离安装。

blockMesh/checkMesh/setFields/solver全部退出0；2048个六面体，5632内部面，3个有效几何/计算方向，Mesh OK；setFields选中1280/2048金属单元。solver正常End，实际10步、终时1e-7 s；SMOKE_CHECKS_PASSED，19个写出场的解析/有限性/尺寸/边界及既有检查通过，173个已识别日志事件，issues=[]。

既有S检查器对uniform/cumulativeContErr采用BYTE_IDENTICAL自比较回退，不能把该项称为严格语义检查。本轮额外调用现有check_m_case.parse_uniform_dimensioned_scalar只读检查新S原文件：class/object正确，七个量纲指数均0，value=8.641891144171712e-10且有限，PASS；未修改S工具或标准。补查记录单独保留本地，不声称它已经收入先前反馈包。

终态T范围约300–330.293282 K，alpha范围约3.743e-74至1，Deposition最大7.280627354225065e14 W/m³。金属主导单元最高T=330.293282 K、液相率0；MELTING_NOT_OBSERVED。五束激光、各150种子/次、正沉积、VOF、温度/压力求解有记录。多次反射、实验准确性、性能热点和AI收益均未建立。

## 实测成本

| 范围 | 墙钟 / s | GNU time 最大RSS / KiB |
| --- | --- | --- |
| 隔离Allwmake，8作业 | 185.44 | 1230492 |
| blockMesh | 0.08 | 66816 |
| checkMesh | 0.06 | 67584 |
| setFields | 0.06 | 70656 |
| 原版solver | 0.36 | 126568 |
| mesh wrapper，含子阶段 | 0.46 | 70656 |
| solve wrapper，含solver及检查 | 1.24 | 126568 |
| 最终显式离线检查及反馈导出 | 0.61 | 20736 |

已记录“准备主体+mesh wrapper+solve wrapper”范围为1.875943304 s，RECORDED_SCOPE_WITHIN_TARGET；不与子阶段重复相加。排除Git、构建、阶段间审阅/等待、准备Python启动和最终离线检查。没有把所有会话活动伪装成约2秒端到端耗时。构建RSS是GNU time记录的最大进程值，不是同时所有编译进程RSS之和。

原始输入、初始化、网格、终态57个文件共1163232 bytes；采集时整个案例普通文件合计1276402 bytes（含日志/报告/反馈），不含validation构建和源码对象。不将磁盘字节数等同于内存。solver最大RSS约123.6 MiB；没有内存硬限额。

## 反馈归档与哈希

反馈包threeD-smoke-feedback.20261017T121903Z.5a055feb3a9143e998ab753f13b1f3fa.tar.gz，11240 bytes，仅本地保存。archive_status=EXPORTED、collection_status=COMPLETE、timing_status=RECORDED_SCOPE、provenance_status=RECORDS_MATCH；missing_required=[]、omitted={}。直接重开核验23个普通文件、22条内部SHA256和FILES清单，无重复、链接或越界条目。归档哈希针对脱敏包，原场清单哈希另记。

| 对象 | SHA256 |
| --- | --- |
| 反馈tar.gz | 78573716e1c99ff20fe3320bd8454c61eea5f4db2e0bd3c1fb729f749ec0c58c |
| 原版solver二进制 | a1d2649731aed36967aea5dbd0320ec84626e33c520205dfa73d7e5bbee6795e |
| 准备输入哈希清单 | e38ef0d96da9dff3204196655cff41ec8cf7edd9f5279e75345304986c4dd339 |
| 初始化哈希清单 | 37963ab9de053e3f82b64fc4af61e692d96da2bc245a892a0c02e2c04b80c876 |
| 原始输入/网格/输出57文件清单 | da7c9496ba3a434ff85c4e1ac7f30ef03f65fa05fc9e3ed77682cb982d6a3e95 |

更多关键指标和项目库哈希见[脱敏JSON摘要](local-codex-S-20261017-summary.json)。没有提交原始日志、manifest、环境报告、网格、场、二进制、归档或个人绝对路径。

## 科学研究衔接与交付边界

另一个本机既有工作区存在M1/M3/M1-IC原场、网格和旧报告，RAW_DATA_PRESENT；本轮仅清点、读取已有报告并核验旧诊断归档，ORIGINAL_FIELD_NUMERICAL_REAUDIT_NOT_PERFORMED。没有虚构缺失数据或重新运行旧CFD；亦未重新认证全部原场历史不变。

[静态源码审查及下一项科学验证](../research/ALPHA_DEPOSITION_STATIC_REVIEW.md)保留M1/M3早期沉积错层和M1-IC未复现M3的结论，区分体积分数守恒与alpha>=0.5射线资格。推荐下一项为复用已有原场的只读初态/早期阈值资格审计，先一个时刻，核对0.5附近浮点值、法向门槛、已有沉积层与射线首遇位置；不新增CFD。本轮未执行该后续任务。

[DEC-008](../research/DECISION_LOG.md)与[EXP-004](../research/EXPERIMENT_LOG.md)追加记录；通过[PR #4](https://github.com/KrisIrving/AI-Accelerated-LaserbeamFoam/pull/4)现有开发分支交付。PR继续Draft，不合并；阶段1仍IN_PROGRESS、正式M仍PROPOSED，研究路线和历史记录保留。

交付前检查：72个本地导航目标存在，DECISION_LOG/EXPERIMENT_LOG相对批准时HEAD保持追加，脱敏内容/空白检查通过，57文件原始快照在采集后复查哈希未变，公开JSON与实际报告一致，受保护代码/配置路径无差异。此次只有研究记录和摘要变更，未新增或重跑合成测试；数值证据来自上述真实求解与现有检查。
