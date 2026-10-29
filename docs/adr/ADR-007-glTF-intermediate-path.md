# ADR-007 模型导入路径：中间 glTF（v1）vs 直接构建（v2）

状态：已接受（Accepted）

## 背景
第二阶段 M2（模型导入 UE 5.8）需把 model IR 落地为 UE 的 SkeletalMesh。MMD2UE_实践手册.md §8.1 给出两条候选路径：
1. **中间 FBX/glTF 路径**（推荐起步）：核心层导出 glTF 或 FBX，UE 通过 Interchange 或 FBX 导入器创建 SkeletalMesh。优点是 UE 原生导入链路稳定；缺点是要额外维护导出器。
2. **直接构建路径**：在 UE Python 中使用 SkeletalMesh 构建 API 直接写顶点、骨骼、权重。优点是无中间格式；缺点是 API 细节多、调试成本高。手册建议作为 v2 优化方向，v1 不做。

手册 §8.1 留下「决策点」：M0 spike 时比较两条路径的骨骼命名保留、权重保真度与导入耗时，写入 ADR。本 ADR 落实该决策，且与既有 ADR 保持一致。

## 决策
第二阶段（v1）**走中间 glTF 路径**，直接构建路径留 v2。

1. **核心层新增 glTF 2.0 导出器**：model IR → glTF 2.0（.gltf + .bin，或 .glb），输出骨骼层级、蒙皮网格（skin/权重）与材质近似。选 glTF 而非 FBX 的理由：
   - glTF 2.0 是开放标准，文本（.gltf/.json）+ 二进制块（.bin）结构适合金标比对与 JSON diff 回归（契合第 14 节「金标 + JSON diff」的门禁机制）；
   - UE 5.8 原生支持 glTF 导入与 Interchange，导入链路稳定；
   - glTF 的 skin/joint/weight 语义与 SkeletalMesh 需求直接对应（骨骼层级、蒙皮权重），与 FBX 相比更少依赖第三方二进制结构。
2. **UE 适配层 adapters/ue5_8/**：读取核心层产出的 glTF，经 UE 原生导入链路（Interchange 或 glTF 导入器）创建 SkeletalMesh，并建立 MMD 近似母材质映射（diffuse→BaseColor、贴图→BaseColor 贴图）。
3. **直接构建路径（v2）**：暂不实现，仅作为 v2 优化方向保留。若后续需要更细粒度的骨骼命名/权重控制（中间路径无法满足时）再启用。

## 与既有约束的关系
- 遵循 **ADR-001**（核心/适配层分离）：glTF 导出器属于核心层（无 UE 依赖，可单测），UE 适配层仅消费 glTF，不 import unreal 的核心逻辑不变。
- 遵循 **ADR-006**（纯转换器，零资产分发）：glTF 导出器仍是转换逻辑，产物目录不含任何 PMX/VMD 实体资产；合成样例 glTF 金标由工具程序化生成。
- 与第 14 节门禁兼容：glTF 文本结构支持金标 JSON diff，新增「glTF 导出金标比对」与「glTF 产物报告检查」门禁步骤。

## 影响
- 核心层新增 glTF 2.0 导出器（含骨骼层级/蒙皮网格/材质近似），需金标覆盖。
- 适配层从「直接写顶点」变为「读取 glTF 导入」，实现复杂度下降，可替换性提高。
- 门禁 verify_all.py 需扩展 glTF 金标与报告检查步（见 docs/stage2-requirements.md §4）。
- 直接构建路径留 v2，若未来启用需另立 ADR 记录新增决策。

## 参考 / 借鉴范围
- 决策来源：MMD2UE_实践手册.md §8.1（用户手册内既定的两条候选路径与推荐），结合 glTF 2.0 开放标准与 UE 5.8 glTF/Interchange 导入能力；非借鉴第三方代码。
