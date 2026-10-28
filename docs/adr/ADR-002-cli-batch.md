# ADR-002 批处理走 CLI

状态：已接受（Accepted）

## 背景
转换工具需要支持一次性转换模型（PMX）、动作（VMD）、相机（VMD）多种输入；批处理应可由 CI / 脚本 / 用户手动触发。

## 决策
提供 CLI 入口 `src/mmd2ue/cli.py`（subcommand：inspect / convert-model / convert-motion / convert-camera），批处理通过 CLI 而非交互式 GUI 完成。

## 影响
- CI 门禁可调用 CLI 做端到端冒烟。
- 未来 UE 适配层可复用同一套核心解析器。

## 参考 / 借鉴范围
- 思路来源：通用 CLI 批处理模式（Python argparse subcommand 范式）。
- clean-room 声明：不复制任何第三方代码，仅采用「子命令 + 参数解析」的通用工程惯例。
- 许可核实指向 ADR-003。
