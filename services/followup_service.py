from datetime import date

from database.db import SessionLocal
from database.models import FollowUp, Invoice


def create_followup(
    invoice_id,
    contact_type="EMAIL",
    response_status="PENDING",
    subject="Payment Reminder",
    notes="Payment reminder sent."
):
    db = SessionLocal()

    try:
        invoice = db.query(Invoice).filter(
            Invoice.id == invoice_id
        ).first()

        if not invoice:
            raise ValueError(
                f"Invoice {invoice_id} not found."
            )

        followup = FollowUp(
            customer_id=invoice.customer_id,
            invoice_id=invoice.id,
            followup_date=date.today(),
            contact_type=contact_type,
            response_status=response_status,
            subject=subject,
            notes=notes
        )

        db.add(followup)
        db.commit()

        return followup

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()