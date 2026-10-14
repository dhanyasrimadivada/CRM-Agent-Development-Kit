from database.db import SessionLocal
from database.models import Quotation


# ============================================================
# GET ALL QUOTATIONS AWAITING PO
# ============================================================

def get_quotations_awaiting_po():
    """
    Return quotations that are waiting for a PO.

    We return dictionaries instead of SQLAlchemy objects
    so the database session can safely close.
    """

    db = SessionLocal()

    try:

        quotations = (
            db.query(Quotation)
            .filter(
                Quotation.status == "AWAITING_PO"
            )
            .order_by(
                Quotation.created_at.desc()
            )
            .all()
        )

        results = []

        for quotation in quotations:

            results.append(
                {
                    "quotation_id": quotation.id,

                    "quotation_number":
                        quotation.quotation_number,

                    "customer_id":
                        quotation.customer_id,

                    "customer_name":
                        quotation.customer.company_name,

                    "quotation_amount":
                        quotation.total_amount,

                    "status":
                        quotation.status
                }
            )

        return results

    finally:

        db.close()


# ============================================================
# GET SPECIFIC QUOTATION FOR PO UPLOAD
# ============================================================

def get_quotation_for_po_upload(
    quotation_id: int
):
    """
    Get a specific quotation that is waiting for a PO.

    This information will eventually be shown on the
    PO upload page.
    """

    db = SessionLocal()

    try:

        quotation = (
            db.query(Quotation)
            .filter(
                Quotation.id == quotation_id
            )
            .first()
        )

        if quotation is None:

            raise ValueError(
                f"Quotation {quotation_id} not found."
            )

        if quotation.status != "AWAITING_PO":

            raise ValueError(
                f"Quotation "
                f"{quotation.quotation_number} "
                f"is not waiting for a PO."
            )

        result = {
            "quotation_id": quotation.id,

            "quotation_number":
                quotation.quotation_number,

            "customer_id":
                quotation.customer_id,

            "customer_name":
                quotation.customer.company_name,

            "quotation_amount":
                quotation.total_amount,

            "status":
                quotation.status
        }

        return result

    finally:

        db.close()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("QUOTATIONS AWAITING PO")
    print("=" * 60)

    quotations = get_quotations_awaiting_po()

    if not quotations:

        print(
            "No quotations are currently "
            "awaiting PO."
        )

    else:

        for quotation in quotations:

            print()
            print(
                f"Quotation ID: "
                f"{quotation['quotation_id']}"
            )

            print(
                f"Quotation Number: "
                f"{quotation['quotation_number']}"
            )

            print(
                f"Customer: "
                f"{quotation['customer_name']}"
            )

            print(
                f"Amount: "
                f"{quotation['quotation_amount']}"
            )

            print(
                f"Status: "
                f"{quotation['status']}"
            )

    print("=" * 60)

    # --------------------------------------------------------
    # Test our Q-TEST-001 quotation
    # --------------------------------------------------------

    try:

        quotation_info = (
            get_quotation_for_po_upload(1)
        )

        print()
        print("=" * 60)
        print("PO UPLOAD CONTEXT")
        print("=" * 60)

        print(
            f"Quotation ID: "
            f"{quotation_info['quotation_id']}"
        )

        print(
            f"Quotation: "
            f"{quotation_info['quotation_number']}"
        )

        print(
            f"Customer: "
            f"{quotation_info['customer_name']}"
        )

        print(
            f"Amount: "
            f"{quotation_info['quotation_amount']}"
        )

        print(
            f"Status: "
            f"{quotation_info['status']}"
        )

        print("=" * 60)

    except ValueError as e:

        print(
            f"Error: {e}"
        )