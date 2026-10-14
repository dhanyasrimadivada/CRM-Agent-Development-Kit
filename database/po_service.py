from datetime import datetime

from database.db import SessionLocal
from database.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    Customer,
)


def save_purchase_order(
    purchase_order_data,
    file_path=None,
    quotation_id=None
):
    """
    Save extracted Purchase Order data into the database.

    purchase_order_data is the dictionary returned by
    documents.processor.process_purchase_order().
    """

    db = SessionLocal()

    try:

        # ==================================================
        # EXTRACT DATA
        # ==================================================

        po_number = str(
            purchase_order_data.get("po_number", "")
        ).strip()

        po_date = purchase_order_data.get("po_date")

        customer_data = (
            purchase_order_data.get("customer")
            or {}
        )

        amounts = (
            purchase_order_data.get("amounts")
            or {}
        )

        payment_terms = (
            purchase_order_data.get("payment_terms")
            or {}
        )

        delivery_terms = (
            purchase_order_data.get("delivery_terms")
            or {}
        )

        buyer = (
            purchase_order_data.get("buyer")
            or {}
        )

        items = (
            purchase_order_data.get("items")
            or []
        )

        # ==================================================
        # FIND / CREATE CUSTOMER
        # ==================================================

        customer_name = str(
            customer_data.get("company_name")
            or customer_data.get("name")
            or buyer.get("company_name")
            or buyer.get("name")
            or ""
        ).strip()

        customer_email = str(
            customer_data.get("email")
            or buyer.get("email")
            or ""
        ).strip()

        customer_gstin = str(
            customer_data.get("gstin")
            or buyer.get("gstin")
            or ""
        ).strip()

        customer_address = str(
            customer_data.get("address")
            or buyer.get("address")
            or ""
        ).strip()

        customer = None

        if customer_name:

            customer = (
                db.query(Customer)
                .filter(
                    Customer.company_name.ilike(
                        customer_name
                    )
                )
                .first()
            )

        if customer is None:

            customer = Customer(
                customer_code=(
                    f"CUST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                ),
                company_name=customer_name or "Unknown",
                email=customer_email or None,
                address=customer_address or None,
                gstin=customer_gstin or None,
            )

            db.add(customer)
            db.flush()

        # ==================================================
        # CHECK DUPLICATE PO
        # ==================================================

        existing_po = (
            db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.po_number == po_number
            )
            .first()
        )

        if existing_po:

            # If this PO already exists, make sure it is
            # linked to the quotation.

            if quotation_id:
                existing_po.quotation_id = quotation_id

            db.commit()

            return existing_po

        # ==================================================
        # PARSE PO DATE
        # ==================================================

        parsed_po_date = None

        if po_date:

            if isinstance(po_date, datetime):
                parsed_po_date = po_date.date()

            else:

                date_string = str(po_date).strip()

                date_formats = [
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%d-%m-%Y",
                    "%d-%b-%y",
                    "%d-%B-%Y",
                ]

                for fmt in date_formats:

                    try:

                        parsed_po_date = datetime.strptime(
                            date_string,
                            fmt
                        ).date()

                        break

                    except ValueError:
                        continue

        # ==================================================
        # CREATE PURCHASE ORDER
        # ==================================================

        purchase_order = PurchaseOrder(
            quotation_id=quotation_id,
            customer_id=customer.id,
            po_number=po_number,
            po_date=parsed_po_date,

            subtotal=float(
                amounts.get("subtotal", 0) or 0
            ),

            tax_amount=float(
                amounts.get("tax_amount", 0) or 0
            ),

            total_amount=float(
                amounts.get("total_amount", 0) or 0
            ),

            payment_terms=str(
                payment_terms.get("description")
                or payment_terms.get("terms")
                or ""
            ) or None,

            payment_days=(
                int(payment_terms.get("payment_days"))
                if payment_terms.get("payment_days")
                else None
            ),

            delivery_terms=str(
                delivery_terms.get("description")
                or delivery_terms.get("terms")
                or ""
            ) or None,

            status="RECEIVED",
        )

        db.add(purchase_order)
        db.flush()

        # ==================================================
        # SAVE ITEMS
        # ==================================================

        for item in items:

            if not isinstance(item, dict):
                continue

            purchase_order_item = PurchaseOrderItem(

    purchase_order_id=purchase_order.id,

    item_code=str(
        item.get("item_code")
        or item.get("code")
        or ""
    ) or None,

    description=str(
        item.get("description")
        or item.get("item_description")
        or item.get("name")
        or ""
    ),

    hsn_code=str(
        item.get("hsn_code")
        or item.get("hsn_sac")
        or ""
    ) or None,

    uom=str(
        item.get("unit")
        or item.get("uom")
        or ""
    ) or None,

    quantity=float(
        item.get("quantity", 0) or 0
    ),

    unit_price=float(
        item.get("unit_price")
        or item.get("rate")
        or 0
    ),

    tax_rate=float(
        item.get("tax_rate", 0) or 0
    ),

    line_total=float(
        item.get("line_total")
        or item.get("amount")
        or 0
    ),

    delivery_date=None,
)

            db.add(purchase_order_item)

        # ==================================================
        # COMMIT
        # ==================================================

        db.commit()
        db.refresh(purchase_order)

        print()
        print("=" * 60)
        print("PURCHASE ORDER SAVED")
        print("=" * 60)
        print(f"PO Number: {purchase_order.po_number}")
        print(f"PO ID: {purchase_order.id}")
        print(f"Quotation ID: {purchase_order.quotation_id}")
        print(f"Customer ID: {purchase_order.customer_id}")
        print(f"Total: ₹{purchase_order.total_amount:.2f}")
        print("=" * 60)

        return purchase_order

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()