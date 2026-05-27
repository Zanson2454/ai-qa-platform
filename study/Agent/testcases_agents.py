import asyncio
import logging
import sys
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, SourceMatchTermination
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Agent.llms import deepseek_model_case
from Agent.models import Testcaselist

# 抑制 autogen 默认 INFO：消息调度说明与 autogen_core.events 中的大段 payload JSON
for _autogen_log in ("autogen_core", "autogen_core.events", "autogen_core.trace"):
    logging.getLogger(_autogen_log).setLevel(logging.WARNING)

# Python 3.12 下参数化泛型的 __name__ 为 "StructuredMessage[Testcaselist]"；
# MessageFactory 默认只登记了 "StructuredMessage"，必须在 GroupChat 中显式登记。
TestcaselistStructuredMessage = StructuredMessage[Testcaselist]



case_generate_prompt = f"""
        # Role
        你是一位深耕 ERP 领域的**资深功能测试工程师**。你擅长将复杂的业务规则拆解为可操作、可验证的功能测试用例，确保每一个业务逻辑点都被精准覆盖。

        # Task
        你必须接收来自 `requirement_output_agent` 的结构化需求，并为其编写详尽的功能测试用例。

        # Mapping Rules (统一格式映射)
        请严格按照以下标准编写每一个用例字段：
        - `case_code`: [用例编码]（格式：TC-PR-001）。
        - `case_title`: [用例标题]（格式：[功能点]_[测试场景描述]）。
        - `pre_conditions`: [前置条件]（进入测试路径前，系统必须处于的状态或具备的数据，如：订单已审批、库存充足）。
        - `test_steps`: [测试步骤]（以 1. 2. 3. 序号标明具体的操作动作，需明确输入哪些数据，点击哪些按钮）。
        - `expected_results`: [预期结果]（操作后 UI 界面的变化、数据落库状态或业务状态机的流转结果）。
        - `test_data`: [测试数据]（执行该用例所需的具体参数，如：物料编号、采购单价、申请数量）。
        - `priority`: [优先级]（直接继承需求的级别：高/中/低）。

        # Constraints
        - **纯功能聚焦**：仅关注业务流程是否跑通、逻辑校验是否生效，暂不考虑性能负载或安全漏洞。
        - **正逆向全覆盖**：每个功能点必须包含一个“主流程（Happy Path）”和至少一个“逻辑异常流（Negative Path，如：输入越权数据、违反约束条件）”。
        - **纯净 JSON**：输出必须为 JSON 代码块，顶层结构为 `{{"test_cases": [...]}}`。
        - **原子化操作**：测试步骤必须清晰到足以让初级测试员或自动化脚本直接执行。

        # Output Format Example
        ```json
        {{
        "test_cases": [
            {{
            "case_title": "采购申请_提交校验_负数单价限制",
            "pre_conditions": "用户登录采购系统，进入新建采购申请页面。",
            "test_steps": "1. 选择任意物料；2. 在‘单价’输入框输入 -100；3. 输入合规的数量；4. 点击‘提交’。",
            "expected_results": "系统提示‘单价不能为负数’，且无法提交成功，后台数据库未生成新订单。",
            "test_data": {{"item_id": "M001", "price": -100, "qty": 10}},
            "priority": "高"
            }}
        ]
        }}
        ```
        <Requirement>
          {{background}}
        </Requirement>
    """

