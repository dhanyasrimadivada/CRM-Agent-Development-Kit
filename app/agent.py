"""Google ADK agent for CRM_ADK.

This replaces the old LangGraph/Groq/MCP agent layer.
The agent talks directly to the existing CRM tools and SQLite database.
"""

from google.adk.agents import Agent

from tools import (
    get_dashboard,
    get_customers,
    get_customer,
    get_quotations,
    get_pending_quotations,
    get_purchase_orders,
    get_deliveries,
    get_invoices,
    get_overdue_invoices,
    get_pending_payments,
    get_followups,
    get_payment_status,
    get_quotations_awaiting_po,
    create_new_quotation,
    change_quotation_status,
    create_delivery,
    change_delivery_status,
    save_purchase_order_data,
    save_invoice_data,
    make_payment,
    send_reminder,
    add_followup,
)


root_agent = Agent(
    name="crm_agent",
    model="groq/qwen/qwen3.8-27b",
    description="A CRM assistant for customers, quotations, purchase orders, deliveries, invoices, payments and follow-ups.",
    instruction="""
You are a helpful CRM assistant for DS TECH.

For greetings and normal conversation, respond naturally.
For general knowledge questions, answer normally.

For CRM questions, use the appropriate CRM tool and always use real database data.
Never invent CRM records.

Use read tools for information requests and write tools only when the user clearly asks
for the action to be performed.

Important rules:
- Overdue invoice questions -> get_overdue_invoices.
- Dashboard/KPI questions -> get_dashboard.
- Customer questions -> get_customers or get_customer.
- Invoice questions -> get_invoices, get_overdue_invoices, get_pending_payments,
  or get_payment_status.
- Quotation questions -> get_quotations or get_pending_quotations.
- Purchase order questions -> get_purchase_orders or get_quotations_awaiting_po.
- Delivery questions -> get_deliveries.
- Follow-up history -> get_followups.
- Never send a payment reminder unless explicitly requested.
- Never record a payment unless explicitly requested.
- Never claim a write operation succeeded unless the tool reports success.
- If a tool fails, explain the error.
- Use ₹ for monetary amounts when appropriate.
""",
    tools=[
        get_dashboard,
        get_customers,
        get_customer,
        get_quotations,
        get_pending_quotations,
        get_purchase_orders,
        get_deliveries,
        get_invoices,
        get_overdue_invoices,
        get_pending_payments,
        get_followups,
        get_payment_status,
        get_quotations_awaiting_po,
        create_new_quotation,
        change_quotation_status,
        create_delivery,
        change_delivery_status,
        save_purchase_order_data,
        save_invoice_data,
        make_payment,
        send_reminder,
        add_followup,
    ],
)
