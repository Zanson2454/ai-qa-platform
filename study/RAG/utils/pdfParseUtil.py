import glob
import pymupdf4llm
import os
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.picUtil import get_text_from_pic

# 得到 PDF 的文本内容和生成图片
def get_content_and_pics(file_path):
    """
    从指定文件中提取Markdown格式的文本内容及图片。

    Args:
        file_path: 输入文件的路径，通常为PDF文件路径。

    Returns:
        str: 转换后的Markdown字符串内容。
    """
    md_content = pymupdf4llm.to_markdown(
        doc=file_path,
        write_images=True, # 启用图片写入功能
        image_path="imagess") #指定图片保存路径
    return md_content

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


# 将图片内容描述替换到 md 文件夹中
def replace_content_with_pics(md_content):
    # 获取所有图片
        image_files = get_all_images("images")
        for tmp_image in image_files:
            # 解析图片
            pic_content = get_text_from_pic(tmp_image)
            # 将图片内容描述替换到 md 文件夹中
            if pic_content:
                # 构建图片标记
                image_tag = f"![]({tmp_image})"
                # 将图片内容描述替换到 md 文件夹中
                md_content = md_content.replace(image_tag, f"-----图片展示----\n{pic_content}")

        return md_content
    
    
    
    
def get_pdf_with_pics(file_path):
    """
    从指定文件中提取Markdown格式的文本内容及图片。

    Args:
        file_path: 输入文件的路径，通常为PDF文件路径。

    Returns:
        str: 转换后的Markdown字符串内容。
    """
    md_content = get_content_and_pics(file_path)
    result_content = replace_content_with_pics(md_content)
    return result_content