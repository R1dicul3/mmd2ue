# 第一阶段（M0 + M1）验收条款

> 来源：MMD2UE_实践手册.md §1、§2、§4、§12、§13、§14（另参 §6、§7、§11 相关条款）。本文档供实现与审查使用，所有条款逐条可验证。
> **阶段范围声明（2026-10-29 修订）**：第一阶段只交付「解析器 + 门禁 + 合成样例金标」；真实黑羽资产的标定、许可证结论属后续含真实黑羽资产标定的里程碑，不在第一阶段验收范围内（见 §3 变更记录）。

## 0. 全局技术约束（贯穿 M0+M1）

以下约束同时约束 M0 与 M1，实现时任一违反即视为不通过。
- C1 语言：转换核心用 **Python 3.11+**；UE 适配层用 UE 内置 Python（UE 5.8 自带解释器）。验证：pyproject.toml 声明 requires-python >=3.11。
- C2 依赖：核心**纯标准库优先**，解析器不 import unreal，不依赖 UE。验证：src/mmd2ue/core/ 与 parsers/ 的 import 仅限标准库，无任何 unreal 导入。
- C3 核心与适配层分离：adapters/ue5_8/ 之外的代码不得 import unreal；IR 是唯一真相。验证：grep src/（排除 adapters/）无 import unreal。
- C4 编码：PMX 字符串支持 UTF-16LE 或 UTF-8；VMD 名称为 Shift-JIS（CP932）；路径与文件名统一 UTF-8；写文件无 BOM。验证：单测覆盖两种 PMX 编码 + VMD Shift-JIS 解码 + 无 BOM 写入。
- C5 资产边界：仓库/发布包**不得包含**任何 PMX/VMD/音频/借用贴图实体文件；.gitignore 含 *.pmx、*.vmd、*.pmm、*.wav、*.mp3 与 samples/private/。验证：门禁资产泄漏检查 + 仓库树核对。
- C6 复现性：同一输入两次运行产物哈希一致。验证：门禁可重复运行且结果稳定。

## 1. M0 —— 仓库 / ADR / 门禁脚手架

### 1.1 交付物
- D-M0-1 仓库骨架：根含 README.md、LICENSE、pyproject.toml；目录含 docs/adr/、src/mmd2ue/、tests/、tools/、samples/（仅自生成最小样本）。采用 src/ 布局。
- D-M0-2 ADR 1–3 篇（docs/adr/，覆盖 ADR-001 核心/适配层分离、ADR-002 批处理走 CLI、ADR-004 资产不分发，及 M0 决策项）。每条 ADR 记录参考来源与借鉴范围。
- D-M0-3 许可证结论：选定 MIT 或 Apache-2.0（不引入 GPL 代码）；逐个核实参考项目（VibeUE、MMD2Unreal、ue5-mmd-toolkit）许可证；GPL 或不明许可者仅 clean-room 借鉴思路，不复制代码。
- D-M0-4 标定结果：确认 scale 与轴符号，提交 tools/calibrate/results/ 下 JSON（不含模型本体），并在 ADR 记录。
- D-M0-5 门禁 tools/verify_all.py（见 §1.2 五步）。

### 1.2 门禁 verify_all.py 五步
python tools/verify_all.py 依次执行以下五步，**任何一步失败禁止合并**：
1. 单测（tests/unit）。
2. 金标比对（tests/golden）。
3. 转换报告检查：报告必须包含 units、skipped、approximated 三个键。
4. 许可证文件存在性检查。
5. 资产泄漏检查：仓库中不得出现 *.pmx、*.vmd 等实体资产。

### 1.3 验收标准（M0）
- AC-M0-1 python tools/verify_all.py 全绿（五步全部通过）。
- AC-M0-2 【延后：待真实黑羽资产标定里程碑】标定结果：从黑羽 PMX 的 T-pose 比对求出 scale_to_cm 与轴符号，写回 manifest.json / transforms/coords.py 常量；标定脚本输出 JSON 可复现。
- AC-M0-3 【延后：待真实黑羽资产标定里程碑】许可证类型已决策（MIT 或 Apache-2.0）并在 LICENSE + ADR 落地。
- AC-M0-4 【延后：待真实黑羽资产标定里程碑】参考项目许可核实结论写入 ADR；任何 clean-room 借鉴在文件头注明来源与许可。
- AC-M0-5 仓库不含任何 PMX/VMD/音频实体文件（.gitignore 已含相应规则）。

### 1.4 M0 第一阶段可验收范围（收窄后）
- 仓库骨架齐全（D-M0-1）。
- ADR 脚手架就绪（D-M0-2，可含标注「待定」的占位决策）。
- 门禁 verify_all.py 五步可运行（D-M0-5，AC-M0-1）。其中第 4 步「许可证文件存在性检查」以**许可证占位文件存在即视为通过**，不要求许可证类型最终敲定。
- 无实体资产（AC-M0-5）。

## 2. M1 —— PMX / VMD 解析器与金标