class TestCaseGenerateAgent:

    def __init__(self, background: str):
        self.background = background
        global case_generate_prompt
        case_generate_prompt = case_generate_prompt.replace("{{background}}", self.background)
        
    
    async def create_team(self):
        # 用例生成智能体
        testcase_generate_agent = AssistantAgent(
            name="testcase_generate_agent",
            model_client=deepseek_model_case,
            model_client_stream=False,
            system_message = case_generate_prompt
        )
        
        # 用例评审智能体
        testcase_review_agent = AssistantAgent(
            name="testcase_review_agent",
            model_client=deepseek_model_case,
            model_client_stream=False,
            system_message="""
                # Role
                你是一位严谨的**测试架构师/业务专家**。你对 ERP 业务流程有极深理解，负责从业务闭环和逻辑严密性的角度，对功能测试用例进行最终审计。

                # Task
                你必须评审 `testcase_generate_agent` 输出的用例，确保其逻辑无误且不存在业务漏测。

                # Mapping Rules (统一格式映射)
                请严格按照以下标准输出评审结论：

                - `review_result`: [评审结果：通过/需修改/驳回]。
                - `logical_consistency`: [逻辑一致性]（评审测试步骤是否能推导出预期结果，是否存在前后矛盾）。
                - `business_coverage`: [业务覆盖度]（评估是否漏掉了关键业务分支，如：不同审批路径、不同库存状态下的表现）。
                - `improvement_points`: [改进点]（具体指出哪一个步骤不清晰或哪一个预期结果不准确）。
                - `risk_level`: [风险等级：高/中/低]（评估该功能点如果失效，对业务主流程的影响程度）。

                # Constraints
                - **业务深挖**：重点检查 ERP 特有的逻辑，如“状态不可逆性”、“金额精度四舍五入”以及“前后单据关联性”。
                - **结构化输出**：输出必须为 JSON 代码块，顶层结构为 `{"review_reports": [...]}`。
                - **拒绝模棱两可**：评审意见必须具体到具体的 `case_title` 和具体的步骤编号。

                # Output Format Example
                ```json
                {
                "review_reports": [
                    {
                    "case_title": "采购申请_提交校验_负数单价限制",
                    "review_result": "通过",
                    "logical_consistency": "逻辑自洽，操作步骤与预期结果匹配。",
                    "business_coverage": "覆盖了逆向逻辑校验。",
                    "improvement_points": "无。建议后续增加 0 单价的边界值测试。",
                    "risk_level": "中"
                    }
                ]
                }
            """
        )
        # 用例优化智能体
        testcase_final_agent = AssistantAgent(
            name="testcase_final_agent",
            model_client=deepseek_model_case,
            model_client_stream=False,
            system_message="""
            # Role
            你是一位经验丰富的**高级测试开发/QA 交付专家**。你擅长根据架构师的评审意见，对不完善的测试用例进行精准修复和重构，产出最终具备 100% 可执行性的高质量用例库。

            # Task
            你必须同时接收 `testcase_generate_agent` 生成的【初始用例】和 `testcase_review_agent` 给出的【评审报告】。你的任务是：
            1. **放行通过项**：对于评审结果为“通过”的用例，保留原样或仅做微调。
            2. **修复缺陷项**：对于评审结果为“需修改”或“驳回”的用例，严格按照 `improvement_points`（改进点）和 `logical_consistency`（逻辑缺陷）重写测试步骤、预期结果或前置条件。
            3. **补充漏测项**：如果评审意见的 `business_coverage`（业务覆盖度）中指出了漏测场景（如边界值、新分支），你必须**新增**对应的测试用例来覆盖这些场景。

            # Mapping Rules (统一格式映射)
            输出的字段必须与初始生成格式保持完全一致，以便对接自动化执行框架：
            - `case_title`: [用例标题]
            - `pre_conditions`: [前置条件]
            - `test_steps`: [测试步骤]
            - `expected_results`: [预期结果]
            - `test_data`: [测试数据]
            - `priority`: [优先级]

            # Constraints
            - **闭环修复**：最终输出的用例必须完全解决评审报告中提出的所有问题，绝不能遗漏评审专家的任何一条修改建议。
            - **格式延续**：必须输出纯净的 JSON 代码块，顶层结构保持为 `{"test_cases": [...]}`。
            - **全量输出**：最终的 JSON 必须包含所有用例（包括无需修改的用例、修改后的用例、以及根据评审意见新增的用例）。

            # Output Format Example
            ```json
            {
            "test_cases": [
                {
                "case_title": "采购申请_提交校验_负数单价限制",
                "pre_conditions": "用户登录采购系统，进入新建采购申请页面。",
                "test_steps": "1. 选择任意物料；2. 在‘单价’输入框输入 -100；3. 输入合规的数量；4. 点击‘提交’。",
                "expected_results": "系统提示‘单价不能为负数’，且无法提交成功，后台数据库未生成新订单。",
                "test_data": {"item_id": "M001", "price": -100, "qty": 10},
                "priority": "高"
                },
                {
                "case_title": "采购申请_提交校验_零单价边界测试",
                "pre_conditions": "用户登录系统，进入新建采购申请页面。",
                "test_steps": "1. 选择任意物料；2. 单价输入 0；3. 输入合规的数量；4. 点击提交。",
                "expected_results": "系统拦截并提示‘采购单价必须大于0’，订单不生效。",
                "test_data": {"item_id": "M001", "price": 0, "qty": 10},
                "priority": "中"
                }
            ]
            }
            ```
            """
        )
        
        # 用例格式化 / 结构化输出智能体
        testcase_output_agent = AssistantAgent(
            name="testcase_output_agent",
            model_client=deepseek_model_case,
            model_client_stream=False,
            output_content_type=Testcaselist,
            system_message="""
                # Role
                你是一位资深的自动化测试专家，擅长将业务逻辑转换为标准、可执行的结构化测试用例。你的任务是将上游生成的测试点（Test Points）或需求分析转化为符合 Pydantic 模型定义的严格 JSON 数据。

                # Task
                你必须将输入内容转换为符合 `Testcaselist` 模型定义的结构化数据。每一条测试用例都必须具备严谨的逻辑性和独立执行的能力。

                # Mapping Rules (字段映射规则)
                - `id`: [用例编号]（自增整数，从 1 开始）。
                - `title`: [用例标题]（采用格式：[模块名] 验证某功能在某种操作下的结果）。
                - `case_code`: [用例编码]（格式：TC-PR-001）。
                - `category`: [用例分类]（如：功能测试、边界值、异常路径、UI测试等）。
                - `priority`: [优先级]（从 P0/P1/P2/P3 中选择，P0 为最高）。
                - `pre_conditions`: [前置条件]（描述执行该用例前系统必须满足的状态或数据准备）。
                - `test_steps`: [测试步骤]（清晰的步骤列表，使用 1. 2. 3. 序号标注，确保可操作性）。
                - `expected_results`: [预期结果]（描述每个关键步骤对应的系统反馈或数据库状态变更）。
                - `test_data`: [测试数据]（必须为 Dict 格式，例如 {"username": "admin", "amount": 100}，若无则为空字典 {}）。
                - `description`: [用例描述]（简述该用例的测试意图和覆盖的业务场景）。

                # Constraints
                - **纯净 JSON**：输出必须是一个标准的 JSON 对象，根节点为 `test_cases` 列表。
                - **数据严谨性**：`test_data` 字段必须是合法的 JSON 对象/字典，不能是字符串。
                - **原子化**：确保每个用例只测试一个核心逻辑点，避免单个用例过于冗长。
                - **逻辑自洽**：预期结果必须与测试步骤、测试数据一一对应。
                - **严禁废话**：仅输出符合 JSON 格式的代码块，不包含任何解释文字。

                # Output Format Example
                ```json
                {
                "test_cases": [
                    {
                    "id": 1,
                    "title": "[采购管理] 验证采购订单提交后状态流转",
                    "category": "功能测试",
                    "priority": "P0",
                    "pre_conditions": "用户已登录系统且具备采购员权限，存在一条处于'草稿'状态的采购订单。",
                    "test_steps": "1. 进入采购订单模块；2. 选择 ID 为 1001 的订单；3. 点击'提交审批'按钮。",
                    "expected_results": "订单状态由'草稿'变为'待审批'，系统弹出'提交成功'提示。",
                    "test_data": {"order_id": 1001, "action": "submit"},
                    "description": "验证采购订单提交功能的正向流程，确保状态机流转正确。"
                    }
                ]
                }
                ```
            """
        )

        # 结构化输出由 testcase_output_agent 首次发言后结束；并限制最大消息数防失控
        source_termination = SourceMatchTermination(sources=["testcase_output_agent"]) 
        
        team = RoundRobinGroupChat(
            [testcase_generate_agent, testcase_review_agent, testcase_final_agent, testcase_output_agent],
            termination_condition= source_termination,
            custom_message_types=[TestcaselistStructuredMessage],
        )
        return team
            
                
                        

