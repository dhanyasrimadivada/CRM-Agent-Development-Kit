from math import isclose

from database.db import SessionLocal
from database.models import Quotation


def validate_po_against_quotation(
    quotation_id: int,
    po_data: dict
):
    """
    Validate an extracted PO against the accepted quotation.

    Groq extracts the PO.
    Python performs deterministic business validation.

    Current hard validation rules:
    1. Quotation must exist.
    2. Quotation must be accepted.
    3. PO number must exist.
    4. PO total must exist.
    5. PO total must match quotation total.

    The PO is linked to the quotation using quotation_id.
    """

    db = SessionLocal()

    try:

        # ==================================================
        # FIND QUOTATION
        # ==================================================

        quotation = (
            db.query(Quotation)
            .filter(
                Quotation.id == quotation_id
            )
            .first()
        )

        if quotation is None:
            return {
                "valid": False,
                "errors": [
                    f"Quotation {quotation_id} not found."
                ]
            }

        # ==================================================
        # CHECK QUOTATION STATUS
        # ==================================================

        if quotation.status not in (
            "ACCEPTED",
            "AWAITING_PO",
            "WON"
        ):
            return {
                "valid": False,
                "errors": [
                    "Quotation must be accepted before "
                    "a PO can be verified."
                ]
            }

        errors = []

        # ==================================================
        # EXTRACT PO NUMBER
        # ==================================================

        po_number = str(
            po_data.get("po_number", "")
        ).strip()

        if not po_number:

            errors.append(
                "PO number is missing."
            )

        # ==================================================
        # EXTRACT PO TOTAL
        # ==================================================

        po_amount = float(
            po_data
            .get("amounts", {})
            .get("total_amount", 0)
            or 0
        )

        quotation_amount = float(
            quotation.total_amount or 0
        )

        if po_amount <= 0:

            errors.append(
                "PO total amount is missing or invalid."
            )

        # ==================================================
        # AMOUNT MATCH
        # ==================================================

        if not isclose(
            quotation_amount,
            po_amount,
            abs_tol=0.01
        ):

            errors.append(
                f"Amount mismatch: "
                f"Quotation = ₹{quotation_amount:.2f}, "
                f"PO = ₹{po_amount:.2f}"
            )

        # ==================================================
        # FINAL RESULT
        # ==================================================

        if errors:

            return {
                "valid": False,
                "quotation_id": quotation.id,
                "quotation_number": (
                    quotation.quotation_number
                ),
                "po_number": po_number,
                "quotation_amount": quotation_amount,
                "po_amount": po_amount,
                "errors": errors
            }

        return {
            "valid": True,
            "quotation_id": quotation.id,
            "quotation_number": (
                quotation.quotation_number
            ),
            "po_number": po_number,
            "quotation_amount": quotation_amount,
            "po_amount": po_amount,
            "errors": []
        }

    finally:

        db.close()