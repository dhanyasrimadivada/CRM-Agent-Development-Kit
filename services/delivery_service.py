from datetime import datetime

from database.db import SessionLocal
from database.models import PurchaseOrder, Delivery


VALID_STATUSES = {
    "NOT_STARTED",
    "IN_PROCESS",
    "COMPLETED",
}


def create_delivery_for_po(
    purchase_order_id: int,
    expected_date=None,
    remarks=None,
):
    """
    Create a delivery record for a Purchase Order.

    Initial status:
        NOT_STARTED
    """

    db = SessionLocal()

    try:
        # --------------------------------------------
        # Find PO
        # --------------------------------------------

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

        # --------------------------------------------
        # Check existing delivery
        # --------------------------------------------

        existing_delivery = (
            db.query(Delivery)
            .filter(
                Delivery.purchase_order_id
                == purchase_order_id
            )
            .first()
        )

        if existing_delivery:

            return {
                "success": True,
                "message": "Delivery already exists.",
                "delivery_id": existing_delivery.id,
                "purchase_order_id": purchase_order_id,
                "delivery_status": (
                    existing_delivery.delivery_status
                ),
            }

        # --------------------------------------------
        # Parse expected date
        # --------------------------------------------

        parsed_expected_date = None

        if expected_date:

            if hasattr(expected_date, "year"):
                parsed_expected_date = expected_date

            else:
                date_string = str(expected_date).strip()

                for fmt in (
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%d-%m-%Y",
                ):
                    try:
                        parsed_expected_date = (
                            datetime.strptime(
                                date_string,
                                fmt
                            ).date()
                        )
                        break

                    except ValueError:
                        continue

        # --------------------------------------------
        # Create delivery
        # --------------------------------------------

        delivery = Delivery(
            purchase_order_id=purchase_order_id,
            delivery_status="NOT_STARTED",
            expected_date=parsed_expected_date,
            remarks=remarks,
        )

        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        print()
        print("=" * 60)
        print("DELIVERY CREATED")
        print("=" * 60)
        print(f"Delivery ID: {delivery.id}")
        print(f"PO ID: {delivery.purchase_order_id}")
        print(
            f"Status: {delivery.delivery_status}"
        )
        print(
            f"Expected Date: {delivery.expected_date}"
        )
        print("=" * 60)

        return {
            "success": True,
            "delivery_id": delivery.id,
            "purchase_order_id": purchase_order_id,
            "delivery_status": (
                delivery.delivery_status
            ),
            "expected_date": (
                str(delivery.expected_date)
                if delivery.expected_date
                else None
            ),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def update_delivery_status(
    delivery_id: int,
    new_status: str,
    actual_date=None,
    remarks=None,
):
    """
    Update delivery status.

    Allowed:
        NOT_STARTED
        IN_PROCESS
        COMPLETED

    When COMPLETED:
        actual_date is automatically recorded.
    """

    db = SessionLocal()

    try:

        new_status = str(
            new_status
        ).strip().upper()

        # --------------------------------------------
        # Validate status
        # --------------------------------------------

        if new_status not in VALID_STATUSES:

            return {
                "success": False,
                "error": (
                    f"Invalid delivery status: "
                    f"{new_status}"
                ),
            }

        # --------------------------------------------
        # Find delivery
        # --------------------------------------------

        delivery = (
            db.query(Delivery)
            .filter(
                Delivery.id == delivery_id
            )
            .first()
        )

        if delivery is None:

            return {
                "success": False,
                "error": "Delivery not found."
            }

        # --------------------------------------------
        # Workflow lock
        # --------------------------------------------
        # COMPLETED is a terminal state. Once delivery is
        # completed, it cannot be moved back to IN_PROCESS
        # or NOT_STARTED.
        if delivery.delivery_status == "COMPLETED" and new_status != "COMPLETED":
            return {
                "success": False,
                "error": (
                    "Delivery is already COMPLETED and cannot be moved "
                    "back to another status."
                ),
            }

        # --------------------------------------------
        # Update status
        # --------------------------------------------

        delivery.delivery_status = new_status

        # --------------------------------------------
        # Actual delivery date
        # --------------------------------------------

        if new_status == "COMPLETED":

            if actual_date:

                if hasattr(actual_date, "year"):
                    delivery.actual_date = actual_date

                else:

                    date_string = str(
                        actual_date
                    ).strip()

                    for fmt in (
                        "%Y-%m-%d",
                        "%d/%m/%Y",
                        "%d-%m-%Y",
                    ):

                        try:

                            delivery.actual_date = (
                                datetime.strptime(
                                    date_string,
                                    fmt
                                ).date()
                            )

                            break

                        except ValueError:
                            continue

            else:

                delivery.actual_date = (
                    datetime.now().date()
                )

        if remarks is not None:
            delivery.remarks = remarks

        db.commit()
        db.refresh(delivery)

        print()
        print("=" * 60)
        print("DELIVERY UPDATED")
        print("=" * 60)
        print(f"Delivery ID: {delivery.id}")
        print(
            f"PO ID: {delivery.purchase_order_id}"
        )
        print(
            f"Status: {delivery.delivery_status}"
        )
        print(
            f"Actual Date: {delivery.actual_date}"
        )
        print("=" * 60)

        return {
            "success": True,
            "delivery_id": delivery.id,
            "purchase_order_id": (
                delivery.purchase_order_id
            ),
            "delivery_status": (
                delivery.delivery_status
            ),
            "actual_date": (
                str(delivery.actual_date)
                if delivery.actual_date
                else None
            ),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_delivery_for_po(
    purchase_order_id: int
):
    """
    Get the delivery record associated with a PO.
    """

    db = SessionLocal()

    try:

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
                "error": "No delivery record found."
            }

        return {
            "success": True,
            "delivery_id": delivery.id,
            "purchase_order_id": (
                delivery.purchase_order_id
            ),
            "delivery_status": (
                delivery.delivery_status
            ),
            "expected_date": (
                str(delivery.expected_date)
                if delivery.expected_date
                else None
            ),
            "actual_date": (
                str(delivery.actual_date)
                if delivery.actual_date
                else None
            ),
            "remarks": delivery.remarks,
        }

    finally:
        db.close()


if __name__ == "__main__":

    print()
    print("=" * 60)
    print("DELIVERY SERVICE TEST")
    print("=" * 60)

    result = create_delivery_for_po(
        purchase_order_id=1,
        expected_date="2026-09-29",
        remarks="Delivery created after PO approval.",
    )

    print()
    print("RESULT:")
    print(result)