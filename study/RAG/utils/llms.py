from dotenv import load_dotenv
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.deepseek import DeepSeek
from openai import OpenAI
from utils.env_util import require_env

load_dotenv()

# 大语言模型
ds_llm = DeepSeek(
    model="deepseek-chat",
    api_key=require_env("ds_api_key"),
    temperature=0.5
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