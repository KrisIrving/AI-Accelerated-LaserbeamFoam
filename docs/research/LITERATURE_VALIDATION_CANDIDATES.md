# 文献与实验验证候选库

检索日期：2026-10-16。**非受控候选研究记录；V1/V2均为PROPOSED，未批准为阶段、基准或验收门槛。** 不修改章程、阶段顺序、S/M定义或官方tutorials。本轮无真实S/实验复现运行。NOT_REPORTED指已查来源未给出该项；UNVERIFIED指尚未取得或核验，不等于实验没有测量。

## 判断与证据类型

暂推荐 **V1b：AMB2022-03 IN718单道热像/截面测量组的宽度与深度**，因工艺变体、原始显微图及分项不确定度可追溯；V1a：AMB2018-02 IN625是备选，须严格分AMMT/CBM、曝光批次和后续校准。V2用于更针对性的光学/熔池动力学审查，复现难度和模型适用性风险更高。排序以数据落地和材料输入补齐为条件，不是正式选型。

| 证据 | 比较对象 | 可以说明 | 不能替代 |
| --- | --- | --- | --- |
| A 代码/数值回归 | 同输入原版与AI入口 | 开发是否改变离散数值结果 | 物理准确性或AI加速 |
| B 物理实验验证 | 原版与实验可观测量 | 指定工况/误差/假设下的模型预测能力 | 端到端加速或所有物理过程 |
| C AI效果 | 同条件原版与新模块 | 耗时、数值/物理误差、稳定性、回退与净收益 | 仅网络推理快或在校准集拟合好 |

下面公开数据的“存在”由官方链接/论文数据声明确认；下载落地、版本和许可证另列状态，不能混淆。NIST PDR多页仅返回JavaScript加载外壳；小README/CSV的受限读取也超时，**未声称已下载/校验原始数据**，未下载大图像包。PDR界面版本1.15.7不是数据集版本。

## V1a — AMB2018-02 / IN625

