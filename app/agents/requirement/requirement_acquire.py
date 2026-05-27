from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage, UserInputRequestedEvent
from autogen_core import AgentId, DefaultTopicId, RoutedAgent, SingleThreadedAgentRuntime, TopicId,message_handler,MessageContext, type_subscription
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

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
from app.models.messages import RequirmentFileMessage,RequirmentMessage
from app.utils.ragUtil import NormalDocumentRAG
from app.utils.pdfParseUtil import get_pdf_multimodal_text
from app.utils.picUtil import get_text_from_pic
from app.conf.llms import kimi_llm



@type_subscription(topic_type='requirment_acquire')
class RequirementAcquireAgent(RoutedAgent):
    
    
    
    def __init__(self,input_func=None):
        super().__init__('Requirement Acquire Agent')
        self.input_func = input_func      
        
    @message_handler
    async def handle_message(self, message: RequirmentFileMessage,ctx: MessageContext) -> None:
        try:
            # RAG 入库
            rag = NormalDocumentRAG(files=message.files)
            # 文档内容  用多模态模型获取文档内容
            doc_content = rag.load_file()
            
            # 拼接集合名
            collection_name = f"project_{message.project_id}"
            
            # 保存到向量数据库中
            await rag.create_remote_index(collection_name=collection_name) 
            
            #发送到前端  PDF 解析成功
            acquisition_agent = AssistantAgent(
                name="requirement_acquire_agent",
                model_client= kimi_llm,
                model_client_stream=True,
                system_message="""
                你是一位专业的软件需求分析师，专长于从原始需求文档中提取关键信息，以支持后续的软件测试活动。请仔细阅读并理解提供的需求文档（可能包含文本、图表、流程图信息），然后进行整理和摘要。重点提取和归纳以下信息：

                1. **主要功能需求**：清晰描述系统应具备的核心功能。
                2. **非功能性需求**：如性能指标、安全性要求、可用性、兼容性等。
                3. **业务背景与目标**：解释该需求的业务价值和要解决的问题。
                4. **用户角色与关键使用场景**：识别不同的用户类型及其典型交互流程。
                5. **核心术语与概念定义**：列出并解释文档中的关键名词或特殊概念。
                6. **数据需求**：涉及的关键数据结构、输入/输出数据格式等。
                7. **依赖关系与约束**：识别与其他系统/模块的依赖或技术/环境限制。
                8. **潜在歧义与待确认点**：标记出文档中描述不清，可能存在多种解释或需要进一步澄清的部分。

                请以结构化、层次清晰的 Markdown 格式输出你的分析摘要，确保信息准确简洁后，为后续生成详细的测试需求奠定基础。
                """
            )
            
            
            acquistion_content = ""
            # 需要人为介入
            if self.input_func:
                user_proxy = UserProxyAgent(
                    name="user_proxy_agent",
                    input_func=self.input_func,
                )
                
                termination_en = TextMentionTermination("APPROVE")
                termination_cn = TextMentionTermination("同意")
                team = RoundRobinGroupChat([acquisition_agent, user_proxy],
                termination_condition = termination_en | termination_cn,
                )
                stream = team.run_stream(task = f"请对如下需求文档进行归纳总结:\n\n{doc_content[0].text}")
                
                # 用来记录用户介入的次数
                update_count = 0
                
                
                # 用来保存对话历史
                acquisition_memory = ListMemory()
                
                
                async for msg in stream:
                    # 流式输出
                    if isinstance(msg,ModelClientStreamingChunkEvent):
                        #前端输出
                        print(msg.content,end="")
                        continue
                    
                    #问题&智能体返回
                    if isinstance(msg,TextMessage):
                        # 记录对话历史
                        await acquisition_memory.add(
                            MemoryContent(
                                content = msg.model_dump_json(),mime_type = MemoryMimeType.JSON
                            )
                        )
                        
                        if msg.source == 'requirement_acquire_agent':
                            update_count += 1
                            acquistion_content = msg.content
                            continue
                    # 用户介入
                    if isinstance(msg,UserInputRequestedEvent) and msg.source == 'user_proxy_agent':
                        print("请输入你的意见")
                        continue
                        
                if update_count > 1: #表示用户已经介入
                    # 整合智能体
                    summarize_agent= AssistantAgent(
                        name="summarize_agent",
                        model_client= kimi_llm,
                        model_client_stream=True,
                        system_message="""
                        你是一位需求整理优化专家，根据上下文对话信息，输出用户最终期望的优化总结后的需求分析。
                        """,
                        memory = [acquisition_memory],
                    )
                    stream = summarize_agent.run_stream(task = f"结合上下文对话信息，输出完整需求分析，markdown 格式输出。")
                    
                    async for msg in stream:
                        if isinstance(msg,ModelClientStreamingChunkEvent):
                            print(msg.content,end="")
                            continue
                        
                        if isinstance(msg,TaskResult):
                            last_message = msg.messages[-1]
                            # TaskResult 可能包含事件消息，先收窄为文本消息再读取内容。
                            if isinstance(last_message, TextMessage):
                                acquistion_content = last_message.content
                            
                
            #不需要人工介入
            else:
                stream = acquisition_agent.run_stream(task = f"请对如下需求文档进行归纳总结:\n\n{doc_content[0].text}")
                async for msg in stream:
                    if isinstance(msg,ModelClientStreamingChunkEvent):
                        print(msg.content,end="")
                        continue
                    
                    if isinstance(msg,TaskResult):
                        last_message = msg.messages[-1]
                        # TaskResult 可能包含事件消息，先收窄为文本消息再读取内容。
                        if isinstance(last_message, TextMessage):
                            acquistion_content = last_message.content
                        continue
            
            # 向需求分析主题发送消息
            await self.publish_message(
                RequirmentMessage(
                    source=self.id.key,
                    content=acquistion_content
                    ), 
                    topic_id = TopicId(
                        type ='requirement_analysis',
                        source =self.id.key))
            
            
        except Exception as e:
            err_msg = f"需求获取出错: {str(e)}"
            print(err_msg)
        
        
    
async def main():
    # 定义消息主体
    requirement_files =  RequirmentFileMessage(
        user_id= 12,
        project_id=1111,
        files=['RAG/data/PUR_PRD_v1.pdf'],
        task="请分析需求文档"
    )
    runtime = SingleThreadedAgentRuntime()
    await RequirementAcquireAgent.register(runtime,"requirement_acquire_agent",lambda: RequirementAcquireAgent(input_func=input))
    runtime.start()
    await runtime.publish_message(requirement_files, topic_id = DefaultTopicId(type='requirement_acquire'))
    await runtime.stop_when_idle()
        
if __name__ == "__main__":
    
    asyncio.run(main())