from datetime import date, datetime

from database.db import SessionLocal
from database.models import Invoice, Payment


PAID_STATUSES = {"PAID", "PARTIAL"}


def _payment_totals(db, invoice_id: int):
    payments = (
        db.query(Payment)
        .filter(
            Payment.invoice_id == invoice_id,
            Payment.status.in_(PAID_STATUSES),
        )
        .all()
    )

    paid = sum(float(p.amount or 0) for p in payments)
    return paid, payments


def get_invoice_paid_amount(invoice_id: int):
    db = SessionLocal()
    try:
        paid, _ = _payment_totals(db, invoice_id)
        return paid
    finally:
        db.close()


def refresh_overdue_invoices():
    """
    Keep invoice status synchronized with the due date.

    Rules:
    - PAID invoices never become overdue.
    - PENDING/PARTIAL invoices become OVERDUE once due_date has passed.
    - PARTIAL invoices are still eligible for overdue status.
    - A partial payment is never converted back to an unpaid state.
    """
    db = SessionLocal()
    changed = 0
    try:
        today = date.today()
        invoices = (
            db.query(Invoice)
            .filter(Invoice.status != "PAID")
            .all()
        )

        for invoice in invoices:
            paid, _ = _payment_totals(db, invoice.id)
            total = float(invoice.total_amount or 0)

            # A fully paid invoice is always completed.
            if total > 0 and paid >= total:
                if invoice.status != "PAID":
                    invoice.status = "PAID"
                    changed += 1
                continue

            if invoice.due_date and invoice.due_date < today:
                if invoice.status != "OVERDUE":
                    invoice.status = "OVERDUE"
                    changed += 1
            else:
                # Do not downgrade an invoice that has recorded partial payment.
                if paid > 0 and invoice.status not in {"PARTIAL", "OVERDUE"}:
                    invoice.status = "PARTIAL"
                    changed += 1
                elif paid <= 0 and invoice.status == "PARTIAL":
                    invoice.status = "PENDING"
                    changed += 1

        if changed:
            db.commit()

        return changed
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_payment_for_invoice(invoice_id: int):
    db = SessionLocal()
    try:
        payment = (
            db.query(Payment)
            .filter(Payment.invoice_id == invoice_id)
            .order_by(Payment.id.desc())
            .first()
        )

        paid_amount, _ = _payment_totals(db, invoice_id)

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        total_amount = float(invoice.total_amount or 0) if invoice else 0.0

        return {
            "success": True,
            "invoice_id": invoice_id,
            "status": payment.status if payment else "PENDING",
            "payment": {
                "id": payment.id,
                "amount": payment.amount,
                "payment_date": str(payment.payment_date) if payment and payment.payment_date else None,
                "payment_method": payment.payment_method if payment else None,
                "reference_number": payment.reference_number if payment else None,
                "status": payment.status if payment else "PENDING",
                "notes": payment.notes if payment else None,
            } if payment else None,
            "total_paid": paid_amount,
            "remaining_amount": max(total_amount - paid_amount, 0.0),
        }
    finally:
        db.close()


def get_overdue_invoices():
    refresh_overdue_invoices()

    db = SessionLocal()
    try:
        return (
            db.query(Invoice)
            .filter(Invoice.status == "OVERDUE")
            .order_by(Invoice.due_date.asc(), Invoice.id.asc())
            .all()
        )
    finally:
        db.close()


def record_payment(
    invoice_id: int,
    status: str = "PAID",
    amount=None,
    payment_date=None,
    payment_method=None,
    reference_number=None,
    notes=None,
):
    """
    Record a payment.

    PAID:
        Marks the invoice fully paid.

    PARTIAL:
        Records a partial payment and locks the workflow out of
        NOT_PAID/unpaid again. The invoice can later be marked PAID.

    NOT_PAID:
        Does not create a payment record. It is only allowed when
        no payment has previously been recorded.
    """
    db = SessionLocal()

    try:
        invoice = (
            db.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .first()
        )

        if invoice is None:
            return {"success": False, "error": "Invoice not found."}

        status = str(status or "").strip().upper().replace("-", "_")

        if status in {"NOT PAID", "NOT_PAID", "UNPAID"}:
            status = "NOT_PAID"
        elif status in {"PARTIAL", "PARTIALLY_PAID", "PARTIALLY PAID"}:
            status = "PARTIAL"
        elif status == "PAID":
            status = "PAID"
        else:
            return {
                "success": False,
                "error": "Payment status must be PAID, PARTIAL or NOT PAID.",
            }

        already_paid, existing_payments = _payment_totals(db, invoice.id)
        total_amount = float(invoice.total_amount or 0)
        remaining = max(total_amount - already_paid, 0.0)
        has_recorded_payment = already_paid > 0 or bool(existing_payments)

        # Once a payment has been recorded, NOT_PAID is not allowed.
        if status == "NOT_PAID" and has_recorded_payment:
            return {
                "success": False,
                "error": (
                    "This invoice already has a recorded payment. "
                    "It cannot be changed back to NOT PAID."
                ),
            }

        if status == "NOT_PAID":
            # Recalculate overdue state immediately.
            today = date.today()
            invoice.status = (
                "OVERDUE"
                if invoice.due_date and invoice.due_date < today
                else "PENDING"
            )
            db.commit()

            return {
                "success": True,
                "invoice_id": invoice.id,
                "status": "NOT_PAID",
                "invoice_status": invoice.status,
                "due_date": str(invoice.due_date) if invoice.due_date else None,
            }

        if payment_date is None:
            payment_date = date.today()
        elif isinstance(payment_date, str):
            parsed = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    parsed = datetime.strptime(payment_date, fmt).date()
                    break
                except ValueError:
                    continue
            if parsed is None:
                return {"success": False, "error": "Invalid payment date."}
            payment_date = parsed

        if amount is None or str(amount).strip() == "":
            payment_amount = remaining if remaining > 0 else total_amount
        else:
            try:
                payment_amount = float(amount)
            except (TypeError, ValueError):
                return {"success": False, "error": "Payment amount must be a valid number."}

        if payment_amount <= 0:
            return {"success": False, "error": "Payment amount must be greater than 0."}

        if total_amount > 0 and payment_amount > remaining + 0.01:
            return {
                "success": False,
                "error": (
                    f"Payment amount ₹{payment_amount:,.2f} exceeds the "
                    f"remaining balance of ₹{remaining:,.2f}."
                ),
            }

        # If the entered amount settles the remaining balance, treat it as PAID.
        if total_amount > 0 and payment_amount >= remaining - 0.01:
            status = "PAID"

        payment = Payment(
            invoice_id=invoice.id,
            amount=payment_amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            status=status,
            notes=notes,
        )
        db.add(payment)

        new_paid = already_paid + payment_amount

        if status == "PAID" or (total_amount > 0 and new_paid >= total_amount - 0.01):
            invoice.status = "PAID"
            status = "PAID"
        else:
            # Keep PARTIAL until the due date; after the due date it becomes OVERDUE.
            invoice.status = (
                "OVERDUE"
                if invoice.due_date and invoice.due_date < date.today()
                else "PARTIAL"
            )

        db.commit()
        db.refresh(payment)

        return {
            "success": True,
            "invoice_id": invoice.id,
            "payment_id": payment.id,
            "status": status,
            "invoice_status": invoice.status,
            "amount": payment.amount,
            "total_paid": new_paid,
            "remaining_amount": max(total_amount - new_paid, 0.0),
            "payment_date": str(payment.payment_date) if payment.payment_date else None,
        }

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
