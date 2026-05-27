from pydantic import BaseModel, Field
from typing import Optional


class Requirement(BaseModel):
    # Field:  用于定义字段的元数据，验证规则，描述信息
    # ... 代表必填
    requirement_name: str = Field(..., description="需求名词")
    requirement_type: str = Field(..., description="需求类型")

    # Optional 类型注解，用于表示一个值可以是某种类型买也可以是None
    # Optional[T] 代表T类型的变量，可以是 T 类型值，也可以是 None
    parent_requirement: Optional[str] = Field(None, description="父需求")

    model: str = Field(..., description="所属模块")
    requirement_level: str = Field(..., description="需求级别")
    estimated_time: int = Field(..., description="预计完成时间")
    description: str = Field(..., description="需求描述")


class Requirementlist(BaseModel):
    requirements: list[Requirement] = Field(..., description="需求列表")



class TestCase(BaseModel):
    # Field:  用于定义字段的元数据，验证规则，描述信息
    # ... 代表必填
    id: int = Field(..., description="用例编号")
    case_code: str = Field(..., description="用例编码")
    title: str = Field(..., description="用例标题")
    category: str = Field(..., description="用例分类")
    priority: str = Field(..., description="优先级")
    pre_conditions: str = Field(..., description="前置条件")
    test_steps: str = Field(..., description="测试步骤")
    expected_results: str = Field(..., description="预期结果")
    test_data: dict = Field(..., description="测试数据")
    description: str = Field(..., description="用例描述")
   

class Testcaselist(BaseModel):
    test_cases: list[TestCase] = Field(..., description="用例列表")
