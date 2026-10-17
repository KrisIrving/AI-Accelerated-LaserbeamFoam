# alpha_filtered 与射线沉积静态审查

2026-10-17；DEC-008授权的阶段1衔接审查。源码基线a5f53b9158871f363a669c16a2a1a631103674b9；本轮不修改求解器、库、物理配置或数值门槛，不运行额外CFD。

## 证据与历史衔接

GitHub的[EXPERIMENT_LOG](EXPERIMENT_LOG.md)记录M1/M3早期沉积层错位：1 μs总沉积约755.601608 W相同，但y质心112.5/101.25 μm，源峰值约2.202245e15/9.060464e15 W/m³，初始金属面105/97.5 μm；共同粗格上的早期正沉积支撑重叠约0。这些是既有研究结论，不是本轮S探针结果。

本机另一个既有工作区确有原始M1、M3、M1-IC：初态、10/10/3个演化时间目录、原生网格和已有诊断报告。本轮只清点文件并读取既有报告、重算诊断包外部及内部哈希；未重新解析全套原场或重新运行比较器。状态为RAW_DATA_PRESENT / ORIGINAL_FIELD_NUMERICAL_REAUDIT_NOT_PERFORMED；不适用RAW_DATA_UNAVAILABLE。私有绝对路径仅在本地清单中保存。

两份本地既有归档均核对9个普通文件、8条内部SHA256及FILES清单通过，未发现重复、链接或越界条目：

| 既有归档 | SHA256 |
| --- | --- |
| m1-m3-comparison-feedback.tar.gz | 8ac01be3e64254bb9130596f6e7bace9a2f8b266a868f5e97a1f723c4a0f221c |
| m1-ic-comparison-feedback.tar.gz | df215f2c3a146c1d80bb3131aa0ee53cac49cc2b54dfa7318bf0132aca1e78b9 |

既有M1-IC三方报告status=COMPARISON_COMPLETED、issues=[]、tool_commit=a5f53b9158871f363a669c16a2a1a631103674b9；报告记录原消费源在当次比较窗口前后哈希一致。本轮归档核验不重新证明这些原场目前与当时完全一致。

| 既有报告观察量 | M1 | M3 | M1-IC |
| --- | --- | --- | --- |
| 初始金属体积 / m³ | 7.02e-11 | 7.29e-11 | 7.29e-11 |
| 1 μs金属最高T / K | 1123.36 | 2274.19 | 1113.62 |
| 3 μs金属最高T / K | 1969.13 | 4086.86 | 1957.76 |
| 3 μs金属最大液相率 | 0.82208 | 1 | 0.59396 |
| alpha>0.5区域首次非零液相率输出 / μs | 3 | 1 | 3 |

M1-IC的初始alpha与受限M3的L1/L2/Linf在既有报告中均为0；初始T与M1一致。1 μs的IC沉积积分、峰值和y质心与M1相同，3 μs质心约112.023 μm，仍远离M3的101.25 μm。保留结论：体积守恒的初态干预未复现M3早期热响应；不能据此宣称初态完全无影响或网格差异已被单因果解释。

## 静态调用链和分支

1. [laserbeamFoam.C](../../applications/solvers/laserbeamFoam/laserbeamFoam.C)第143–164行：每个PIMPLE外迭代先推进alpha，再执行updateProps，随后将alpha_filtered、n_filtered和电阻率传给laser.updateDeposition。因此写出时刻的alpha不是保证等于同一步沉积调用瞬间的全部输入；初态也不能直接代表首次热源调用状态。
2. [updateProps.H](../../applications/solvers/laserbeamFoam/updateProps.H)第43–107行：alpha>0.99设1，alpha<0.01设0，其余保留原值，端点0.01/0.99也保留。内部与边界均有该处理，最后再次correctBoundaryConditions，实际边界最终值还受patch类型支配。它不是将所有混合单元二值化，也不是alpha_smoothed；后者另由fvc::average(alpha1)计算。
3. n_filtered=grad(alpha_filtered)/(mag(grad(alpha_filtered))+deltaN)。这是有限体积梯度法向，不是这里求取的精确PLIC交点。alpha的体积守恒限制不保持这个梯度、逐射线首遇单元或亚单元界面位置。alpha_filtered也参与潜热插值，温度变化不能全部归因于单一射线门槛。
4. [laserHeatSource.C](../../src/laserHeatSource/laserHeatSource.C)第713–716行从每束字典读dep_cutoff，缺省0.5；锁定fiveLasersOnSubstrate输入没有显式覆盖该项。每次更新清空沉积后累加五束；trackingData直接接收上述过滤场及法向。
5. [laserRayParticle.C](../../src/laserHeatSource/laserRayParticle.C)第118–120、181–239、241–380行：普通追踪中，若mag(n)>0.5且alpha>=depCutoff，则本单元沉积A*P/V并镜面反射，剩余功率乘1-A；若仅alpha>=depCutoff，则本单元全吸收P/V；其余继续追踪。因此资格在0.5处不连续，**恰等于0.5被纳入**，不是alpha>0.5。诊断中metal mask的严格大于号与射线门槛不同。
6. 反射后的escapingInterface状态抑制界面带内重复事件；alpha<cutoff离带，进入alpha>max(0.98,cutoff)可重定向或吸收，超过200次带内跳转也吸收余量。maxRayBounces默认1000，默认动作deposit；功率相对终止阈值默认1e-4。第436–450行墙面回调直接向边界单元沉积余量，没有在该回调再核对alpha。需要分别识别这些贡献，不能把每个正沉积单元都当作Fresnel首遇界面。
7. [TEqn.H](../../applications/solvers/laserbeamFoam/TEqn.H)约第78行直接使用laser.deposition()作为体积热源；没有在这里再乘alpha。局部P/V与热容/导热离散都会随网格和混合率变化。相同积分功率不保证相同局部温升。

## 可检验推论与边界

若一个粗混合层的alpha接近0.5，浮点限制结果、alpha推进、梯度法向和首遇资格可共同改变沉积层；相同金属体积并不能控制这些变量。这是从源码得到的机制候选，尚未用本轮原场重算验证，不能登记为Bug或M1-IC结果的唯一原因。没有证据宣布多次反射、网格/时间收敛、实验准确性、性能热点或AI收益已验证。

## 推荐下一项科学验证（PROPOSED）

优先做**只读初态与早期沉积资格审计**，复用已有M1/M3/M1-IC的0及1 μs场、原生网格与已有VTK射线路径，不新增CFD。将alpha与0.01/0.5/0.99的带符号距离按y层统计（含0.5附近浮点最小/最大值、>=与>两种计数），读取实际fvSchemes/边界并按原生离散计算过滤场和梯度门槛，再与已有Deposition非零支撑及射线首遇位置交叉比较。字段时间与热源调用时间不一致、路径未保存或不能重建的环节单列UNVERIFIED；用读取窗口前后哈希保护原数据。

首要判别：IC的混合层是否在0.5门槛或法向门槛处被跳过，是否解释其首遇沉积仍主要在112.5 μm。公开交付只需层表、分支资格计数、支撑重叠和哈希。预算目标小于2分钟、RSS小于1 GiB，均为待测目标；不重跑已有全场比较器、不重跑M1/M3/M1-IC。先测一个时刻，预算超限停止并记录。

该任务不改dep_cutoff，成本低于新CFD，能先排除“IC限制层恰在阈值附近但被当作等效界面”的解释。若仍不能辨别，再单独提出冻结初态、仅一次热源更新的受控重放；修改门槛或加入埋点必须另行明确批准。本轮没有执行上述后续任务，阶段路线保持不变。
