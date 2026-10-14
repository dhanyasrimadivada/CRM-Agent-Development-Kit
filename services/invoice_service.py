from datetime import datetime, timedelta
import re

from database.db import SessionLocal
from database.models import (
    PurchaseOrder,
    Delivery,
    Invoice,
)


def save_invoice_for_po(
    purchase_order_id: int,
    invoice_data: dict,
    source_document_id=None,
):
    """
    Save an extracted invoice for a Purchase Order.

    Invoice is allowed only when delivery is COMPLETED.
    """

    db = SessionLocal()

    try:

        # ==================================================
        # FIND PO
        # ==================================================

        purchase_order = (
            db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.id == purchase_order_id
            )
            .first()
        )

        if purchase_order is None:
            return {
                "success": False,
                "error": "Purchase Order not found."
            }

        # ==================================================
        # DELIVERY GATE
        # ==================================================

        delivery = (
            db.query(Delivery)
            .filter(
                Delivery.purchase_order_id
                == purchase_order_id
            )
            .first()
        )

        if delivery is None:
            return {
                "success": False,
                "error": (
                    "Invoice cannot be uploaded because "
                    "no delivery record exists."
                )
            }

        if delivery.delivery_status != "COMPLETED":
            return {
                "success": False,
                "error": (
                    "Invoice cannot be uploaded until "
                    "delivery is COMPLETED."
                ),
                "delivery_status": (
                    delivery.delivery_status
                ),
            }

        # ==================================================
        # EXTRACT DATA
        # ==================================================

        invoice_number = str(
            invoice_data.get("invoice_number", "")
        ).strip()

        invoice_date = invoice_data.get(
            "invoice_date"
        )

        amounts = (
            invoice_data.get("amounts")
            if isinstance(invoice_data.get("amounts"), dict)
            else {}
        )

        payment_info = (
            invoice_data.get("payment")
            or invoice_data.get("payment_terms")
            or {}
        )

        # ==================================================
        # VALIDATE INVOICE NUMBER
        # ==================================================

        if not invoice_number:
            return {
                "success": False,
                "error": "Invoice number is missing."
            }

        # ==================================================
        # CHECK DUPLICATE
        # ==================================================

        existing_invoice = (
            db.query(Invoice)
            .filter(
                Invoice.invoice_number
                == invoice_number
            )
            .first()
        )

        if existing_invoice:

            return {
                "success": False,
                "error": (
                    f"Invoice {invoice_number} "
                    f"already exists."
                )
            }

        # ==================================================
        # PARSE INVOICE DATE
        # ==================================================

        parsed_invoice_date = None

        if invoice_date:

            if hasattr(invoice_date, "year"):

                parsed_invoice_date = invoice_date

            else:

                date_string = str(
                    invoice_date
                ).strip()

                for fmt in (
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%d-%m-%Y",
                    "%d-%b-%y",
                    "%d-%B-%Y",
                ):

                    try:

                        parsed_invoice_date = (
                            datetime.strptime(
                                date_string,
                                fmt
                            ).date()
                        )

                        break

                    except ValueError:
                        continue

        # ==================================================
        # AMOUNTS
        # ==================================================

        subtotal = float(
            amounts.get("subtotal") or invoice_data.get("subtotal") or 0
        )

        tax_amount = float(
            amounts.get("tax_amount") or invoice_data.get("tax_amount") or 0
        )

        total_amount = float(
            amounts.get("total_amount") or invoice_data.get("total_amount") or 0
        )

        # ==================================================
        # PAYMENT TERMS / DUE DATE
        # ==================================================

        def parse_days(value):
            if value is None:
                return None
            try:
                number = int(value)
                return number if number > 0 else None
            except (TypeError, ValueError):
                pass

            match = re.search(r"\b(\d{1,3})\s*(?:day|days|d)\b", str(value), re.I)
            if match:
                number = int(match.group(1))
                return number if number > 0 else None
            return None

        if isinstance(payment_info, str):
            payment_description = payment_info.strip()
            payment_days = parse_days(payment_info)
            extracted_due_date = invoice_data.get("due_date")
        else:
            payment_days = parse_days(payment_info.get("payment_days"))
            payment_description = str(
                payment_info.get("payment_terms")
                or payment_info.get("description")
                or payment_info.get("terms")
                or ""
            ).strip()
            if payment_days is None:
                payment_days = parse_days(payment_description)

            extracted_due_date = (
                payment_info.get("due_date")
                or invoice_data.get("due_date")
            )

        # If the invoice does not specify terms, use the PO terms.
        if payment_days is None:
            payment_days = parse_days(purchase_order.payment_days)

        if not payment_description and purchase_order.payment_terms:
            payment_description = str(purchase_order.payment_terms).strip()

        # Business rule: if neither the invoice nor the PO contains
        # payment terms/days, default the invoice due date to 10 days
        # after the invoice date.
        if payment_days is None:
            payment_days = 10
            if not payment_description:
                payment_description = "Default payment term: 10 days"

        # ==================================================
        # DUE DATE
        # ==================================================

        due_date = None

        if extracted_due_date:
            if hasattr(extracted_due_date, "year"):
                due_date = extracted_due_date
            else:
                date_string = str(extracted_due_date).strip()
                for fmt in (
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%d-%m-%Y",
                    "%d-%b-%y",
                    "%d-%B-%Y",
                ):
                    try:
                        due_date = datetime.strptime(date_string, fmt).date()
                        break
                    except ValueError:
                        continue

        if due_date is None:
            base_date = parsed_invoice_date or datetime.now().date()
            due_date = base_date + timedelta(days=payment_days)

        # ==================================================
        # CREATE INVOICE
        # ==================================================

        invoice = Invoice(
            purchase_order_id=purchase_order.id,
            customer_id=purchase_order.customer_id,

            invoice_number=invoice_number,

            invoice_date=parsed_invoice_date,

            subtotal=subtotal,

            tax_amount=tax_amount,

            total_amount=total_amount,

            payment_terms=(
                payment_description
                or None
            ),

            payment_days=payment_days,

            due_date=due_date,

            status="PENDING",

            source_document_id=(
                source_document_id
            ),
        )

        db.add(invoice)

        db.commit()
        db.refresh(invoice)

        print()
        print("=" * 60)
        print("INVOICE SAVED")
        print("=" * 60)
        print(
            f"Invoice Number: "
            f"{invoice.invoice_number}"
        )
        print(
            f"Invoice ID: {invoice.id}"
        )
        print(
            f"PO ID: {invoice.purchase_order_id}"
        )
        print(
            f"Customer ID: {invoice.customer_id}"
        )
        print(
            f"Total: ₹{invoice.total_amount:.2f}"
        )
        print(
            f"Due Date: {invoice.due_date}"
        )
        print(
            f"Status: {invoice.status}"
        )
        print("=" * 60)

        return {
            "success": True,
            "invoice_id": invoice.id,
            "purchase_order_id": (
                invoice.purchase_order_id
            ),
            "customer_id": invoice.customer_id,
            "invoice_number": (
                invoice.invoice_number
            ),
            "invoice_date": (
                str(invoice.invoice_date)
                if invoice.invoice_date
                else None
            ),
            "total_amount": (
                invoice.total_amount
            ),
            "due_date": (
                str(invoice.due_date)
                if invoice.due_date
                else None
            ),
            "status": invoice.status,
        }

    except Exception:

        db.rollback()
        raise

    finally:
        db.close()


def get_invoice_for_po(
    purchase_order_id: int
):
    """
    Get invoice associated with a PO.
    """

    db = SessionLocal()

    try:

        invoice = (
            db.query(Invoice)
            .filter(
                Invoice.purchase_order_id
                == purchase_order_id
            )
            .first()
        )

        if invoice is None:

            return {
                "success": False,
                "error": "No invoice found."
            }

        return {
            "success": True,
            "invoice_id": invoice.id,
            "purchase_order_id": (
                invoice.purchase_order_id
            ),
            "customer_id": invoice.customer_id,
            "invoice_number": (
                invoice.invoice_number
            ),
            "invoice_date": (
                str(invoice.invoice_date)
                if invoice.invoice_date
                else None
            ),
            "total_amount": invoice.total_amount,
            "due_date": (
                str(invoice.due_date)
                if invoice.due_date
                else None
            ),
            "status": invoice.status,
        }

    finally:

        db.close()