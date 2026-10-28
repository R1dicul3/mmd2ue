# ADR-001 核心 / 适配层分离

状态：已接受（Accepted）

## 背景
MMD→UE5.8 转换工具需要解析 MMD 资产（PMX/VMD）并导入 UE 5.8。UE 内置 Python 解释器与标准 Python 环境不同，直接把解析逻辑与 UE API 耦合会造成核心逻辑无法独立测试与复用。

## 决策
将代码分为两层：
- `core/`：纯解析与 IR 生成，只用 Python 3.11+ 标准库，不 import unreal。
- `adapters/ue5_8/`：UE 适配层，调用 UE 内置 API，消费 core 产出的 IR。

IR 是唯一真相（single source of truth），核心与适配层通过 IR JSON 交换数据。

## 影响
- 核心解析器可在无 UE 环境下单测（约束 C2/C3）。
- 适配层可独立演进（M2+）。
- 每个 IR 产物带 `ir_version`，版本不匹配时拒绝加载（AC-M1-5）。

## 参考 / 借鉴范围
- 借鉴思路来源：MMD2Unreal、ue5-mmd-toolkit 的整体分层（clean-room，不复制代码）。
- 许可核实结论见 ADR-003。
