# 第二阶段（M2）验收条款：模型导入 UE 5.8

> 来源：MMD2UE_实践手册.md §8（UE 5.8 适配层）、§13（里程碑与验收）M2 行、§14（测试与验收阈值）；另参 §1.2（v1 范围）、§2.1（技术约束）、§9（物理预留）。本文档供实现与审查使用，所有条款逐条可验证。
> **阶段范围声明**：第二阶段只交付「model IR → glTF 2.0 导出 → UE SkeletalMesh 导入 + 基础材质近似」。动作（M3）、镜头/Sequencer（M4）、材质总报告（M5）、物理（M7 仅接口）不在本阶段验收范围内。
> **路径声明（ADR-007）**：本阶段走**中间 glTF 路径（v1 推荐）**，直接构建留 v2。

## 0. 全局技术约束（贯穿 M2）

以下约束同时约束核心层与适配层，实现时任一违反即视为不通过。

- C1 依赖边界（无 unreal 依赖）：**核心层（core/ 与 glTF 导出器）不得 import unreal，不依赖 UE**；只有适配层 adapters/ue5_8/ 才允许 import unreal。验证：grep src/mmd2ue/（排除 adapters/）无任何 unreal 导入。
- C2 核心/适配层分离：glTF 导出器在核心层，读取 model IR；UE 适配层只读取 glTF（经 Interchange 或 glTF 导入器），不回读 IR 内部实现细节。验证：适配层入口消费 glTF 文件，核心层产 glTF 文件。
- C3 资产边界（ADR-006）：本阶段交付物及任何产物目录**不含任何 PMX/VMD 实体资产**，也不含任意图借用贴图/音频。合成样例（tests 夹具）由工具程序化生成，非借用模型数据。验证：门禁资产泄漏检查 + 仓库 tree 核对。
- C4 复现性：同一输入两次运行产物哈希一致。验证：门禁可重复运行且结果稳定。

## 1. M2 —— 交付物

