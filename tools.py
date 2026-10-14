"""CRM tools exposed directly to Google ADK.

These are ordinary Python functions. No MCP server/client is used.
They reuse the existing CRM SQLite database and service layer.
"""

from database.db import SessionLocal
from database.models import (
    Customer,
    Quotation,
    PurchaseOrder,
    Delivery,
    Invoice,
    FollowUp,
)
from database.po_service import save_purchase_order
from services.delivery_service import (
    create_delivery_for_po,
    update_delivery_status,
)
from services.followup_service import create_followup
from services.invoice_service import save_invoice_for_po
from services.payment_service import (
    get_payment_for_invoice,
    record_payment,
    refresh_overdue_invoices,
)
from services.quotation_service import (
    create_quotation,
    update_quotation_status,
)
from services.reminder_service import send_payment_reminder
from services.po_workflow_service import get_quotations_awaiting_po as _get_quotations_awaiting_po


def get_dashboard():
    """Get CRM KPI summary and business analysis."""
    refresh_overdue_invoices()
    db = SessionLocal()
    try:
        quotations = db.query(Quotation).all()
        invoices = db.query(Invoice).all()
        deliveries = db.query(Delivery).all()
        won = [q for q in quotations if q.status == "WON"]
        declined = [q for q in quotations if q.status == "DECLINED"]
        overdue = [i for i in invoices if i.status == "OVERDUE"]
        pending = [i for i in invoices if i.status in {"PENDING", "PARTIAL"}]
        paid = [i for i in invoices if i.status == "PAID"]
        return {
            "quotation_count": len(quotations),
            "won_quotations": len(won),
            "declined_quotations": len(declined),
            "conversion_percent": round(len(won) / len(quotations) * 100, 2) if quotations else 0,
            "quotation_value": sum(q.total_amount or 0 for q in quotations),
            "outstanding_amount": sum(i.total_amount or 0 for i in pending + overdue),
            "overdue_amount": sum(i.total_amount or 0 for i in overdue),
            "paid_amount": sum(i.total_amount or 0 for i in paid),
            "pending_invoices": len(pending),
            "overdue_invoices": len(overdue),
            "paid_invoices": len(paid),
            "deliveries_in_process": sum(d.delivery_status == "IN_PROCESS" for d in deliveries),
            "deliveries_completed": sum(d.delivery_status == "COMPLETED" for d in deliveries),
        }
    finally:
        db.close()


def get_customers():
    """Get all CRM customers."""
    db = SessionLocal()
    try:
        return [
            {
                "id": c.id,
                "company_name": c.company_name,
                "contact_person": c.contact_person,
                "email": c.email,
                "phone": c.phone,
                "gstin": c.gstin,
            }
            for c in db.query(Customer).order_by(Customer.id.asc()).all()
        ]
    finally:
        db.close()


def get_customer(customer_id: int):
    """Get one CRM customer by ID."""
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            return {"success": False, "message": "Customer not found."}
        return {
            "success": True,
            "id": c.id,
            "company_name": c.company_name,
            "contact_person": c.contact_person,
            "email": c.email,
            "phone": c.phone,
            "gstin": c.gstin,
            "address": c.address,
        }
    finally:
        db.close()


def get_quotations():
    """Get all quotations."""
    db = SessionLocal()
    try:
        return [
            {
                "id": q.id,
                "quotation_number": q.quotation_number,
                "customer": q.customer.company_name if q.customer else None,
                "amount": q.total_amount,
                "status": q.status,
                "date": str(q.quotation_date) if q.quotation_date else None,
            }
            for q in db.query(Quotation).order_by(Quotation.id.desc()).all()
        ]
    finally:
        db.close()


def get_pending_quotations():
    """Get quotations that still require action."""
    db = SessionLocal()
    try:
        rows = db.query(Quotation).filter(
            Quotation.status.in_(["DRAFT", "SENT", "AWAITING_PO"])
        ).order_by(Quotation.id.desc()).all()
        return [
            {
                "id": q.id,
                "quotation_number": q.quotation_number,
                "customer": q.customer.company_name if q.customer else None,
                "amount": q.total_amount,
                "status": q.status,
            }
            for q in rows
        ]
    finally:
        db.close()


def get_purchase_orders():
    """Get all purchase orders."""
    db = SessionLocal()
    try:
        return [
            {
                "id": po.id,
                "po_number": po.po_number,
                "quotation_id": po.quotation_id,
                "customer": po.customer.company_name if po.customer else None,
                "amount": po.total_amount,
                "payment_terms": po.payment_terms,
                "payment_days": po.payment_days,
                "status": po.status,
            }
            for po in db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).all()
        ]
    finally:
        db.close()


def get_deliveries():
    """Get all deliveries and their current status."""
    db = SessionLocal()
    try:
        return [
            {
                "id": d.id,
                "purchase_order_id": d.purchase_order_id,
                "status": d.delivery_status,
                "expected_date": str(d.expected_date) if d.expected_date else None,
                "actual_date": str(d.actual_date) if d.actual_date else None,
                "remarks": d.remarks,
            }
            for d in db.query(Delivery).order_by(Delivery.id.desc()).all()
        ]
    finally:
        db.close()