### 2.1 交付物
- D-M1-1 src/mmd2ue/core/parsers/pmx.py：PMX 2.0/2.1 解析（纯解析，不做语义转换）。
- D-M1-2 src/mmd2ue/core/parsers/vmd.py：VMD 解析（骨骼/表情/相机/光源/自阴影/IK 开关六块）。
- D-M1-3 src/mmd2ue/core/ir.py：IR 数据结构与 ir_version；model.json 保留 rigid_bodies、joints 字段（物理预留，可为空）。
- D-M1-4 CLI 入口 src/mmd2ue/cli.py：inspect、convert-model、convert-motion、convert-camera。
- D-M1-5 金标 IR：tests/golden/ 下人工对照生成的 IR JSON（第一阶段用**合成样例**生成，真实黑羽资产金标延后）。
- D-M1-6 单测：tests/unit/（解析器、bezier 插值数学、边界检查等）。
- D-M1-7 parsers/pmm.py 入口预留，抛 NotImplementedError（PMM is v2）；VPD 可选。

### 2.2 解析正确性要求（§6）
- PMX：'PMX ' 签名 + float 版本号（2.0/2.1）；全局参数块（编码标志、附加 UV 数、各索引字节宽度）严格按规范读取；数据块顺序固定（顶点→面→贴图→材质→骨骼→morph→显示框→刚体→关节）；字符串长度前缀以字节计；骨骼标志位决定 IK/付与/可见性/可变形附加数据；顶点权重 v1 至少支持 BDEF1/2/4 与 SDEF（SDEF 可近似 BDEF2 并记入报告）。
- VMD：固定长度签名 + 模型名（Shift-JIS，去尾部 0x00）；骨骼帧按帧号排序，同名同帧号按规范处理冲突；名称解码失败时保留原始字节（hex）并在报告标注，不静默替换。
- 边界检查：每个字段做边界检查；**未知版本直接报错，不猜**。

### 2.3 验收标准（M1）
- AC-M1-1 【延后：待真实黑羽资产标定里程碑】黑羽 PMX 解析的骨骼数、材质数与 MMD 显示一致（§13 M1 行）。
- AC-M1-2 【延后：待真实黑羽资产标定里程碑】VMD 帧数与 MMD 一致（§13 M1 行）；帧号偏差 0 帧（30fps，§14.2）。
- AC-M1-3 金标比对通过：解析结果与人工对照 IR 一致（第一阶段用合成样例金标，tests/golden JSON diff）。
- AC-M1-4 单测全绿（tests/unit）。
- AC-M1-5 IR 产物均带 ir_version；版本不匹配时拒绝加载，不做隐式兼容（§5.1）。
- AC-M1-6 解析器不 import unreal（满足 C2/C3）。
- AC-M1-7 报告含 units/skipped/approximated（衔接 M0 门禁第 3 步）。
- AC-M1-8 PMM 入口抛 NotImplementedError，不产生错误数据（§6.4）。

### 2.4 M1 第一阶段可验收范围（收窄后）
- 解析器正确性：以**合成样例 + 合成金标**验证（AC-M1-3、AC-M1-4），不依赖真实黑羽 PMX/VMD 资产。
- IR 版本号与拒绝加载逻辑（AC-M1-5）。
- 无 unreal 依赖（AC-M1-6）。
- 报告键齐全（AC-M1-7）。
- PMM 入口占位（AC-M1-8）。
- 真实黑羽资产下的骨骼数/材质数/帧数一致性（AC-M1-1、AC-M1-2）延后到后续里程碑。

## 3. 变更记录

### 3.1 2026-10-29：延后真实资产标定与许可证结论（方案 b）
- 批准人：用户（2026-10-29 决策）。
- **变更内容**：AC-M0-2、AC-M0-3、AC-M0-4、AC-M1-1、AC-M1-2 的归属由第一阶段改为「延后：待真实黑羽资产标定里程碑」。
- **理由**：本会话无真实黑羽 PMX/VMD 资产，无法完成真实资产下的标定与骨骼/材质/帧数一致性核验；许可证类型（MIT/Apache-2.0）与参考项目许可核实也未定。
- **影响**：第一阶段可验收范围收窄为「解析器正确性（合成样例 + 金标）、门禁五步、无实体资产、许可证占位即视为通过」。相关延后条款不影响最终正确性目标，仅在拿到真实资产后于后续里程碑单独验收。

## 4. 未决项
- U1 许可证类型：MIT / Apache-2.0（延后到后续里程碑决定，见 P1；第一阶段以占位许可证视为通过）。
- U2 黑羽 PMX 样本路径：标定与金标依赖的真实样本，延后到后续里程碑（本会话无此资产）。
- U3 标定 scale 与轴符号：scale_to_cm 在标定前为 null，延后到后续里程碑写入（§5.1/§7.2/§7.4）。
- U4 模型导入路径（中间 glTF/FBX vs 直接构建）：M0 spike 后决定（P2，不影响 M0/M1 验收）。
- U5 参考项目借鉴范围：M0 许可核实后决定（P3）；第一阶段不要求核实结论。

## 5. 范围边界
- 本阶段（M0+M1）**不含**：UE 适配层实现（M2+）、IK/付与烘焙（M3）、相机/Sequencer 组装（M4）、材质近似与总报告（M5）、物理（M7 仅接口）。
- 本文档不包含、不应包含任何 PMX/VMD 等实体资产。
- **第一阶段完成判定**：以 §1.4、§2.4 收窄后的可验收范围逐条通过为准，不得使用整体性过关表述（被延后的 AC-M0-2/3/4、AC-M1-1/2 由后续里程碑单独验收，不计入第一阶段判定）。