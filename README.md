# mmd2ue

MMD（PMX / VMD）→ Unreal Engine 5.8 转换工具，纯 Python，无外部依赖。

当前版本 **v0.2.0**。本工具是纯转换器：不包含、不分发任何模型数据，只转换你本地的
MMD 资产。

## 安装

需要 Python 3.11+。

```powershell
# 开发模式安装
pip install -e .[dev]

# 验证安装
mmd2ue --version
# → mmd2ue (IR 0.2.0)
```

## 已可用功能

- **PMX 2.0 / 2.1 解析**（UTF-16LE / UTF-8）：骨骼层级、顶点蒙皮、材质、表情、刚体/关节、
  骨骼 IK/付与/轴限制。
- **VMD 解析**（CP932 日文编码）：骨骼 / 表情 / 相机 / 光源 / 自阴影 / IK 六块。
- **模型 → glTF 2.0**：骨骼 + 蒙皮 + 材质近似（标准右手系，可直接导入 UE）。
- **模型 → IR JSON**、**动作 → IR JSON**、**相机 → IR JSON**：版本化中间表示。

## 使用

### 查看模型 / 动作概况

```powershell
mmd2ue inspect model.pmx
mmd2ue inspect motion.vmd
```

输出模型名、版本、编码、各数据块计数。

### 模型 → IR JSON

```powershell
mmd2ue convert-model model.pmx -o model.ir.json
```

### 动作 → IR JSON

```powershell
mmd2ue convert-motion motion.vmd -o motion.ir.json
```

### 提取相机轨迹

```powershell
mmd2ue convert-camera motion.vmd -o camera.ir.json
```

### 模型 → glTF 2.0

```powershell
mmd2ue export-gltf model.pmx -o model.gltf --bin model.bin
```

产物：`model.gltf`（glTF 2.0 JSON）+ `model.bin`（顶点/蒙皮/索引二进制），两者须同级。
可加 `--report report.json` 输出转换报告（含忽略的材质项、外部贴图清单）。

### 导入 UE 5.8

把导出的 `model.gltf` + `model.bin` 一起拖进 UE 5.8 内容浏览器即可。

注意：贴图不会随导出复制。若模型带贴图，请把 PMX 引用的贴图文件放到 `model.gltf`
同级目录（或 URI 所指相对路径），UE 导入时才能正确加载。
