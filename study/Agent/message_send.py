from dataclasses import dataclass
from pydantic import BaseModel,Field
from autogen_agentchat.messages import TextMessage
from autogen_core import RoutedAgent,SingleThreadedAgentRuntime ,AgentId ,message_handler,MessageContext
import asyncio









@dataclass
class MyMessageType:
    content:str 
    
    
    
    
class MyMessageType2(BaseModel):
    content:str = Field(..., description="content")
    source: str = Field(default="unknown", description="消息来源")







class MyAgent(RoutedAgent):
    @message_handler
    async def on_text_message(self, message: TextMessage,ctx: MessageContext) -> None:
        """
        处理接收到的文本消息。

        当接收到文本类型的消息时，此异步方法会被调用。它主要用于打印消息来源
        以及用户发送的具体内容，常用于调试或简单的消息回声场景。

        Args:
            message (TextMessage): 包含消息具体内容及来源信息的文本消息对象。
            ctx (MessageContext): 消息处理的上下文环境，包含会话状态等额外信息。

        Returns:
            None: 此方法不返回任何值。
        """
        print(f"hello  {message.source},you said {message.content}")
        # 向 my_agent 发送一条消息
        await self.send_message(TextMessage(content="this is a message for my_agent2",source="my_agent"),AgentId(type='my_agent2',key='default'))
    
    @message_handler
    async def on_text_message1(self, message: MyMessageType2,ctx: MessageContext) -> None:
        print(f"hello  {message.source},you said {message.content}")


class MyAgent2(RoutedAgent):
    @message_handler
    async def on_text_message2(self, message: TextMessage,ctx: MessageContext) -> None:
        print(f"hello  {message.source},you said {message.content}")



async def main():
    """
    主异步入口函数，用于初始化代理运行时环境、注册代理实例、发送消息并停止运行。

    该函数演示了如何使用 SingleThreadedAgentRuntime 创建单线程代理运行时，
    注册一个 MyAgent 类型的代理，并向其发送一条文本消息，最后优雅地停止运行时。

    参数:
        无

    返回:
        无
    """
    runtime = SingleThreadedAgentRuntime()  #创建一个单线程的 Agent 运行时实例 runtime。这是管理 Agent 生命周期和消息调度的核心容器。
    await MyAgent.register(runtime,"my_agent",lambda: MyAgent("My Agent"))  #注册 MyAgent 类型的代理实例，并命名为 "my_agent"。 MyAgent("My Agent") # 工厂函数：返回一个新的 MyAgent 实例
    await MyAgent2.register(runtime,"my_agent2",lambda: MyAgent2("My Agent2"))
    runtime.start()  #启动 Agent 运行时，使其开始处理消息。 
    # 向已注册的代理发送一条来自用户的问候消息，并等待处理完成
    await runtime.send_message(TextMessage(content="hello Anson",source="user"), AgentId(type='my_agent',key='default'))
    await runtime.stop()  #优雅地停止运行时，释放资源。
    
    
    
    
    
    
if __name__ == "__main__":
    asyncio.run(main())