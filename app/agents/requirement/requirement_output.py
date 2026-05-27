


from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_core import RoutedAgent, message_handler, type_subscription,MessageContext
from autogen_agentchat.agents import AssistantAgent

from pathlib import Path
import sys
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
from app.conf.llms import kimi_llm
from app.models.messages import RequirmentMessage
import json
from loguru import logger  # pyright: ignore[reportMissingImports]
@type_subscription(topic_type='requirement_output')
class RequirementOutputAgent(RoutedAgent):
    def __init__(self):
        super().__init__('Requirement Output Agent') #这个智能体订阅了 一个名为 requirement_output 的消息主题
        self._prompt = """
        你是一位需求整理优化专家，根据上下文对话信息，输出用户最终期望的优化总结后的需求分析。
        必须输出合法的 JSON 格式，结构如下：
        {
            "requirements": [
                {
                    "name": "需求名称",
                    "description": "需求描述",
                    "priority": "优先级（高/中/低）",
                    "category": "需求分类（功能需求/非功能需求/业务规则/数据需求/接口需求）",
                    "acceptance_criteria": "验收标准",
                    "dependencies": "依赖项（无则填'无'）",
                    "notes": "备注（无则填'无'）"
                }
            ]
        }
        确保输出是纯 JSON，不要包含 markdown 代码块标记。
        """  #这个智能体的系统提示词
        
        
        
    @message_handler
    async def handle_message(self, message: RequirmentMessage,ctx: MessageContext) -> None:

        # 创建需求输出智能体
        output_agent = AssistantAgent(
            name="requirement_output_agent",
            model_client= kimi_llm,
            model_client_stream=True,
            system_message=self._prompt,
        )  
        
        # 发送给前端 状态描述
        task ="请根据以下需求分析，输出用户最终期望的优化总结后的需求分析。\n\n{message.content}"
        
        output_content = ""
        try:
            stream = output_agent.run_stream(task = task)
            async for msg in stream:
                if isinstance(msg,ModelClientStreamingChunkEvent):
                    # 发送给前端
                    continue
                if isinstance(msg,TaskResult):
                    last_message = msg.messages[-1]
                    if isinstance(last_message,TextMessage):
                        output_content = last_message.content
                        continue
            # 解析输出内容,确保输出的内容是有效的 json，将 json 格式的字符串解析为 Python 中的 dict
            parsed_output = json.loads(output_content)
            
            # 发送给前端
            
            # 发送给下一个智能体
        
        except json.JSONDecodeError as e:
            err_msg = f"需求输出解析出错,不是一个有效的json: {str(e)}"
            logger.error(err_msg)
            
            # 利用智能体修复 json 格式错误
            fix_agent = AssistantAgent(
                name="requirement_output_fix_agent",
                model_client= kimi_llm,
                model_client_stream=False,
                system_message=f"""
                你是一位经验丰富的json格式修复专家，根据上下文对话信息，输出用户最终期望的优化总结后的需求分析。
                你将获得一个可能格式不正确的的json格式的字符串，错误信息为{str(e)}你需要修复json格式错误，并输出修复后的json格式的字符串。
                确保输出符合以下结构:
                {
                    "requirements":[
                        {
                            "name":"...",
                            "description":"...",
                            ...其他字段...
                        }
                    ]
                }
                """
            )
            fix_result = await fix_agent.run(task = f"修复以下错误的 json 内容，将其修改为正确的 json 格式:\n\n{output_content}")
            last_message = fix_result.messages[-1]
            if isinstance(last_message,TextMessage):
                fixed_content = last_message.content            
            else:
                err_msg = f"修复结果不是文本消息: {fix_result}"
                logger.error(err_msg)
                raise json.JSONDecodeError(err_msg, output_content, 0)
           
            try:
                # 再次验证 
                parsed_output = json.loads(fixed_content) 
                
                # 发送给前端  json 修复成功
                # 发送给下一个智能体
            except json.JSONDecodeError as e:
                err_msg = f"修复结果不是有效的json: {str(e)}"
                logger.error(err_msg)

        except Exception as e:
            err_msg = f"需求输出出错: {str(e)}"
            logger.error(err_msg)
            raise e