- D-M2-1 **核心层 glTF 2.0 导出器**：model IR → glTF 2.0（.gltf + .bin，或 .glb），含骨骼层级、蒙皮网格（skin/权重）、材质近似。位于 src/mmd2ue/core/（纯标准库，无 UE 依赖）。
- D-M2-2 **UE 适配层 adapters/ue5_8/**：读取 glTF，通过 UE 原生导入链路（Interchange 或 glTF 导入器）创建 SkeletalMesh；含 MMD 近似母材质映射。入口脚本放 adapters/ue5_8/，经 UE commandlet 运行（§8.6）。
- D-M2-3 **材质近似映射**：每 PMX 材质 → 一个 UE MaterialInstance，父材质统一为「MMD 近似」母材质；映射规则见 §3。
- D-M2-4 **glTF 导出金标**：tests/golden/ 下人工对照生成的 glTF 金标（用合成样例生成），供金标比对回归。
- D-M2-5 **门禁扩展**：tools/verify_all.py 增加 glTF 导出金标比对步与 glTF 产物报告检查步（见 §4）。

## 2. M2 —— 导入路径（glTF 中间路径，v1）

- 本阶段采用 §8.1 推荐的**中间 glTF 路径**：核心层导出 glTF 2.0，UE 通过原生导入链路创建 SkeletalMesh。
- **直接构建路径（UE Python 逐顶点写入）留 v2**，v1 不做。决策与理由见 ADR-007。
- 决策依据（§8.1）：中间 glTF 路径 UE 原生导入链路稳定；缺点是需额外维护导出器。直接构建路径无中间格式但 API 细节多、调试成本高，故延后。

## 3. M2 —— 材质近似规则（§8.2）

- 每个 PMX 材质映射到一个 UE MaterialInstance，父材质统一为一个「MMD 近似」母材质。
- 参数映射（逐条验收）：
  - **diffuse → BaseColor 系数**。
  - **贴图（纹理）→ BaseColor 贴图**。
  - **sphere map → v1 忽略，记入报告**。
  - **toon → v1 忽略**，用简单 Lambert/PBR 近似，记入报告。
  - **edge（描边）→ v1 忽略**，记入报告。
- 材质名保留日文原名，便于用户对照。

## 4. M2 —— 门禁扩展

python tools/verify_all.py 在既有五步之外，增加以下步骤，**任何一步失败禁止合并**：
1. glTF 导出金标比对：核心层导出结果与 tests/golden/ 下金标 glTF 逐字段比对（JSON diff / 数值容差）。
2. glTF 产物报告检查：导出产出的报告列出被忽略/近似的材质项（sphere map / toon / edge）。

## 5. M2 —— 验收标准（§13 M2 行 + 本阶段）

- AC-M2-1 用合成样例（或本机 PMX，如黑羽，若可用）经 glTF 路径在 UE 5.8 生成 SkeletalMesh，**骨骼层级完整**。
- AC-M2-2 生成的 SkeletalMesh **网格可见**（顶点/面数据经过 glTF 保真导入）。
- AC-M2-3 **基础材质正确**：diffuse→BaseColor 系数、贴图→BaseColor 贴图 生效；sphere map / toon / edge 被忽略并逐项记入报告。
- AC-M2-4 **glTF 导出金标对比通过**：核心层导出的 glTF 与金标一致（含骨骼层级、蒙皮权重、材质近似字段）。
- AC-M2-5 **无 unreal 依赖边界**：核心层导出器不 import unreal（C1/C2）；只有 adapters/ue5_8/ import unreal。
- AC-M2-6 **零资产分发边界（ADR-006）**：本阶段交付物与产物不含任何 PMX/VMD 实体资产。
- AC-M2-7 门禁 verify_all.py 全绿（含新增的 glTF 金标与报告检查步）。
- AC-M2-8 glTF 导出报告包含被忽略/近似的材质项（sphere map / toon / edge）逐项列出（衔接 M5 总报告，本阶段先落底座）。

## 6. M2 —— 可验收范围（收窄后）

- 由 §13 M2 行「骨骼层级完整，网格可见，基础材质正确」+ 本阶段 glTF 导出金标 + 无 unreal 依赖边界 + 零资产分发构成。
- 附注：§14.2 的骨骼/动作/相机位置误差阈值属模型几何保真度量，其中「骨骼位置误差（T-pose）< 2 cm」可在有真实资产标定后作为 M2 的几何保真参考；第一阶段标定已延后，故本阶段不强制真实黑羽误差验收，以合成样例 + glTF 金标为准。
- 动作导入（M3）、镜头/Sequencer（M4）、材质近似总报告与全量近似清单（M5）、物理（M7 仅接口）**不在本阶段验收范围**。

## 7. 范围边界

- 本阶段（M2）**不含**：动作导入（AnimSequence）、相机/Sequencer 组装、物理资产生成（仅 IR 预留 rigid_bodies/joints 字段）、PMM/PMM 工程、其他 UE 版本适配。
- 本文档不包含、不应包含任何 PMX/VMD 实体资产。
- **第二阶段完成判定**：以 §5 收窄后的 AC-M2-1 ~ AC-M2-8 逐条通过为准，不得使用整体性过关表述。

## 8. 报告 `units` 字段口径（F9）

`units`/`skipped`/`approximated` 三个键由 M0 门禁统一要求（stage1 §1.2 第 3 步），但
`units` 在三个报告生产方之间口径**不同**——字段名相同、含义不同，聚合（如 M5 材质/总
报告）时必须按本表换算，不得跨口径直接相加：

| 报告来源 | `units` 含义 | 口径说明 |
| --- | --- | --- |
| PMX 解析报告（`pmx.parse` → `ir.report`） | **1 模型** | 一个 PMX 文件即一个模型，恒为 `1`；顶点/材质/骨骼计数在 `ir.counts` 下，不占 `units` |
| VMD 解析报告（`vmd.parse` → `ir.report`） | **段数** | `bone + morph + camera` 帧数之和（动作段数） |
| glTF 导出报告（`gltf.export_gltf` → `ExportReport`） | **顶点数** | 写入网格的顶点数 |

权威定义位于 `src/mmd2ue/core/ir.py` 模块 docstring；解析器与导出器的注释均回指该处。
换算示例（合成样例）：PMX `units=1`、VMD `units=5`（2 骨骼帧 + 1 morph 帧 + 2 相机帧）、
glTF 导出 `units=3`（3 顶点）——三者值域与含义均不同，属预期行为，不是缺陷。

## 9. 骨骼 `position` 坐标语义（F8 方向纠正）

PMX 2.0 规范定义 **bone.position 为相对父骨骼的本地平移（local translation）**，不是模型空间
绝对坐标（权威来源：felixjones PMX 2.0 规范『Position | vec3 | The local translation of the bone』）。

- `pmx.py` 解析时原样透传该相对偏移（不累加、不绝对化）。
- `gltf.py` 的 `node.translation` 直接取 `bone.position`（glTF node 平移本就是 parent-relative，语义一致，无换算）。
- `inverseBindMatrices` 用沿父链累加的绝对静止变换求逆：`绝对位置 = 父绝对位置 + position`，
  静止变换为纯平移，故 `IBM = translate(−绝对位置)`。
- 顶点 `position` 是模型空间绝对坐标，与骨骼 `position` 口径不同，二者不得混用。

合成样例 `pmx_gltf_chain`：hips=(0,8,0)、spine=(0,1,0)、head=(0,11,0) 为规范相对偏移，
导出后世界位置为 (0,8,0)/(0,9,0)/(0,20,0)。
