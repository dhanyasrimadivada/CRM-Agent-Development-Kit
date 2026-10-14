from datetime import date, datetime

from database.db import SessionLocal
from database.models import (
    Customer,
    Quotation,
    QuotationItem
)


# ============================================================
# CREATE QUOTATION
# ============================================================

def create_quotation(
    customer_id: int,
    quotation_number: str,
    quotation_date: date,
    valid_until: date | None,
    items: list,
    status: str = "DRAFT"
):
    """
    Create a quotation and its quotation items.

    items example:

    [
        {
            "item_code": "ITEM001",
            "description": "Machine Service",
            "hsn_code": "9987",
            "quantity": 1,
            "unit": "EA",
            "unit_price": 100000,
            "tax_rate": 18
        }
    ]
    """

    db = SessionLocal()

    try:

        # ====================================================
        # 1. CHECK CUSTOMER
        # ====================================================

        customer = (
            db.query(Customer)
            .filter(
                Customer.id == customer_id
            )
            .first()
        )

        if customer is None:

            raise ValueError(
                f"Customer with ID "
                f"{customer_id} not found."
            )

        # ====================================================
        # 2. CHECK DUPLICATE QUOTATION NUMBER
        # ====================================================

        existing = (
            db.query(Quotation)
            .filter(
                Quotation.quotation_number
                == quotation_number
            )
            .first()
        )

        if existing:

            raise ValueError(
                f"Quotation "
                f"{quotation_number} "
                f"already exists."
            )

        # ====================================================
        # 3. CALCULATE AMOUNTS
        # ====================================================

        subtotal = 0
        tax_amount = 0

        calculated_items = []

        for item in items:

            quantity = float(
                item.get("quantity", 0)
            )

            unit_price = float(
                item.get("unit_price", 0)
            )

            tax_rate = float(
                item.get("tax_rate", 0)
            )

            line_subtotal = (
                quantity * unit_price
            )

            line_tax = (
                line_subtotal * tax_rate / 100
            )

            line_total = (
                line_subtotal + line_tax
            )

            subtotal += line_subtotal
            tax_amount += line_tax

            calculated_items.append(
                {
                    "item_code": item.get(
                        "item_code",
                        ""
                    ),

                    "description": item.get(
                        "description",
                        ""
                    ),

                    "hsn_code": item.get(
                        "hsn_code",
                        ""
                    ),

                    "quantity": quantity,

                    "unit": item.get(
                        "unit",
                        ""
                    ),

                    "unit_price": unit_price,

                    "tax_rate": tax_rate,

                    "line_total": line_total
                }
            )

        total_amount = (
            subtotal + tax_amount
        )

        # ====================================================
        # 4. CREATE QUOTATION
        # ====================================================

        quotation = Quotation(

            quotation_number=(
                quotation_number
            ),

            customer_id=customer.id,

            quotation_date=quotation_date,

            valid_until=valid_until,

            subtotal=subtotal,

            tax_amount=tax_amount,

            total_amount=total_amount,

            status=status
        )

        db.add(quotation)

        db.flush()

        # ====================================================
        # 5. CREATE QUOTATION ITEMS
        # ====================================================

        for item in calculated_items:

            quotation_item = QuotationItem(

                quotation_id=quotation.id,

                item_code=item["item_code"],

                description=item["description"],

                hsn_code=item["hsn_code"],

                quantity=item["quantity"],

                unit=item["unit"],

                unit_price=item["unit_price"],

                tax_rate=item["tax_rate"],

                line_total=item["line_total"]
            )

            db.add(quotation_item)

        # ====================================================
        # 6. COMMIT
        # ====================================================

        db.commit()

        db.refresh(quotation)

        print()
        print("=" * 60)
        print("QUOTATION CREATED SUCCESSFULLY")
        print("=" * 60)

        print(
            f"Quotation ID: "
            f"{quotation.id}"
        )

        print(
            f"Quotation Number: "
            f"{quotation.quotation_number}"
        )

        print(
            f"Customer: "
            f"{customer.company_name}"
        )

        print(
            f"Subtotal: "
            f"{quotation.subtotal}"
        )

        print(
            f"Tax: "
            f"{quotation.tax_amount}"
        )

        print(
            f"Total: "
            f"{quotation.total_amount}"
        )

        print(
            f"Status: "
            f"{quotation.status}"
        )

        print("=" * 60)

        return quotation

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# ============================================================
# UPDATE QUOTATION STATUS
# ============================================================

def update_quotation_status(
    quotation_id: int,
    new_status: str
):
    """
    Update quotation status.

    Allowed lifecycle:

    DRAFT
      ↓
    SENT
      ↓
    ACCEPTED / DECLINED

    ACCEPTED
      ↓
    AWAITING_PO
    """

    allowed_statuses = {
        "DRAFT",
        "SENT",
        "ACCEPTED",
        "DECLINED",
        "AWAITING_PO"
    }

    if new_status not in allowed_statuses:

        raise ValueError(
            f"Invalid quotation status: "
            f"{new_status}"
        )

    db = SessionLocal()

    try:

        quotation = (
            db.query(Quotation)
            .filter(
                Quotation.id
                == quotation_id
            )
            .first()
        )

        if quotation is None:

            raise ValueError(
                f"Quotation "
                f"{quotation_id} "
                f"not found."
            )

        # ====================================================
        # ACCEPTED
        # ====================================================

        if new_status == "ACCEPTED":

            quotation.status = "ACCEPTED"

            quotation.accepted_at = (
                datetime.utcnow()
            )

        # ====================================================
        # DECLINED
        # ====================================================

        elif new_status == "DECLINED":

            quotation.status = "DECLINED"

            quotation.declined_at = (
                datetime.utcnow()
            )

        # ====================================================
        # OTHER STATUS
        # ====================================================

        else:

            quotation.status = new_status

        # ====================================================
        # ACCEPTED → AWAITING PO
        # ====================================================

        if new_status == "ACCEPTED":

            quotation.status = (
                "AWAITING_PO"
            )

        db.commit()

        db.refresh(quotation)

        print()
        print("=" * 60)
        print("QUOTATION STATUS UPDATED")
        print("=" * 60)

        print(
            f"Quotation: "
            f"{quotation.quotation_number}"
        )

        print(
            f"Status: "
            f"{quotation.status}"
        )

        print("=" * 60)

        return quotation

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# ============================================================
# GET QUOTATION
# ============================================================

def get_quotation(
    quotation_id: int
):
    """
    Get one quotation with its customer
    and quotation items.
    """

    db = SessionLocal()

    try:

        quotation = (
            db.query(Quotation)
            .filter(
                Quotation.id
                == quotation_id
            )
            .first()
        )

        if quotation is None:

            raise ValueError(
                f"Quotation "
                f"{quotation_id} "
                f"not found."
            )

        return quotation

    finally:

        db.close()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # IMPORTANT:
    # Customer ID 1 already exists because
    # we inserted our sample PO earlier.
    # --------------------------------------------------------

    quotation = create_quotation(

        customer_id=1,

        quotation_number="Q-TEST-001",

        quotation_date=date.today(),

        valid_until=None,

        items=[
            {
                "item_code": "E2000102",

                "description":
                    "Supply and installation service",

                "hsn_code": "9987",

                "quantity": 1,

                "unit": "EA",

                "unit_price": 315000,

                "tax_rate": 18
            }
        ]
    )

    # --------------------------------------------------------
    # Test acceptance
    # --------------------------------------------------------

    update_quotation_status(
        quotation.id,
        "ACCEPTED"
    )