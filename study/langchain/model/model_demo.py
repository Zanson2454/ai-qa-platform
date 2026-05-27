import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_deepseek import ChatDeepSeek   

load_dotenv()

#v1.0
deepseek_llm = init_chat_model(
    model="deepseek-v4-flash",
    api_key=os.getenv("ds_api_key"),
    base_url=os.getenv("ds_base_url"),
)

deepseek_llm2 = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=os.getenv("ds_api_key"),
)


response = deepseek_llm2.invoke("请问 python 怎么学")
print(response)

# 流式输出