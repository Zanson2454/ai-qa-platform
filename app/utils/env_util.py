"""环境变量读取，避免仅校验 env 时拖入 llama_index 等重依赖。"""

import os
def require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise ValueError(f"缺少环境变量: {key}")
    return value
