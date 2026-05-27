from pydantic import BaseModel, Field
from typing import List, Any
from dataclasses import dataclass



class RequirmentFileMessage(BaseModel):
    user_id: int = Field(..., description="用户ID")
    project_id: int = Field(default=1, description="项目ID")
    files: List[str] = Field(..., description="文件列表")
    task : str = Field( default="请分析需求文档", description="任务描述")
    

@dataclass  
class RequirmentMessage(BaseModel):
    content : Any  # 可以接受任意类型的数据
    source : str = Field(default="unknown", description="消息来源")