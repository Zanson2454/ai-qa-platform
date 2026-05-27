from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from RAG.utils.env_util import require_env


load_dotenv()

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



deepseek_model_client2 = OpenAIChatCompletionClient(
    model="deepseek-chat",
    api_key=require_env("ds_api_key"),
    base_url=require_env("ds_base_url"),
    model_info = {
        "json_output": True, # 允许 json 输出
        "function_calling": True, # 允许函数调用
        "structured_output": True, # 允许结构化输出
        "vision":False ,#可视化
        "family": "unknown"
    }
)

deepseek_model_case = OpenAIChatCompletionClient(
    model="deepseek-chat",
    api_key=require_env("ds_api_key"),
    base_url=require_env("ds_base_url"),
    model_info = {
        "json_output": True, # 允许 json 输出
        "function_calling": True, # 允许函数调用
        "structured_output": True, # 允许结构化输出
        "vision":False ,#可视化
        "family": "unknown"
    }
)









