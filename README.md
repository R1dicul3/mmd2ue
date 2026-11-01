# mmd2ue

MMD（PMX / VMD / VPD）→ Unreal Engine 5.8 转换工具，纯 Python 标准库实现，不依赖
Blender / Unity / MMD 本体。

**当前版本：v0.2.0（第一版可用版本）**，覆盖 M0（脚手架 + 门禁）、M1（PMX/VMD 解析器）、
M2（model IR → glTF 2.0 导出 + UE 适配层）。

> 本工具是**纯转换器**：不包含、不附带、不分发任何模型数据；它只把用户本地的 MMD
> 资产转换成中间 IR / glTF，模型、动作、贴图、音乐的授权由使用者自行负责（ADR-006）。

## 特性

- **PMX 2.0 / 2.1 解析**（UTF-16LE / UTF-8），完整读取骨骼层级、顶点蒙皮
  （BDEF1/2/4 + SDEF→BDEF2 + QDEF 降级）、材质、表情、刚体/关节、骨骼 IK/付与/轴限制。
- **VMD 解析**（CP932）：骨骼 / 表情 / 相机 / 光源 / 自阴影 / IK 六块。
- **版本化 IR**（ir_version）：解析产物带版本号，版本不匹配拒绝加载，不做隐式兼容。
- **glTF 2.0 导出**：model IR → 标准右手系 glTF（.gltf + 外部 .bin），含骨骼层级、
  蒙皮 JOINTS_0/WEIGHTS_0、材质近似 PBR、POSITION/NORMAL min/max。
- **UE 适配层**：adapters/ue5_8/ 经 UE 原生 glTF 导入创建 SkeletalMesh + MMD 近似母材质。
- **八步门禁**：单测 / 金标 / 报告三键 / 许可证 / 资产泄漏 / glTF 金标 / glTF 报告 /
  分发树资产检查。

## 安装

需要 Python 3.11+（本仓库在 3.13 上验证）。

```powershell
# 开发模式安装（含 pytest）
pip install -e .[dev]

# 验证安装
mmd2ue --version
# → mmd2ue (IR 0.2.0)
```

## 使用指南

### 1. 查看模型 / 动作概况（inspect）

```powershell
mmd2ue inspect model.pmx
mmd2ue inspect motion.vmd
```

输出 JSON：PMX 显示模型名、PMX 版本、编码、各数据块计数（骨骼/材质/表情/顶点/面）、
报告键（units/skipped/approximated）；VMD 显示骨骼/表情/相机/光源/自阴影/IK 帧数。

### 2. 转换模型 → IR JSON（convert-model）

```powershell
mmd2ue convert-model model.pmx -o model.ir.json
# → wrote model.ir.json (N bones, M materials, K morphs)
```

### 3. 转换动作 → 动作 IR JSON（convert-motion）

```powershell
mmd2ue convert-motion motion.vmd -o motion.ir.json
# → wrote motion.ir.json (N bone frames, M morph frames, K camera frames)
```

### 4. 提取相机轨迹 → 相机 IR JSON（convert-camera）

```powershell
mmd2ue convert-camera motion.vmd -o camera.ir.json
```

### 5. 导出模型 → glTF 2.0（export-gltf）

```powershell
mmd2ue export-gltf model.pmx -o model.gltf --bin model.bin --report report.json
# → wrote model.gltf + model.bin (N bones, V verts, M materials)
#   ignored material items: ...
```

产物：
- `model.gltf`：glTF 2.0 JSON（引用 `model.bin`）。
- `model.bin`：顶点 / 法线 / UV / 蒙皮 / 索引二进制缓冲，须与 .gltf 同级。
- `report.json`（可选）：导出报告，含 units/skipped/approximated、忽略的材质项
  （sphere_map / toon / edge）、外部贴图引用清单（texture_refs）。

### 导入 UE 5.8

把导出的 `.gltf` + `.bin` 拖入 UE 5.8 内容浏览器（glTF 导入），或使用适配层脚本：

```powershell
& "D:\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "<你的工程>.uproject" \
  -run=pythonscript -script="<repo>/adapters/ue5_8/import_gltf.py"
```

