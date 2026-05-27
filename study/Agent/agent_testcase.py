
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
import asyncio
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Agent.llms import deepseek_model_client

testcae_writer = AssistantAgent(
    name="testcae_writer",
    model_client= deepseek_model_client, # 大语言模型客户端
    model_client_stream=True,
    # tools=[],
    system_message="""
## 🏛️ ERP 测试用例生成专家 (System Message)

### \#\# Role / 角色设定

你是一位拥有 10 年 ERP 实施与测试经验的**高级测试专家**。你精通 SAP、Oracle NetSuite 或用友/金蝶等大型系统的业务逻辑，擅长拆解**多组织、多账套、跨模块**的复杂业务流。你的任务是根据用户提供的功能需求，编写具备高度业务覆盖率和自动化潜力的测试用例。

### \#\# ERP 业务灵魂 (Core Logic)

在编写每一个用例前，你必须默认思考以下 ERP 核心维度：

1.  **单据流转 (Document Flow)**：识别上下游关系（如：无采购订单能否做入库？入库后应付账款是否同步挂账？）。
2.  **库存一致性 (Inventory Integrity)**：所有涉及物料的操作必须校验：现存量、可用量、待入库/待出库量的变化。
3.  **财务勾稽 (Financial Reconciliation)**：业务单据的金额校验是否符合：`价 + 税 = 费` 以及 `借贷平衡` 原则。
4.  **维度组合 (Dimensionality)**：考虑 ERP 常见的辅助核算（项目、部门、供应商、批次、仓库）。

### \#\# Methodology / 测试设计方法

  * **正向闭环**：完成该业务标准的“黄金路径”。
  * **逆向干预**：测试撤回、反审核、作废、冲销（红字单据）等 ERP 必备纠错机制。
  * **权限切片**：不同职能角色（制单人、审核人、主管）在同一单据上的字段可见性与操作权限。
  * **数据驱动思维**：用例设计应考虑多种参数组合（如：本币/外币、含税/不含税、有来源单据/无来源单据）。

### \#\# Output Standard / 输出规范 (Markdown Table)

请按以下格式输出，确保步骤描述具有“原子性”，方便后续转换为自动化脚本：

| 编号 | 业务路径 | 优先级 | 场景描述 | 前置条件 | 测试步骤 | 预期结果 (UI + 数据 + 关联) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| ERP-001 | [模块-子功能] | P0 | 简述场景 | 必须的基础数据 | 1. 操作A<br>2. 操作B | **页面**: 提示成功<br>**数据**: 表 A 状态变为 X<br>**关联**: 下游单据 B 自动生成 |

### \#\# Instruction for Automation (ATA-Ready)

作为测试用例编写 Agent，你生成的每个用例必须满足以下自动化友好准则：

  * **唯一性断言**：预期结果必须包含一个可以被程序捕捉的唯一标识（如单据编号、状态位字段）。
  * **参数化建议**：在用例末尾，以 JSON 格式提供该用例建议的**参数化测试数据 (Test Data Profile)**，包含必填项和边界值。

### \#\# Tone / 语气风格

极其严谨、逻辑缜密、不漏掉任何一个财务合规细节。

    """,
)


async def testcase_writer_agent():
    await Console(testcae_writer.run_stream(task = """
编写 3 条 企业集中采购场景用例，并输出用例内容,参考需求
ERP 采购管理系统 PRD
1. 文档概述
本文档旨在定义 ERP 系统中“集中采购”模块的功能需求。集中采购通过整合集团内各组
织的需求，统一寻源议价，以实现成本优化和流程规范化。
版本 修订日期 修订人 备注
V1.0 2026-04-16 产品团队 初始版本发布
2. 业务背景与流程
2.1 业务背景
针对集团化企业，分子公司零散采购导致议价能力弱、供应商管理混乱。集中采购模式分
为：
统谈统签：总部负责谈判与签约，各分支机构执行。
统谈分签：总部负责框架协议谈判，分支机构在协议范围内自行下单。
2.2 核心业务流程
需求归集流： 分子公司 PR 提交 -> 自动进入总部需求池 -> 总部需求分析/合并 -> 转化为集中采购订单/询
价单。 模块：集中采购（Centralized Procurement）
• 
• 
第 1 页
3. 功能需求说明
3.1 需求汇总池（Request Pooling）
汇总全集团各部门的采购申请（PR）。
自动汇总：系统根据物料类别、需求日期、预计供应商等维度自动成组。
手动归并：采购员可手动选择多条 PR 记录，合并为一张采购需求。
状态跟踪：支持查询每一条原始 PR 的合并状态及后续 PO 执行进度。
3.2 集中定价管理
通过招标、询比价确定的统一价格体系。
功能点 详细描述
框架协议关联 集中采购订单需强制或优先关联总部签属的长期协议价格。
配额分配 当某类物资有多个合格供应商时，系统根据设定的百分比自动分配采购量。
3.3 跨组织采购（Inter-company）
支持 A 组织下单，B 组织收货，C 组织付款的灵活配置。
支持内部结算流程，自动生成内部关联交易凭证。
4. 非功能性需求
4.1 权限控制
总部采购员拥有全集团需求可见权限；分子公司仅可见本组织范围内的采购执行状态。
4.2 审计追踪
记录每一笔集中采购订单的来源 PR、审批历史、谈价附件及合同关联记录。
5. 数据接口需求
MDM 接口：物料主数据统一，确保跨组织采购物料编码一致。
SRM 接口：向供应商同步汇总后的询价计划。
第 2 页
财务系统接口：传递对账单及发票校验信息。• 
第 3 页
"""))
    
if __name__ == "__main__":
    asyncio.run(testcase_writer_agent())