论文：Brandon M. Lane, Jarred C. Heigel, Richard E. Ricker, Ivan Zhirnov, Vladimir Khromchenko, Jordan S. Weaver, Thien Q. Phan, Mark R. Stoudt, Sergey Mekhontsev, Lyle E. Levine (2020), *Measurements of Melt Pool Geometry and Cooling Rates of Individual Laser Traces on IN625 Bare Plates*, Integrating Materials and Manufacturing Innovation 9，DOI [10.1007/s40192-020-00169-1](https://doi.org/10.1007/s40192-020-00169-1)。[NIST书目](https://www.nist.gov/publications/measurements-melt-pool-geometry-and-cooling-rates-individual-laser-traces-in625-bare)、[可读全文](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=927485)。

| 项目 | 已核查事实、缺口与来源 |
| --- | --- |
| 实验/原始数据 | 有。CBM原始热像入口：[M31931](https://doi.org/10.18434/M31931)；AMMT截面原始显微图：[mds2-3830](https://doi.org/10.18434/mds2-3830)；具体机器/轨迹/曝光批次须配对，不能混成一次实验。[官方数据索引](https://www.nist.gov/ambench/direct-am-bench-data-links-and-referencing-guidance) |
| 下载/版本/许可 | 上述为官方DOI入口；文件下载、README修订、校验和及单项许可证UNVERIFIED。按DOI记录引用数据及Lane论文；不因NIST来源就填写CC0/GPL。正式使用前取得落地文件清单、版本、许可和访问日期。 |
| 材料与热物性 | 裸IN625，无粉末，厚度/粒径不适用；官方有制造商成分证书。成分证书不是完整rho/k(T)/cp(T)/潜热/黏度/表面张力/电阻率/光学输入，完整物性包UNVERIFIED。[实验说明](https://www.nist.gov/ambench/amb2018-02-description) |
| 标称与实测功率 | 编程A/B/C=150/195/195 W；AMMT修正实际137.9/179.2/179.2 W，对应400/800/1200 mm/s。CBM使用150/195/195 W，不套用AMMT校正。具体功率不确定度须从对应原记录补录，未填统一百分比。[修正说明](https://www.nist.gov/ambench/amb2018-02-description) |
| 光斑与分布 | 1070 nm，近Gaussian；后续修正AMMT D4σ=170 µm、FWHM约100 µm；CBM D4σ=100 µm、FWHM约59 µm。不能把直径填入laserRadius。[修正说明](https://www.nist.gov/ambench/amb2018-02-description)、Lane表3/4 |
| 轨迹/几何/初态 | 说明与论文使用14 mm扫描、0.5 mm间距、每道间隔至少5分钟，约25 °C；基板24.08×24.82×3.18 mm，销钉固定、有限接触散热。精确时间功率/轨迹及接触热边界仍需原始文件，不以恒定速度声明代替真实起停记录。[说明](https://www.nist.gov/ambench/amb2018-02-description) |
| 气氛/表面 | AMMT为Ar；CBM为N2，氧水平、表面处理及相应流场需保持分组。氧化/表面状态会涉及模型适用性，不能直接移植S的300K/气氛字典。[说明](https://www.nist.gov/ambench/amb2018-02-description) |
| 可比指标/不确定度 | 优先宽/深、匹配批次的熔池长度；长度按1290 °C固相线定义。Lane表5–7给分项、合成和k=2扩展不确定度；不同机器/批次不能用一个误差条。论文结论明确冷却速率仅exemplar，**不推荐作为模型参考或校准**；AMMT-100µs运动模糊使长度不宜替代20µs批次。见全文表3–7与结论。 |
| 来源冲突 | [截面网页](https://www.nist.gov/ambench/chal-amb2018-02-mp-xsection)仍有16 mm与旧图FWHM45 µm；与更新说明/2020论文存在冲突。不可拼接参数。正式复现前按样品ID/DOI README核对，未解决则该批次保持UNVERIFIED。 |
| 求解器适配/缺口 | 单道移动光束、相变/热毛细/反冲及射线有对应路径；须独立替换IN625物性、单激光/轨迹、边界和坐标。表面氧化、真实气流、接触传热及光学参数不自动表示。标定吸收率若需要，必须留出别的功率/速度条件独立验证。 |
| 成本/推荐 | 不是10步任务。14mm在400/800/1200mm/s下分别需35/17.5/11.67ms，仅为轨迹除法推算，外加冷却；墙钟UNVERIFIED。建议备选，以宽深优先，先解决批次/光斑冲突。 |

## V1b — AMB2022-03 / IN718

论文：Jordan S. Weaver, David Deisenroth, Sergey Mekhontsev, Brandon M. Lane, Lyle E. Levine, Ho Yeung (2024), *Cross-Sectional Melt Pool Geometry of Laser Scanned Tracks and Pads on Nickel Alloy 718 for the 2022 Additive Manufacturing Benchmark Challenges*, Integrating Materials and Manufacturing Innovation 13, 363–379，DOI [10.1007/s40192-024-00355-5](https://doi.org/10.1007/s40192-024-00355-5)。[NIST书目](https://www.nist.gov/publications/cross-sectional-melt-pool-geometry-laser-scanned-tracks-and-pads-nickel-alloy-718-2022)、[全文与不确定度附录](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=957295)。

| 项目 | 已核查事实、缺口与来源 |
| --- | --- |
| 实验/原始数据 | 有。[mds2-2716](https://doi.org/10.18434/mds2-2716)：原位热像和真实扫描策略；[mds2-2718](https://doi.org/10.18434/mds2-2718)：原始显微图和尺寸测量。微结构mds2-2775与动态耦合mds2-3842是其他记录，不默认和本组同条件。[官方索引](https://www.nist.gov/ambench/direct-am-bench-data-links-and-referencing-guidance) |
| 下载/版本/许可 | DOI可定位PDR，原文件下载、单项数据版本/许可证UNVERIFIED。2022结果说明要求以各dataset README追踪修订；实验说明PDF为v1.01，结果说明为v1.0，均不是2716/2718的数据版本。引用数据DOI与Weaver论文。[结果说明](https://www.nist.gov/system/files/documents/2022/07/27/AMB2022-03Measurement%20and%20%20Result%20Descriptions_v1.0.pdf) |
| 材料/粉末 | 裸IN718，无粉末。25.4×25.4×3.17mm板，制造商成分在论文附录1；完整温度相关热物性/光学参数包尚未核验。S的钛合金风格参数不能沿用。 |
| 功率/扫描（本组） | 热像/截面baseline记录285W、960mm/s、+X、10mm；case功率245/325W，速度800/1200mm/s，光斑49/82µm分别改变一项。此处是**来源报告值**；设定值与独立功率计原始实测记录的对应/不确定度UNVERIFIED，不能称都已校准到样品。[2024论文表2/3](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=957295) |
| 光斑（本组） | baseline D4σ=67µm、旋转对称Gaussian；与激光耦合组不同。[v1.01表1/2](https://www.nist.gov/document/amb2022-03-measurement-and-challenge-descriptions-version-101) |
| 初温/环境/边界 | 23.5±1°C；Ar，氧<1000ppm；热像组气流−Y、Z=10mm处4.3m/s；95±5kPa、入射5±0.5°，论文说明对应覆盖因子k=1。实际夹持热传导、气流边界/湍动和入射方位需补录。 |
| 不能混用的耦合组 | v1.01表3/4的baseline光斑110µm、+Y、入射8°、101±2kPa、气流+X且采样高度不同；不能拿其吸收数据验证67µm组几何。[v1.01](https://www.nist.gov/document/amb2022-03-measurement-and-challenge-descriptions-version-101) |
| 表面来源冲突 | 旧v1.01表写Ra=5.8µm；2024论文写Ra=0.15µm（5.8µin）。保留冲突并以原样品/最终论文澄清，不能悄悄把二者当同单位。 |
| 指标/不确定度 | 优先单道宽深；论文表4与附录3/表7提供按case的扩展不确定度k=2及分量。原始图像0.069µm/pixel、光学分辨率0.5µm，**像素尺寸不是总体不确定度**。TAM使用1298°C附近的实验定义/拐点，热像为表观温度，不能直接将每个CFD T值等同相机温度。 |
| 多道数据限制 | pads有真实轨迹、转向/等待和重熔历史，不能改成五束同时照射；先单道，再考虑独立多道候选。尺寸为2.5×5mm、间距110µm，详细时间序列从2716读取，不用尺寸/速度自行拼造。 |
| 表示能力/缺口 | 现有单束timeVsLaserPosition/Power可描述扫描，IN718热/流/光学参数、气体条件和受热边界需独立配置；表面化学、真实气流及极不稳定小孔仍有模型限制。不以调吸收率补偿未知光斑/轨迹。 |
| 成本/推荐 | 10mm/960mm/s=10.42ms仅为扫描时间推算；需冷却与空间/时间敏感性。墙钟UNVERIFIED。**优先V1候选**：宽深的可观测量与不确定度清楚，七组工况利于校准/独立验证分离；材料和下载尚缺，不能立即承诺复现。 |

## V2 — A-AMB2022-01 / Ti-6Al-4V能量耦合

基础实验论文：Brian J. Simonds, Jack Tanner, Alexandra Artusio-Glimpse, Paul A. Williams, Niranjan Parab, Cang Zhao, Tao Sun (2021), *The causal relationship between melt pool geometry and energy absorption measured in real time during laser-based manufacturing*, Applied Materials Today 23, 101049，DOI [10.1016/j.apmt.2021.101049](https://doi.org/10.1016/j.apmt.2021.101049)，[NIST记录](https://www.nist.gov/publications/causal-relationship-between-melt-pool-geometry-and-energy-absorption-measured-real-time)。论文包含裸板和粉末多组实验，不能把整篇全部条件视为公开校准文件的一次工况。

挑战结果论文：B. J. Simonds, J. Tanner, A. Artusio-Glimpse, N. Parab, C. Zhao, T. Sun, P. A. Williams (2024), *Ability to Simulate Absorption and Melt Pool Dynamics for Laser Melting of Bare Aluminum Plate: Results and Insights from the 2022 Asynchronous AM-Bench Challenge*, DOI [10.1007/s40192-023-00336-0](https://doi.org/10.1007/s40192-023-00336-0)，[全文](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=956550)。

| 项目 | 已核查事实、缺口与来源 |
| --- | --- |
| 材料分组 | 公开校准材料Ti-6Al-4V SRM654b；原盲挑战为Al5182 SRM1241c。**Ti不是盲挑战铝**，不能套用铝473W/1.980ms等参数。[官方说明](https://www.nist.gov/ambench/amb2022-01-benchmark-challenge-problems) |
| 公开原始数据 | 官方给出校准CSV、原始/处理X射线图像、光斑和同步示例；整个校准/挑战记录为[mds2-2525](https://doi.org/10.18434/mds2-2525)。2021论文当时为按请求提供，后来公开的这个记录才是本候选数据来源。 |
| 下载与版本/许可 | 从官方HTML解析并确认以下精确链接；README/CSV小范围读取超时，内容/列名/测量功率与许可UNVERIFIED，**不是已验证下载成功**。README文件名v110只证明链接命名，不冒充整个dataset版本。引用2525、2021实验论文及实际使用的挑战结果；许可证须原记录核查。 |
| 精确下载链接 | [README v110](https://data.nist.gov/od/ds/mds2-2525/2525_README_v110.txt)、[Ti裸板spot校准CSV](https://data.nist.gov/od/ds/mds2-2525/Spot%20on%20Bare%20Metal_Calibrated%20Absorption%20Data.csv)、[Ti裸板scan校准CSV](https://data.nist.gov/od/ds/mds2-2525/Scan%20on%20Bare%20Metal_Calibrated%20Absorption%20Data.csv)、[样品图V110](https://data.nist.gov/od/ds/mds2-2525/Sample%20Diagram_V110.pdf)、[焦平面光斑CSV](https://data.nist.gov/od/ds/mds2-2525/Beam%20Profile_5p5micron%20pixels_Normalized%20Integral.csv)。不把processed_wAbsorption图像当原始辐射影像。 |
| 材料/粉末/几何 | 本候选只取裸板，无粉末；SRM654b试样横向厚约300µm，表面抛光；完整形状从样品图补录。SRM化学证书不提供所有所需热物性/表面光学特性。[说明](https://www.nist.gov/ambench/amb2022-01-benchmark-challenge-problems) |
| 功率与轨迹 | Ti标称、实测P(t)、脉冲起止、扫描速度和真实起止轨迹：**UNVERIFIED，待校准CSV/README逐项核对**。官方说明讨论约2ms与700mm/s，但铝挑战参数不能未经匹配转移到Ti。选一个独立spot或scan记录，不混合。 |
| 光斑 | 1070nm；样品处1/e²直径122.5±3.0µm，焦点处49.5±5µm，样品在焦点下2.8mm；近Gaussian、有轻微椭圆性。**焦平面光斑CSV不是样品处光斑**。入射相对法向7°；该页另一句“对表面7°”有表述歧义，须用图和法向定义核对。[说明](https://www.nist.gov/ambench/amb2022-01-benchmark-challenge-problems) |
| 初温/边界/光学 | Ar回填至室压；具体初始温度数值、热接触、入射方位/偏振、表面氧化状态和材料光学常数尚未落地，UNVERIFIED，不照抄S。 |
| 指标/不确定度 | 时间吸收功率与吸收率、熔池/小孔宽深和凝固动态。吸收采样40ns，X射线50kfps（20µs帧距、2.5µs曝光），这些是采样/曝光，**不是吸收幅值或几何总体不确定度**；幅值/边界/同步不确定度需从实验文献/数据说明提取，暂UNVERIFIED。 |
| 模型适用性 | 光线+角度Fresnel/多反射是相应路径，但当前光学近似及反冲模型不保证定量小孔频谱/孔隙。未知Drude光学参数、表面状态、蒸汽/羽流遮蔽和真实边界可能主导误差。换成SRM654b材料包、单激光、实际P(t)/轨迹，不能沿用S五激光参数。 |
| 成本/推荐 | ms级照射与后续冷却、µm级界面及小孔时间尺度；墙钟UNVERIFIED，明显不能由10步S比例直接外推。**条件推荐**：光学模块成热点或验证目标时很有价值；当前作为高风险候选，不强制实施。 |

## LaserbeamFoam与当前S的来源/适用性

| 文献/源码 | 已实现或已发表内容 | 本项目不能据此声称 |
| --- | --- | --- |
| T. F. Flint, J. D. Robson, G. Parivendhan, P. Cardiff (2023), *laserbeamFoam: Laser ray-tracing and thermally induced state transition simulation toolkit*, SoftwareX21,101299，[DOI](https://doi.org/10.1016/j.softx.2022.101299)、[作者机构记录](https://research.manchester.ac.uk/en/publications/laserbeamfoam-laser-ray-tracing-and-thermally-induced-state-trans/) | 热流/相变/角度Fresnel射线工具；出版社数据声明为本软件文章未使用数据 | 软件论文不是当前S独立实验验证数据集 |
| Flint, Robson, Esmati, Grilli, Parivendhan, Cardiff (2024), Version2.0，SoftwareX25，[DOI](https://doi.org/10.1016/j.softx.2023.101612) | 多组分和多激光扩展；数据按请求提供 | 五束示例参数不是NIST实验输入；不以代码示例代替校准 |
| Flint, Ćosić, Parivendhan, Rodriguez, Bunaziv, O’Toole, Cardiff (2025), Version3.0，SoftwareX32，[DOI](https://doi.org/10.1016/j.softx.2025.102419)、[作者机构摘要](https://www.sintef.no/en/publications/publication/10281395/) | isoAdvector选项、激光离散/追踪和压缩多组分扩展 | 压缩求解器能力不能转嫁给当前不可压laserbeamFoam；版本号不替代锁定commit |
| G. Parivendhan, P. Cardiff, T. Flint, Ž. Tuković, M. Obeidi, D. Brabazon, A. Ivanković (2023), *A numerical study of processing parameters and their effect on the melt-track profile in Laser Powder Bed Fusion processes*, AM67,103482，[DOI](https://doi.org/10.1016/j.addma.2023.103482)、[期刊页](https://www.sciencedirect.com/science/article/pii/S2214860423000957) | CFD/DEM与实验尺寸对照；物理验证相关 | 数据声明按请求提供，非已确认可直接下载原始测量的优先候选；旧教程README的作者简写不能替代正式书目 |
| fiveLasersOnSubstrate/constant/transportProperties、LaserProperties；laserRayParticle.C、laserHeatSource.C；锁定3c93f265 | S保留rho4420、Ts1928.15/Tl1978K、sigma1.7、dSigma/dT−3.6e-4等示例值；各光束w55µm、1064nm、电子密度5.83e29 | 这些数值没有在字典中逐项给实验出处；不能宣称已是SRM654b的可追溯物性或NIST验证材料 |
| ThermoLab团队（作者顺序UNVERIFIED，2005）, *Surface Tension and Viscosity of Industrial Alloys from Parabolic Flight Experiments—Results of the ThermoLab Project*，[DOI线索](https://doi.org/10.1007/BF02945937)、[项目出版物目录](https://thermolab.net/publications/) | S的Marangoni注释指向此类实验；可作为表面物性查新线索 | 本轮未取得原文核对该常数/合金/温区，匹配UNVERIFIED；不能为整个热物性包背书 |

本地源码边界：原版采用不可压两相、蒸发冷却和经验反冲（见README、UEqn.H、TEqn.H），不完整求解蒸发质量损失/体积膨胀和可压缩羽流。光学以电子密度/电阻率构造复介电常数，平均s/p反射，不能直接表示任意偏振和氧化层。当前原生geometricVoF依赖以真实ldd为准。

半径匹配依据是源码I(r)∝exp[−Radius_Flavour(r/w)²]。当取默认2且实验确为圆Gaussian时，D4σ=2w、FWHM=w√(2ln2)；这是解析换算，不是测量。AMMT170µm→w85µm，CBM100µm→w50µm，2022组67µm→w33.5µm；V2样品122.5µm→w61.25µm。椭圆/截断/非Gaussian不能只用这一换算。源码射线截断r=1.5w，有限射线积分和能量账本必须核对，不能假定发射离散功率恰等于标称P。多激光Total Q日志是逐束处理后的累计沉积，不直接当每束独立吸收功率。

## V配置与资源提案（未实现，不覆盖S/M）

若获批准，另建版本化的V1-IN718-single或V1-IN625-machine-batch配置，以及V2-Ti64-record-ID配置；各自记录输入出处/不确定度、dataset/file hash、完整功率轨迹/几何/坐标、提取方法、校准/留出划分。现在这些是本文件中的配置提案，**没有可运行V算例，也不执行仿真**。

| 提案 | 空间/时间与成本分析（不是收敛结论） | 关键否决或补证 |
| --- | --- | --- |
| V1 单道 | 界面附近先评估2.5–5µm并做至少三级空间及独立时间细化；实际域/气层和网格须按熔池尺度及域敏感性批准。1.5×0.6×0.6mm假设局部域、5µm均匀网格仅算术即432万单元，2.5µm为3456万；这不是已验证可替代真实25mm基板的域。全10/14mm扫描ms级，dt假设1e-8–1e-7时约10^5–10^6量级步数，近表面流动还可能要求更小dt；墙钟/内存UNVERIFIED。不能承诺5–15分钟。 | 初始条件/域截断/夹持热边界无法证明时不能缩短扫描或裁域冒充实验；先定一组工况并完整取得数据及物性。不做昂贵全矩阵。 |
| V2 能量耦合 | 300µm厚试样须保持，不可直接降为2D；先评估界面1–5µm并独立细化射线分辨率/时间。若约2ms且dt假设1e-8–1e-7，为2万–20万步；700mm/s×2ms=1.4mm仅是官方扫描示例的长度推算，**不是已确认Ti轨迹**。采样40ns不强迫CFD逐点40ns推进，必须以过程带宽、收敛和观测滤波决定；必要分辨率仍可能更高。墙钟/内存UNVERIFIED。 | 先取得Ti的实际P(t)、同步、光学输入和幅值不确定度。若羽流/质量损失/偏振误差主导，应声明当前模型不适用，不能靠自由吸收率拟合“验证”。 |

资源预算只能在参考单元数、每步迭代/射线数量与真实M计时后估算；不可把小S的秒数按单元线性乘成承诺。并行如确需只选代表性配置并先排查已知风险，不恢复强制MPI矩阵。

## 正式实验验证前的可信度设计

1. 空间、时间、射线离散分别敏感性检查；固定其他变量，记录提取量收敛和迭代容差。能估离散误差时报告，振荡/非单调时不伪造收敛阶。
2. 坐标/单位：显式给实验→CFD变换、扫描正向、入射法向、原表面/变形表面、米/微米、秒/毫秒、K/°C。NIST通常z法向，当前示例y法向，不能只换变量名。
3. 宽深采用实验截面位置及**熔化历史包络/最高温度或液相历史**定义，不能用完全冷却后T或金属alpha外形代替熔合边界。长度按对应阈值/成像定义；2022 TAM与2018固相线长度不是同一量。
4. V2区分气液小孔边界和固液熔池边界；X射线是有限厚度投影，不无依据当作中心平面截线。按曝光/时间分辨率/视场/重建算子处理模拟输出，再比较；40ns吸收与20µs影像须同步。
5. 尺寸报绝对/相对误差和带单位偏差；时间序列报RMSE、清楚定义的nRMSE和时移。分开实验标准/扩展不确定度、输入传播和数值误差，处理相关性，不把重复标准差、像素、时间采样当总体不确定度。
6. 标定/独立验证必须分离到工况/独立重复/预先指定时间窗，不能随机拆高度相关相邻帧。若用B组拟合光学参数，其他功率/速度保留；冻结材料/光学参数后再做留出预测，报告失败，不继续调到通过。
7. 定义适用范围：单道宽深不验证粉末铺展、孔隙统计、氧化、微结构或多道热历史；V2拟合吸收不单独验证全部流动。V候选批准后再提出实验专属误差门槛，不擅用或放宽串行A/B容差。

当前未决：各数据文件/版本/许可证落地；完整温度相关物性和光学/表面条件；来源冲突；可观测量脚本；域/网格/步长收敛与真实成本。**S实测优先，V选型等待负责人批准。**
