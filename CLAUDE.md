# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 环境初始化

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 版本：3.12（`.python-version`）。

## 代码风格

- 生成的代码都需要有中文注释，准确说明关键逻辑、边界处理和异常处理意图。
- 避免无意义注释（例如重复代码字面含义的注释）。

## 架构概览

项目是一个基于 AutoGen 多智能体框架的 AI 测试需求分析平台。核心流程：上传需求文档 → 智能体提取分析 → 输出结构化测试需求 JSON。

### 三阶段 Agent 流水线

Agent 通过 AutoGen 的 Topic 发布/订阅机制串联，定义在 `app/agents/requirement/`：

1. **RequirementAcquireAgent**（入口）— 接收文件（PDF/Word/图片），RAG 入库到 Milvus，用 Kimi LLM 总结需求，支持人工介入（UserProxyAgent）。发布到 `requirement_analysis` topic。
2. **RequirementAnalysisAgent** — 对需求进行整理优化。发布到 `requirement_output` topic。
3. **RequirementOutputAgent** — 输出结构化 JSON，含 JSON 修复容错机制。

消息体定义在 `app/models/messages.py`：`RequirmentFileMessage`（文件输入）、`RequirmentMessage`（Agent 间传递）。

### 技术栈

- **Agent 框架**：Microsoft AutoGen（`autogen_core` + `autogen_agentchat`）
- **RAG**：LlamaIndex + Milvus 远程向量库
- **嵌入模型**：Ollama 本地 `qwen3-embedding:0.6b`
- **主 LLM**：Kimi K2.6（Moonshot API），配置在 `app/conf/llms.py`
- **视觉模型**：Qwen3-VL（阿里云 DashScope），用于 PDF 图片描述
- **PDF 解析**：PyMuPDF4LLM，支持图文多模态提取

### 已知问题

- `app/conf/llms.py` 导入路径使用 `from utils.env_util import ...`（非 `app.utils`），与 agents 目录下的导入方式不一致，可能源于代码从 `study/` 迁移未完全调整。
- `study/` 与 `app/utils/` 存在大量重复代码（ragUtil、pdfParseUtil、picUtil 等），study 为早期实验代码。
- 无统一应用入口，各 Agent 仅有 `__main__` 测试块。
