import base64
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.llms import client 
def get_text_from_pic(file_path: str) -> str:
    """获取图片文本
    """
    try:
        with open(file_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")

    
    # 创建聊天完成请求
        completion = client.chat.completions.create(
            model="qwen3-vl-plus",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                # "url": "https://img.alicdn.com/imgextra/i1/O1CN01gDEY8M1W114Hi3XcN_!!6000000002727-0-tps-1024-406.jpg"
                                "url": f'data:image/jpeg;base64,{image_base64}'
                            },
                        },
                        {"type": "text", "text": "请详细描述下这张图片？"},
                    ],
                },
            ],
            stream=False,
            # enable_thinking 参数开启思考过程，thinking_budget 参数设置最大推理过程 Token 数
            extra_body={
                'enable_thinking': True,
                "thinking_budget": 81920},
        )
        content = completion.choices[0].message.content
        return content if isinstance(content, str) else ""
    except Exception as e:
        print(f"获取文本失败: {e}")
        return ""


if __name__ == "__main__":
    print(get_text_from_pic("RAG/data/测试商品.jpg"))