> ⚠️ adapters/ue5_8/ 按 UE 5.x Python API 编写，**尚未在真实 5.8 编辑器内运行验证**。
> 类/属性名（GltfImportOptions、FSkeletalMaterial 等）使用前请对照目标 5.8 stub 核对。

## 坐标与单位约定

- **PMX 坐标系**：DirectX 左手系，Y 向上，正面 -Z，角色左手侧 +X；骨骼
  `bone.position` 是**相对父骨骼的本地平移**（felixjones PMX 规范）。
- **glTF 坐标系**：右手系，Y 向上。导出器在**导出时**做手性转换——反射 X 轴
  （x → -x）并反转三角绕序，避免左右镜像；UV 的 V 轴同步翻转。
- **单位**：本阶段不缩放，保留 PMX 原单位（MMD 模型通常约 20 单位高）；米制归一
  与 scale/轴符号标定延后到真实资产标定里程碑（U3）。

## 项目布局

```
src/mmd2ue/
  core/
    ir.py                 # IR 数据结构与 ir_version（0.2.0）
    bezier.py             # VMD bezier 插值纯函数求值
    export/gltf.py        # model IR -> glTF 2.0（含手性转换）
    parsers/
      pmx.py              # PMX 2.0/2.1 解析（骨骼 tail/IK/付与/轴限制）
      vmd.py              # VMD 六块解析（CP932）
      vpd.py              # VPD 姿势解析
      pmm.py              # PMM 入口预留（抛 NotImplementedError）
  cli.py                  # CLI 五子命令
adapters/ue5_8/           # UE 适配层（import_gltf / material_map，仅此处 import unreal）
tools/
  verify_all.py           # 八步门禁
  gen_samples.py          # 自生成合成样例与金标（纯标准库）
docs/
  adr/                    # 架构决策记录 ADR-001..007
  stage1-requirements.md  # 第一阶段验收条款
  stage2-requirements.md  # 第二阶段验收条款
```

## 已知限制（v0.2.0）

- **QDEF**（PMX 2.1 weight type 4）：跳过该顶点蒙皮并计入 report.skipped，降级解析。
- **SDEF**：按 BDEF2 近似（丢 C/R0/R1）并计入 report.approximated。
- **材质**：仅 MMD 近似 PBR（diffuse→BaseColor、贴图→BaseColor 贴图）；sphere map /
  toon / edge 忽略并记入报告，不做 MToon 卡通着色。
- **贴图**：导出器不复制、不内嵌贴图；外部贴图须由用户放置到 .gltf 同级（uri 所指相对
  路径），清单见 report 的 texture_refs。
- **动作/镜头/物理**：VMD 已解析为 IR，但 → AnimSequence / Sequencer / SpringBone 的
  烘焙（M3/M4/M7）尚未实现；VMD bezier 仅提供求值函数，切线/速度应用延后。
- **未决项**：许可证类型（U1）、真实黑羽资产标定（U2/U3）、UE 导入路径实测（U4 已决
  glTF 路径）、借鉴范围核实（U5）——均如实记录，未宣称「全部通过」。

## 开发

```powershell
pip install -e .[dev]
python -m pytest tests/unit -q      # 单测（50 例）
python -m pytest tests/golden -q    # 金标（17 例）
python tools/verify_all.py          # 八步门禁（任何一步失败禁止合并）
```

门禁八步：① 单测 ② 金标比对 ③ 报告三键 ④ 许可证存在 ⑤ 资产泄漏 ⑥ glTF 金标
⑦ glTF 报告 ⑧ 分发树资产检查（git ls-files 无实体资产）。

## 许可证与资产边界

- 许可证：MIT（占位，类型待用户最终确认，见 ADR-003 / U1）。
- 仓库与分发包**不包含任何模型数据**（PMX/VMD/纹理/音频），仅含工具自身代码；
  测试用样例由 tools/gen_samples.py 程序化生成（ADR-006 / C5b）。
- 参考项目许可核实：VibeUE / MMD2Unreal / ue5-mmd-toolkit / VRMify（GPL-3.0）等，
  逐条核实后仅 clean-room 借鉴思路，不复制代码（ADR-003 / ADR-004）。
