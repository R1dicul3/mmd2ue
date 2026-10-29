# mmd2ue

MMD（PMX/VMD/VPD）→ UE5.8 转换工具。本仓库当前处于**第一阶段（M0 + M1）**：仓库/ADR/门禁脚手架 + PMX/VMD 解析器与金标。

## 约束

- 核心用 Python 3.11+，纯标准库优先；解析器不 import unreal、不依赖 UE。
- 核心（core/）与适配层（adapters/ue5_8/）分离；IR 是唯一真相。
- 仓库**不包含**任何 PMX/VMD/音频/借用贴图实体文件（见 .gitignore）。

## 已知限制（v1）

- PMX 权重类型 QDEF（PMX 2.1 合法，weight type 4）在 v1 中不被支持：解析器对其**跳过**该顶点的蒙皮数据并计入 `report["skipped"]`，使含 QDEF 的真实 2.1 资产可降级解析，而非整文件失败（见 ADR-004 / R14）。
- PMX SDEF 顶点按 BDEF2 近似并计入 `report["approximated"]`（丢 C/R0/R1）。
- VMD 名称 CP932 解码失败时保留 `<hex:...>` 并计入 `report["approximated"]`。
- VMD bezier 插值在 M1 提供纯函数求值（`mmd2ue.core.bezier`）；切线/速度应用延后至 M3。

## 布局

```
src/mmd2ue/
  core/
    ir.py                 # IR 数据结构与 ir_version
    export/
      gltf.py             # model IR -> glTF 2.0 导出器（M2）
    parsers/
      pmx.py              # PMX 2.0/2.1 解析
      vmd.py              # VMD（骨骼/表情/相机/光源/自阴影/IK）解析
      vpd.py              # VPD 姿势解析
      pmm.py              # PMM 入口预留（抛 NotImplementedError）
  cli.py                  # CLI：inspect / convert-model / convert-motion / convert-camera / export-gltf
tests/
  unit/                   # 单测
  golden/                 # 金标 IR JSON（自生成最小样本）
tools/
  verify_all.py           # 八步门禁（glTF 金标 / glTF 报告 / 分发树资产检查）
  gen_samples.py          # 自生成合成样例与金标 JSON（纯标准库）
docs/
  adr/                    # 架构决策记录
  stage1-requirements.md  # 第一阶段验收条款
```


## 第二阶段（M2）：glTF 导出 + UE 适配层

M2 走中间 glTF 路径（ADR-007，v1）：核心层 export_gltf 把 model IR 导出为
glTF 2.0（.gltf + 外部 .bin），UE 适配层 adapters/ue5_8/ 读取 glTF 经 UE
原生导入创建 SkeletalMesh。

### 贴图解析规则

- PMX 贴图路径（texture_index 指向的相对路径）原样写入 glTF images[].uri；
  导出器不复制、不嵌入、不随包分发贴图（ADR-006，零资产分发）。
- 外部 .bin：.gltf 的 buffers[0].uri 指向 export_gltf_files 实际写出的 .bin
  文件名（默认 model.bin），须与 .gltf 同级；换输出路径时 .bin 同名同目录。
- 外部贴图：贴图文件须由用户自行放置在 .gltf 同级（或 images[].uri 所指
  相对路径）供 UE 导入解析；导出器在 --report 的 texture_refs 里列出
  「material → 贴图 uri」清单，便于用户核对与落地。
- data: URI 内嵌（用户自带贴图时）在本阶段未实现，记入后续 M5 材质总报告。

### UE 适配层状态

adapters/ue5_8/（import_gltf.py / material_map.py）按 UE 5.x Python API 编写，
尚未在真实 Unreal 5.8 编辑器内运行验证。类/属性名（GltfImportOptions、
FSkeletalMaterial 等）须对照目标 5.8 Python stub 核对后再用于生产。

## 开发

```
pip install -e .[dev]
python -m pytest tests/unit -q
python tools/verify_all.py
```

## 门禁（verify_all.py 五步）

1. 单测（tests/unit）
2. 金标比对（tests/golden）
3. 转换报告检查（units/skipped/approximated 三键）
4. 许可证文件存在性检查
5. 资产泄漏检查（无 *.pmx / *.vmd 等实体资产）
