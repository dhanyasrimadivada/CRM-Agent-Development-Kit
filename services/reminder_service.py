import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

from database.db import SessionLocal
from database.models import Invoice
from services.followup_service import create_followup


load_dotenv()


def send_payment_reminder(invoice_id):

    db = SessionLocal()

    try:
        invoice = db.query(Invoice).filter(
            Invoice.id == invoice_id
        ).first()

        if not invoice:
            raise ValueError(
                f"Invoice {invoice_id} not found."
            )

        if invoice.status != "OVERDUE":
            raise ValueError(
                "Reminder can only be sent for overdue invoices."
            )

        customer = invoice.customer

        if not customer.email:
            raise ValueError(
                "Customer email is missing."
            )

        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_APP_PASSWORD")

        if not sender_email or not sender_password:
            raise ValueError(
                "Email credentials are not configured."
            )

        message = EmailMessage()

        message["Subject"] = (
            f"Payment Reminder - Invoice "
            f"{invoice.invoice_number}"
        )

        message["From"] = sender_email
        message["To"] = customer.email

        message.set_content(
            f"""
Dear {customer.contact_person or customer.company_name},

This is a reminder regarding the pending payment for:

Invoice: {invoice.invoice_number}
Amount: ₹{invoice.total_amount}
Due Date: {invoice.due_date}

Kindly arrange the payment at the earliest.

Regards,
Accounts Team
"""
        )

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as server:

            server.login(
                sender_email,
                sender_password
            )

            server.send_message(message)

        create_followup(
            invoice_id=invoice.id,
            contact_type="EMAIL",
            response_status="PENDING",
            subject=message["Subject"],
            notes="Payment reminder email sent."
        )

        print()
        print("=" * 60)
        print("PAYMENT REMINDER SENT")
        print("=" * 60)
        print(f"Invoice: {invoice.invoice_number}")
        print(f"Customer: {customer.company_name}")
        print(f"Email: {customer.email}")
        print("=" * 60)

        return True

    finally:
        db.close()