# ADR-003 许可证结论（占位）

状态：草案（Draft，待用户确认，未决项 U1）

## 决策
许可证类型暂定为 MIT（LICENSE 已放占位文本）；候选为 MIT 或 Apache-2.0，**不引入 GPL 代码**。

## 参考项目许可核实结论
逐个核实参考项目许可证（待补全）：
- VibeUE：待核实。
- MMD2Unreal：待核实。
- ue5-mmd-toolkit：待核实。

GPL 或不明许可者仅 clean-room 借鉴思路，不复制代码。

## 同步义务（U1 关闭前生效）
- `pyproject.toml` 的 `license = { text = "MIT" }` 与 classifier `"License :: OSI Approved :: MIT License"` 暂按 MIT 填写，仅为占位，**不代表最终对外许可结论**。
- U1 若改判 Apache-2.0，必须同步修改 `pyproject.toml` 的 license 字段与 classifier，以及 `LICENSE` 正文，并重出分发包（重新 build sdist/wheel）。
- U1 关闭前，请勿以 OSI classifier 向外界宣称为最终许可。
