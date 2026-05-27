from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from  autogen_core import AgentId, DefaultTopicId, RoutedAgent, SingleThreadedAgentRuntime, TopicId,message_handler,MessageContext, type_subscription
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType   
from autogen_agentchat.base import TaskResult
import docx2txt
import asyncio

from typing import List
import sys
from pathlib import Path

from app.conf.llms import kimi_llm
from app.models.messages import RequirmentMessage
from loguru import logger

@type_subscription(topic_type='requirement_analysis')
class RequirementAnalysisAgent(RoutedAgent):
    def __init__(self):
        super().__init__('Requirement Analysis Agent')
        self._prompt = """
        你是一位需求整理优化专家，负责对原始需求进行结构化分析，为后续测试需求生成奠定基础。
        请按以下维度逐一分析每条需求，以结构化 Markdown 格式输出：

        ## 需求名称
        [简洁的需求名称]

        ## 需求描述
        [详细描述需求的具体内容和期望行为]

        ## 优先级
        [高/中/低，并说明判断依据]

        ## 需求分类
        [功能需求/非功能需求/业务规则/数据需求/接口需求]

        ## 验收标准
        [明确的、可验证的验收条件]

        ## 依赖项
        [该需求依赖的其他需求、系统或条件，无则填"无"]

        ## 备注
        [补充说明、潜在风险或待确认点，无则填"无"]

        对每条需求重复以上结构，确保分析全面、无遗漏。
        """
        
    @message_handler
    async def handle_message(self, message: RequirmentMessage,ctx: MessageContext) -> None:
        try:
            # 获取需求分析内容
            requirement_analysis_content = message.content
            
            # 创建需求分析智能体
            requirement_analysis_agent = AssistantAgent(
                name="requirement_analysis_agent",
                model_client= kimi_llm,
                model_client_stream=True,
                system_message=self._prompt,
            )  
            logger.info(f"开始需求分析")
            
            #向前端发送消息
            
            task = "请根据以下需求进行需求分析，并输出规范的需求分析报告\n\n{requirement_analysis_content}"
            analysis_report = ""
            stream = requirement_analysis_agent.run_stream(task = task)
            async for msg in stream:
                if isinstance(msg,ModelClientStreamingChunkEvent):
                    print(msg.content,end="")
                    continue
                if isinstance(msg, TaskResult):
                    last_message = msg.messages[-1]
                    # TaskResult 可能包含事件消息，先收窄为文本消息再读取内容。
                    if isinstance(last_message, TextMessage):
                        analysis_report = last_message.content
            
            
            # 发送给下一个智能体 requirement_output
            
            await self.publish_message(
                RequirmentMessage(
                    source=self.id.key,
                    content=analysis_report
                ),
                topic_id = TopicId(
                    type ='requirement_output',
                    source =self.id.key)
            )
            
        except Exception as e:
            err_msg = f"需求分析出错: {str(e)}"
            print(err_msg)