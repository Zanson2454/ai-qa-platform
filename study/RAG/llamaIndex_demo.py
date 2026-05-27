from llama_index.core import Settings
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.llms.deepseek import DeepSeek

llm = DeepSeek(model="deepseek-chat", api_key="sk-36eca0b473084e848bcff12ee6035cc5")
Settings.llm = llm

chat_engine = SimpleChatEngine.from_defaults()
# chat_engine.chat_repl()


chat_engine.streaming_chat_repl()

response = chat_engine.stream_chat("请用中文回答：常州历史悠久嘛？")
for token in response.response_gen:
    print(token, end="")