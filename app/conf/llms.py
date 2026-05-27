from dotenv import load_dotenv
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.deepseek import DeepSeek
from openai import OpenAI
from utils.env_util import require_env
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

# 大语言模型
deepseek_model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    api_key=require_env("ds_api_key"),
    base_url=require_env("ds_base_url"),
    model_info = {
        "json_output": True, # 允许 json 输出
        "function_calling": True, # 允许函数调用
        "structured_output": True, # 允许结构化输出
        "vision":False ,#可视化
        "family": "unknown"
    },
)



kimi_llm = OpenAIChatCompletionClient(
    # model="kimi-k2.6",
    model="kimi-k2.6",
    api_key=require_env("kimi_api_key"),
    base_url="https://api.moonshot.cn/v1",
    model_info = {
        "json_output": True, # 允许 json 输出
        "function_calling": True, # 允许函数调用
        "structured_output": True, # 允许结构化输出
        "vision":False ,#可视化
        "family": "unknown",
        "multiple_system_messages": True
    }
)

# 嵌入模型
embedder_model = OllamaEmbedding(
    model_name=require_env("ollama_embedding_model"),
    base_url=require_env("ollama_base_url")
)

# 视觉模型
# 初始化OpenAI客户端
client = OpenAI(
    api_key = require_env("qwen3_api_key"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)



