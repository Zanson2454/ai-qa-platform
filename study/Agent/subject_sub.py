from autogen_core import RoutedAgent,message_handler,MessageContext, type_subscription
from autogen_agentchat.messages import TextMessage
from autogen_core import SingleThreadedAgentRuntime,DefaultTopicId
import asyncio
















# 这个智能体订阅了 一个名为 Anson 的消息主题
@type_subscription(topic_type='Anson')
class BroadcastAgent(RoutedAgent):
    @message_handler
    async def on_text_message(self, message: TextMessage,ctx: MessageContext) -> None:
        print(f"hello  {message.source},you said {message.content}!--1")



@type_subscription(topic_type='Anson')
class BroadcastAgent_2(RoutedAgent):
    @message_handler
    async def on_text_message2(self, message: TextMessage,ctx: MessageContext) -> None:
        print(f"hello  {message.source},you said {message.content} ! --2")


@type_subscription(topic_type='潍谷')
class BroadcastAgent_3(RoutedAgent):
    @message_handler
    async def on_text_message3(self, message: TextMessage,ctx: MessageContext) -> None:
        print(f"hello  {message.source},you said {message.content} ! --3")
        
        # 向另外一个主题发送消息
        await self.publish_message(
            TextMessage(content="hello Anson,this message from 潍谷!",source="broadcast_agent_3"), 
            topic_id = DefaultTopicId(type='Anson'))
        
        
        
async def main():
    runtime = SingleThreadedAgentRuntime()
    await BroadcastAgent.register(runtime,"broadcast_agent",lambda: BroadcastAgent("Broadcast Agent"))
    await BroadcastAgent_2.register(runtime,"broadcast_agent_2",lambda: BroadcastAgent_2("Broadcast Agent 2"))
    await BroadcastAgent_3.register(runtime,"broadcast_agent_3",lambda: BroadcastAgent_3("Broadcast Agent 3"))
    runtime.start()
    
    # 向主题发送消息
    await runtime.publish_message(
        TextMessage(content="hello Anson,this message from runtime",source="runtime"), 
        topic_id =  DefaultTopicId(type='潍谷'))
    
    
    
    await runtime.stop_when_idle() # 等待所有消息处理完成后再停止运行时
    
    
    
if __name__ == "__main__":
    asyncio.run(main())
    