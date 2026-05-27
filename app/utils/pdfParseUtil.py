import glob
import os
import re
import sys
import tempfile
from pathlib import Path

import pymupdf4llm
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.picUtil import get_text_from_pic


def _pymupdf4llm_to_str(raw: object) -> str:
    """pymupdf4llm.to_markdown 可能返回 str 或按页结构 list，统一为 Markdown 字符串。"""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                t = item.get("text")
                parts.append(t if isinstance(t, str) else str(item))
            else:
                parts.append(str(item))
        return "\n\n".join(parts)
    return str(raw)


# 得到 PDF 的文本内容和生成图片
def get_content_and_pics(file_path):
    """
    从指定文件中提取Markdown格式的文本内容及图片。

    Args:
        file_path: 输入文件的路径，通常为PDF文件路径。

    Returns:
        str: 转换后的Markdown字符串内容。
    """
    raw = pymupdf4llm.to_markdown(
        doc=file_path,
        write_images=True,  # 启用图片写入功能
        image_path="imagess",
    )  # 指定图片保存路径
    return _pymupdf4llm_to_str(raw)

# 获取文件夹中的所有图片
def get_all_images(image_folder_path):
    supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    image_files = []
    for format in supported_formats:
        # images/*.jpg
        pattern = os.path.join(image_folder_path, f'*.{format}')
        # glob 主要用于文件路径名的匹配
        image_files.extend(glob.glob(pattern))
        
        #PNG JPG
        pattern_upper = os.path.join(image_folder_path, f'*{format.upper()}')
        image_files.extend(glob.glob(pattern_upper))
    return list(set(image_files))


# 将图片内容描述替换到 md 中（按图片目录解析 Markdown 里的图片引用）
def replace_content_with_pics(md_content: str, image_folder_path: str) -> str:
    image_folder_path = os.path.abspath(image_folder_path)

    def _resolve_image_path(img_ref: str) -> str | None:
        ref = img_ref.strip()
        candidates = [
            ref if os.path.isabs(ref) else None,
            os.path.normpath(os.path.join(image_folder_path, ref)),
            os.path.normpath(os.path.join(image_folder_path, os.path.basename(ref))),
        ]
        return next((c for c in candidates if c and os.path.isfile(c)), None)

    def _replacer(m: re.Match[str]) -> str:
        p = _resolve_image_path(m.group(1))
        if not p:
            return m.group(0)
        pic_content = get_text_from_pic(p)
        if not pic_content:
            return m.group(0)
        return f"-----图片展示----\n{pic_content}"

    return re.sub(r"!\[[^\]]*\]\(([^)]+)\)", _replacer, md_content)


def get_pdf_multimodal_text(file_path: str) -> str:
    """PDF 多模态：pymupdf4llm 转 Markdown，抽取图片并用 VLM 描述后并入文本。"""
    with tempfile.TemporaryDirectory(prefix="pdf_img_") as tmp:
        raw = pymupdf4llm.to_markdown(
            doc=file_path,
            write_images=True,
            image_path=tmp,
        )
        md_content = _pymupdf4llm_to_str(raw)
        return replace_content_with_pics(md_content, tmp)


def get_pdf_with_pics(file_path: str) -> str:
    """
    从指定文件中提取 Markdown 及内嵌图片的多模态描述文本。

    Args:
        file_path: 输入文件的路径，通常为 PDF 文件路径。

    Returns:
        str: 含图片 VLM 描述的合并文本。
    """
    return get_pdf_multimodal_text(file_path)