if __name__ == "__main__":
    background = """
        MRP（Material Requirements Planning，物料需求计划）是现代制造业管理的核心逻辑。它不仅是一个软件功能，更是一套确保“在需要的时间、将需要的物料、按需要的数量”送达生产现场的精密算法。

        以下是关于 MRP 需求的详细技术描述。

        ---

        ## 1. MRP 核心逻辑概述

        MRP 的本质是根据**主生产计划 (MPS)**，利用**物料清单 (BOM)** 和**库存信息**，通过“剥洋葱”式的层层分解，计算出所有零部件、原材料的加工与采购指令。

        ### 1.1 基本计算公式
        MRP 的核心计算逻辑遵循以下等式：
        $$净需求 = 毛需求 + 安全库存 - (现有库存 + 预计入库)$$

        ---

        ## 2. 输入需求 (Inputs)

        MRP 系统的高效运行依赖于三大核心数据的准确性：

        | 数据项 | 描述 | 关键字段 |
        | :--- | :--- | :--- |
        | **主生产计划 (MPS)** | 确定最终产成品的生产数量和时间。 | 零件编号、需求日期、计划订单量 |
        | **物料清单 (BOM)** | 产品结构的层级化描述。 | 父项/子项关系、单位用量、损耗率 |
        | **库存状态 (Inventory)** | 实时掌握原材料和在制品的动态。 | 现存量、已分配量、在途订单、提前期 (Lead Time) |

        ---

        ## 3. 详细功能需求说明

        ### 3.1 需求展开与分解
        系统必须能够处理多层 BOM 结构。当顶层需求确定后，MRP 应自动向下穿透：
        * **低层码 (Low-Level Code) 处理：** 确保同一物料在不同层级出现时，只在最低层级进行一次合并计算，避免重复。
        * **时间偏移：** 根据物料的**提前期 (Lead Time)**，将需求时间从“完工日期”倒推至“开工/采购日期”。

        ### 3.2 净需求计算逻辑
        系统需执行以下步骤：
        1.  **毛需求 (Gross Requirements)：** 来源于上层订单或预测。
        2.  **预计入库 (Scheduled Receipts)：** 尚未交付但已发出的采购订单或生产订单。
        3.  **现有库存 (On Hand)：** 仓库中可用的物理库存。
        4.  **净需求 (Net Requirements)：** 扣除库存与预计入库后的真实缺口。

        ### 3.3 批量规则 (Lot Sizing)
        系统应支持多种批量订货策略，以平衡库存持有成本与订货成本：
        * **按需订货 (LFL, Lot-for-Lot)：** 缺多少订多少，库存持有成本最低。
        * **固定周期 (Fixed Period Requirement)：** 合并未来 $N$ 天的需求。
        * **经济订货批量 (EOQ)：** 使用公式计算最优性价比数量：
            $$EOQ = \\sqrt{{\\frac{{2DS}}{{H}}}}$$
            其中 $D$ 为年需求量，$S$ 为单次订货成本，$H$ 为单位储存成本。

        ---

        ## 4. 输出需求 (Outputs)

        MRP 运算后应自动生成以下建议文档：

        * **计划订单发布 (Planned Order Releases)：** 建议采购员下达采购单或计划员下达生产任务。
        * **重排计划通知 (Exception Reports)：**
            * **提前 (Expedite)：** 现有物料到货太晚，无法满足生产。
            * **推迟 (Delay)：** 生产计划变更，现有物料到货太早。
            * **取消 (Cancel)：** 需求已消失，建议取消订单。

        ---

        ## 5. 约束与非功能性需求

        * **运算频率：** 支持“全重调度 (Regenerative MRP)”（通常每周/每日一次）和“净改变 (Net Change MRP)”（实时或准实时更新）。
        * **数据准确度：** 要求库存准确率需达到 **98%** 以上，BOM 准确率需达到 **99%** 以上，否则 MRP 结果将失去参考价值。
        * **可视化监控：** 提供“物料可用性检查”看板，红色预警缺料风险。

        > **专家提示：** MRP 虽然强大，但它是基于“无限产能”假设的。在实际应用中，必须配合 **CRP (能力需求计划)** 进行闭环验证，确保生产指令在人力和机器设备上是可行的。
    """
    agent = TestCaseGenerateAgent(background)
    team = asyncio.run(agent.create_team())
    asyncio.run(Console(team.run_stream(task = "我希望针对 ERP 中的 MRP 需求，编写用例，用例完成后总结一下")))
