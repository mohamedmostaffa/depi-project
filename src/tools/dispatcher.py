"""
BrandMind — Tool Dispatcher
Provides unified execution, logging, and error handling for all agent tools.
"""

from typing import Any, Dict, Optional
from datetime import date

from src.schemas import ToolExecutionResult
from src.tools.catalog_tool import CatalogTool
from src.tools.order_tool import OrderTool
from src.tools.return_tool import ReturnTool
from src.tools.escalation_tool import EscalationTool


class ToolDispatcher:
    def __init__(
        self,
        catalog_tool: Optional[CatalogTool] = None,
        order_tool: Optional[OrderTool] = None,
        return_tool: Optional[ReturnTool] = None,
        escalation_tool: Optional[EscalationTool] = None,
    ):
        self.catalog = catalog_tool or CatalogTool()
        self.orders = order_tool or OrderTool()
        self.returns = return_tool or ReturnTool()
        self.escalations = escalation_tool or EscalationTool()

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """Executes a named tool and returns a typed ToolExecutionResult."""
        try:
            if tool_name == "search_products":
                items = self.catalog.search_products(
                    query=arguments.get("query"),
                    category=arguments.get("category"),
                    size=arguments.get("size"),
                    color=arguments.get("color"),
                    max_price=arguments.get("max_price"),
                    brand_id=arguments.get("brand_id", "rlvnt"),
                )
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    data=[item.model_dump() for item in items],
                )

            elif tool_name == "get_order_status":
                order_id = arguments.get("order_id", "")
                brand_id = arguments.get("brand_id", "rlvnt")
                order = self.orders.get_order_status(order_id=order_id, brand_id=brand_id)
                if order:
                    return ToolExecutionResult(
                        tool_name=tool_name,
                        success=True,
                        data=order.model_dump(),
                    )
                else:
                    return ToolExecutionResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"Order '{order_id}' not found for brand '{brand_id}'.",
                    )

            elif tool_name == "check_return_eligibility":
                facts = arguments.get("facts", {})
                brand_id = arguments.get("brand_id", "rlvnt")
                today = arguments.get("today")
                if isinstance(today, str):
                    today = date.fromisoformat(today)

                res = self.returns.check_eligibility(facts=facts, brand_id=brand_id, today=today)
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    data=res.model_dump(),
                )

            elif tool_name == "escalate_to_human":
                session_id = arguments.get("session_id", "unknown")
                brand_id = arguments.get("brand_id", "rlvnt")
                reason = arguments.get("reason", "Customer requested human support")
                msg = arguments.get("customer_message", "")
                summary = arguments.get("summary")

                record = self.escalations.escalate(
                    session_id=session_id,
                    brand_id=brand_id,
                    reason=reason,
                    customer_message=msg,
                    conversation_summary=summary,
                )
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    data=record.model_dump(),
                )

            else:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Unknown tool name: '{tool_name}'",
                )

        except Exception as e:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool execution failed with exception: {str(e)}",
            )
