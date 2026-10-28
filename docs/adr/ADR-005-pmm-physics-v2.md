# ADR-005 PMM 与物理延后至 v2

状态：已接受（Accepted）

## 背景
MikuMikuMoving 项目格式（PMM）与 PMX 物理（刚体/关节/IK 烘焙）在第一阶段（M0+M1）中仅需接口预留。

## 决策
- PMM（MikuMikuMoving project, v2）不纳入 v1 解析范围；`parsers/pmm.py` 入口预留并抛 `NotImplementedError`（不读取输入、不产生错误数据，见 D-M1-7 / AC-M1-8）。
- PMX 物理字段（`rigid_bodies`、`joints`）在 IR 中保留为空占位（D-M1-3），完整物理与 IK/付与烘焙延后至 M3/M7。
- v1 仅完成解析器正确性与金标基准，不做语义转换（见 ADR-001 分层）。

## 影响
- 真实 PMM 资产与物理烘焙能力在 v2 才落地。
- IR 中已预留 `rigid_bodies` / `joints` 字段，后续里程碑填充无需破坏现有 IR 结构。

## 参考 / 借鉴范围
- 思路来源：MMD 工具链将「项目/动画工程格式」与「模型解析」分阶段的常见做法。
- clean-room 声明：不复制任何第三方代码。
- 许可核实指向 ADR-003。