def get_invoices():
    """Get all invoices."""
    db = SessionLocal()
    try:
        return [
            {
                "id": i.id,
                "invoice_number": i.invoice_number,
                "customer": i.customer.company_name if i.customer else None,
                "purchase_order_id": i.purchase_order_id,
                "amount": i.total_amount,
                "invoice_date": str(i.invoice_date) if i.invoice_date else None,
                "due_date": str(i.due_date) if i.due_date else None,
                "status": i.status,
            }
            for i in db.query(Invoice).order_by(Invoice.id.desc()).all()
        ]
    finally:
        db.close()


def get_overdue_invoices():
    """Get all invoices whose payment is currently overdue."""
    refresh_overdue_invoices()
    db = SessionLocal()
    try:
        rows = db.query(Invoice).filter(Invoice.status == "OVERDUE").order_by(Invoice.due_date.asc(), Invoice.id.asc()).all()
        return [
            {
                "id": i.id,
                "invoice_number": i.invoice_number,
                "customer": i.customer.company_name if i.customer else None,
                "email": i.customer.email if i.customer else None,
                "amount": i.total_amount,
                "due_date": str(i.due_date) if i.due_date else None,
                "status": i.status,
            }
            for i in rows
        ]
    finally:
        db.close()


def get_pending_payments():
    """Get invoices with PENDING, PARTIAL, or OVERDUE payment status."""
    refresh_overdue_invoices()
    db = SessionLocal()
    try:
        rows = db.query(Invoice).filter(
            Invoice.status.in_(["PENDING", "PARTIAL", "OVERDUE"])
        ).order_by(Invoice.due_date.asc(), Invoice.id.asc()).all()
        return [
            {
                "id": i.id,
                "invoice_number": i.invoice_number,
                "customer": i.customer.company_name if i.customer else None,
                "amount": i.total_amount,
                "due_date": str(i.due_date) if i.due_date else None,
                "status": i.status,
            }
            for i in rows
        ]
    finally:
        db.close()


def get_followups():
    """Get CRM follow-up history."""
    db = SessionLocal()
    try:
        rows = db.query(FollowUp).order_by(FollowUp.id.desc()).all()
        return [
            {
                "id": f.id,
                "customer_id": f.customer_id,
                "invoice_id": f.invoice_id,
                "date": str(f.followup_date) if f.followup_date else None,
                "contact_type": f.contact_type,
                "response_status": f.response_status,
                "subject": f.subject,
                "notes": f.notes,
            }
            for f in rows
        ]
    finally:
        db.close()


def get_payment_status(invoice_id: int):
    """Get payment status, total paid, and remaining amount for an invoice."""
    return get_payment_for_invoice(invoice_id)


def get_quotations_awaiting_po():
    """Get quotations that are waiting for a purchase order."""
    return _get_quotations_awaiting_po()


def create_new_quotation(customer_id: int, quotation_number: str, quotation_date: str, valid_until: str | None, items: list):
    """Create a quotation using the existing CRM quotation service."""
    from datetime import date
    q_date = date.fromisoformat(quotation_date)
    v_date = date.fromisoformat(valid_until) if valid_until else None
    return create_quotation(customer_id, quotation_number, q_date, v_date, items)


def change_quotation_status(quotation_id: int, status: str):
    """Update a quotation status using the existing CRM workflow."""
    return update_quotation_status(quotation_id, status)


def create_delivery(purchase_order_id: int, expected_date: str, remarks: str = ""):
    """Create a delivery record for a purchase order."""
    from datetime import date
    return create_delivery_for_po(purchase_order_id, date.fromisoformat(expected_date), remarks)


def change_delivery_status(delivery_id: int, status: str, actual_date: str | None = None, remarks: str = ""):
    """Update a delivery status using the existing CRM workflow."""
    from datetime import date
    actual = date.fromisoformat(actual_date) if actual_date else None
    return update_delivery_status(delivery_id, status, actual, remarks)


def save_purchase_order_data(purchase_order_data: dict, quotation_id: int | None = None):
    """Save a purchase order dictionary using the existing CRM PO service."""
    return save_purchase_order(purchase_order_data, quotation_id=quotation_id)


def save_invoice_data(purchase_order_id: int, invoice_data: dict):
    """Save an invoice dictionary for a purchase order using the existing CRM service."""
    return save_invoice_for_po(purchase_order_id, invoice_data)


def make_payment(invoice_id: int, amount: float | None = None, payment_method: str = "BANK_TRANSFER", reference_number: str = ""):
    """Record a payment when the user explicitly asks to do so."""
    result = record_payment(
        invoice_id=invoice_id,
        status="PAID",
        amount=amount,
        payment_method=payment_method,
        reference_number=reference_number,
    )
    return result if isinstance(result, dict) else {"success": True, "result": str(result)}


def send_reminder(invoice_id: int):
    """Send a payment reminder only when the user explicitly requests it."""
    send_payment_reminder(invoice_id)
    return {"success": True, "invoice_id": invoice_id, "message": "Payment reminder sent successfully."}


def add_followup(invoice_id: int, contact_type: str = "EMAIL", response_status: str = "PENDING", subject: str = "Follow-up", notes: str = ""):
    """Add a follow-up record for an invoice."""
    followup = create_followup(invoice_id, contact_type, response_status, subject, notes)
    return {"success": True, "followup_id": followup.id}
