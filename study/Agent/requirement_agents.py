import logging

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from llama_index.core import SimpleDirectoryReader
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination,MaxMessageTermination,SourceMatchTermination
from autogen_agentchat.messages import StructuredMessage,TextMessage
from typing import Any
import asyncio
import json
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
from Agent.llms import deepseek_model_client,deepseek_model_client2
from Agent.models import Requirementlist


# 抑制 autogen 默认 INFO：消息调度说明与 autogen_core.events 中的大段 payload JSON
for _autogen_log in ("autogen_core", "autogen_core.events", "autogen_core.trace"):
    logging.getLogger(_autogen_log).setLevel(logging.WARNING)


# Python 3.12 下参数化泛型的 __name__ 为 "StructuredMessage[Requirementlist]"，
# MessageFactory 默认只登记了 "StructuredMessage"，必须在 GroupChat 中显式登记。
RequirementlistStructuredMessage = StructuredMessage[Requirementlist]


class  RequirementAnalysisAgent:
    def __init__(self,files:list[str]):
        self.files = files
    
    async def get_file_content(self):
        """获取文件内容"""
        try:
            data = SimpleDirectoryReader(input_files=self.files).load_data()
            doc = "\n\n".join([d.text for d in data[::]])
            return doc
        except Exception as e:
            return f"读取文件失败: {str(e)}"
    async def create_team(self):
        """
        创建需求分析团
        1. 需求获取智能体
        2. 需求分析智能体
        3. 需求输出智能体
        """
        # 需求获取智能体
        requirement_acquire_agent = AssistantAgent(
            name="requirement_acquire_agent",
            model_client= deepseek_model_client,
            model_client_stream=False,
            tools = [self.get_file_content],
            system_message="""
            你是一个数据获取助手，当用户要求进行需求分析时，你必须
            1. 必须先调用 get_file_content工具，获取文档内容
            2. 然后将获取到的完整文档直接输出
            3. 确保只提供原始内容,不做其他处理
            """
        )
        
        # 需求分析智能体
        requirement_analyze_agent = AssistantAgent(
            name="requirement_analyze_agent",
            model_client= deepseek_model_client,
            model_client_stream=False,
            system_message="""
                # Role
                你是一位拥有 10 年以上大型 ERP 或复杂分布式系统经验的**资深软件测试架构师**。你擅长通过“剥洋葱”的方式，将模糊的业务需求拆解为具备严密逻辑的测试模型，并能精准识别隐藏的系统风险和逻辑断层。

                # Task & Workflow
                1. **获取数据**：你必须首先根据 `requirement_acquire_agent` 获取文档原始内容。
                2. **深度解构**：基于获取的内容，生成一份面向测试执行的**《需求逻辑分析手册》**。
                3. **分析维度**：
                - **业务流程建模**：识别主路径（Happy Path）、分支路径（Alternative Path）和异常流（Exception Path）。
                - **状态机与生命周期**：提取核心实体的状态转换触发条件及流转约束。
                - **数据契约与校验**：提取核心实体的属性约束（类型、长度、必填、唯一性、业务规则）。
                - **隐性逻辑探测**：挖掘文档未明说的前置依赖、后置影响以及跨模块联动。

                # Output Format (Markdown)

                ## 1. 业务目标与价值概览
                > 简述业务解决的核心痛点及用户成功路径。

                ## 2. 核心实体及其生命周期
                > 识别系统中的关键对象，并描述其状态流转逻辑。
                * **实体名**：[如：采购订单]
                * **关键属性**：[属性A(类型/约束), 属性B...]
                * **状态机**：[状态A] -> (触发动作) -> [状态B]

                ## 3. 详细逻辑规则矩阵 (Logic Matrix)
                | 模块/功能 | 业务规则/校验逻辑 | 前置条件 | 后置状态/预期结果 |
                | :--- | :--- | :--- | :--- |
                | [子模块] | 详细描述规则（含边界值/逆向逻辑） | 进入该场景必须满足的系统状态/权限 | 操作后的数据变更、接口响应或UI反馈 |

                ## 4. 关键测试关注点 (P0/P1 优先级)
                > 重点关注高频高危场景（如：资损风险、高并发冲突、数据一致性、权限越权）。

                ## 5. 需求澄清与潜在冲突 (Gap Analysis)
                > **【重要】** 列出文档中描述模糊、逻辑自相矛盾、未覆盖的边界情况或潜在的工程实现风险。

                # Constraints
                - **严禁虚构**：所有分析必须有文档出处，禁止生成通用的测试建议。
                - **深度优先**：优先分析复杂逻辑（如：折扣算法、库存分账、权限互斥），而非简单的页面布局。
                - **数学表达**：涉及金额、数量、比例等逻辑，使用精确的数学逻辑描述（如：`可用库存 = 总库存 - 冻结库存`）。
                - **工具调用**：必须先执行工具获取全文，严禁在未读取文档的情况下进行猜测分析。
            """
        )

        # 格式化输出智能体
        requirement_output_agent = AssistantAgent(
            name="requirement_output_agent",
            model_client= deepseek_model_client2,
            model_client_stream=False,
            output_content_type= Requirementlist,
            system_message="""
                # Role
                你是一个高精度的数据结构化助手，专长是将非结构化的软件需求分析文档转换为严格的 JSON 结构。你能够精准识别业务逻辑中的实体关系、优先级和任务属性。

                # Task
                你必须将 `requirement_analyze_agent` 输出的深度分析报告转换为符合以下 Pydantic 模型定义的结构化数据。

                # Mapping Rules (统一格式映射)
                请严格按照以下标准提取并映射每一个字段，确保逻辑严密：
                requirements: list[Requirement]
                - `requirement_name`: [需求名称]（提取具体的测试逻辑点或功能点名称）。
                - `requirement_type`: [需求类型：功能需求/安全需求/性能需求]（严格限制在此三类中选择）。
                - `parent_requirement`: [父需求]（识别该逻辑点所属的上级业务流或大模块，若无则为 null）。
                - `model`: [所属模块]（归属的 ERP 业务子模块，如：采购、库存、财务）。
                - `requirement_level`: [需求级别：高/中/低]（根据分析中的 P0/P1/P2 进行转换）。
                - `estimated_time`: [预计完成时间]（根据逻辑复杂度估算该点的测试设计时长，单位：小时，必须为整数）。
                - `description`: [需求描述]（提取该点的核心约束规则、前置条件及预期结果）。

                # Constraints
                - **纯净 JSON**：输出必须是一个标准的 JSON 对象，且必须被包裹在 `requirements` 列表中。
                - **严禁废话**：直接输出 JSON 代码块，严禁包含任何前缀、后缀或对字段的解释说明。
                - **数据类型**：`estimated_time` 必须为整数（Integer），`parent_requirement` 在无值时必须为 null 而非空字符串。
                - **忠实原文**：所有信息必须源自 `requirement_analyze_agent` 的输出，严禁虚构需求。
                - **格式一致性**：确保每一条记录都包含上述所有 7 个字段，缺失信息需根据常理进行合理推断或标注为 null。
                
                # Output Format Example
                ```json
                {
                "requirements": [
                    {
                    "requirement_name": "采购订单审批状态同步",
                    "requirement_type": "功能需求",
                    "parent_requirement": "采购流程自动化",
                    "model": "采购管理",
                    "requirement_level": "高",
                    "estimated_time": 3,
                    "description": "校验当 OA 系统审批通过后，ERP 系统内采购订单状态应实时从‘审批中’变更为‘已生效’，并触发库存占用。"
                    }
                ]
                }
            """
        )
        source_termination = SourceMatchTermination(sources=["requirement_output_agent"])
        team = RoundRobinGroupChat(
            [requirement_acquire_agent, requirement_analyze_agent, requirement_output_agent],
            termination_condition=source_termination,
            custom_message_types=[RequirementlistStructuredMessage],
        )
        return team

# 关键修正 4：增加执行入口保护
if __name__ == "__main__":
    file = ["RAG/data/PUR_PRD_v1.pdf"]
    requirement_agent = RequirementAnalysisAgent(file)
    team = asyncio.run(requirement_agent.create_team())
    asyncio.run(Console(team.run_stream(task="分析下这个需求文档，并输出需求分析报告")))