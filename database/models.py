from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship

from database.db import Base


# =========================================================
# CUSTOMER
# =========================================================

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    customer_code = Column(String(50), unique=True, nullable=True)

    company_name = Column(String(255), nullable=False)

    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))

    address = Column(Text)

    gstin = Column(String(50))
    pan = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    quotations = relationship(
        "Quotation",
        back_populates="customer"
    )

    purchase_orders = relationship(
        "PurchaseOrder",
        back_populates="customer"
    )

    invoices = relationship(
        "Invoice",
        back_populates="customer"
    )

    followups = relationship(
        "FollowUp",
        back_populates="customer"
    )


# =========================================================
# QUOTATION
# =========================================================

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)

    quotation_number = Column(
        String(50),
        unique=True,
        nullable=False
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False
    )

    quotation_date = Column(Date)
    valid_until = Column(Date)

    subtotal = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)

    status = Column(
        String(30),
        default="DRAFT"
    )

    sent_at = Column(DateTime)
    accepted_at = Column(DateTime)
    declined_at = Column(DateTime)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    customer = relationship(
        "Customer",
        back_populates="quotations"
    )

    items = relationship(
        "QuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan"
    )

    purchase_order = relationship(
        "PurchaseOrder",
        back_populates="quotation",
        uselist=False
    )


# =========================================================
# QUOTATION ITEMS
# =========================================================

class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(Integer, primary_key=True)

    quotation_id = Column(
        Integer,
        ForeignKey("quotations.id"),
        nullable=False
    )

    item_code = Column(String(100))

    description = Column(Text)

    hsn_code = Column(String(50))

    quantity = Column(Float, default=0)

    unit = Column(String(50))

    unit_price = Column(Float, default=0)

    tax_rate = Column(Float, default=0)

    line_total = Column(Float, default=0)

    quotation = relationship(
        "Quotation",
        back_populates="items"
    )


# =========================================================
# PURCHASE ORDER
# =========================================================

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)

    quotation_id = Column(
        Integer,
        ForeignKey("quotations.id"),
        nullable=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False
    )

    po_number = Column(
        String(100),
        unique=True,
        nullable=False
    )

    po_date = Column(Date)

    subtotal = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)

    payment_terms = Column(Text)
    payment_days = Column(Integer)

    delivery_terms = Column(Text)
    delivery_date = Column(Date)

    buyer_name = Column(String(255))
    buyer_email = Column(String(255))
    buyer_phone = Column(String(50))

    gstin = Column(String(50))
    pan = Column(String(50))

    status = Column(
        String(30),
        default="RECEIVED"
    )

    source_document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    quotation = relationship(
        "Quotation",
        back_populates="purchase_order"
    )

    customer = relationship(
        "Customer",
        back_populates="purchase_orders"
    )

    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )

    deliveries = relationship(
        "Delivery",
        back_populates="purchase_order"
    )

    invoices = relationship(
        "Invoice",
        back_populates="purchase_order"
    )


# =========================================================
# PURCHASE ORDER ITEMS
# =========================================================

class PurchaseOrderItem(Base):
    __tablename__ = "po_items"

    id = Column(Integer, primary_key=True)

    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id"),
        nullable=False
    )

    item_code = Column(String(100))

    description = Column(Text)

    hsn_code = Column(String(50))

    uom = Column(String(50))

    quantity = Column(Float, default=0)

    unit_price = Column(Float, default=0)

    tax_rate = Column(Float, default=0)

    line_total = Column(Float, default=0)

    delivery_date = Column(Date)

    purchase_order = relationship(
        "PurchaseOrder",
        back_populates="items"
    )


# =========================================================
# DELIVERY
# =========================================================

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True)

    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id"),
        nullable=False
    )

    delivery_status = Column(
        String(30),
        default="NOT_STARTED"
    )

    expected_date = Column(Date)

    actual_date = Column(Date)

    delivery_document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=True
    )

    remarks = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    purchase_order = relationship(
        "PurchaseOrder",
        back_populates="deliveries"
    )


# =========================================================
# INVOICE
# =========================================================

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id"),
        nullable=False
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False
    )

    invoice_number = Column(
        String(100),
        unique=True,
        nullable=False
    )

    invoice_date = Column(Date)

    subtotal = Column(Float, default=0)

    tax_amount = Column(Float, default=0)

    total_amount = Column(Float, default=0)

    payment_terms = Column(Text)

    payment_days = Column(Integer)

    due_date = Column(Date)

    status = Column(
        String(30),
        default="PENDING"
    )

    source_document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    purchase_order = relationship(
        "PurchaseOrder",
        back_populates="invoices"
    )

    customer = relationship(
        "Customer",
        back_populates="invoices"
    )

    payments = relationship(
        "Payment",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )

    followups = relationship(
        "FollowUp",
        back_populates="invoice"
    )


# =========================================================
# PAYMENT
# =========================================================

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)

    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False
    )

    amount = Column(Float, default=0)

    payment_date = Column(Date)

    payment_method = Column(String(100))

    reference_number = Column(String(100))

    status = Column(
        String(30),
        default="PENDING"
    )

    notes = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    invoice = relationship(
        "Invoice",
        back_populates="payments"
    )


# =========================================================
# FOLLOW-UP
# =========================================================

class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False
    )

    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=True
    )

    followup_date = Column(DateTime)

    contact_type = Column(String(50))

    response_status = Column(String(50))

    subject = Column(String(255))

    notes = Column(Text)

    email_message_id = Column(String(255))

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    customer = relationship(
        "Customer",
        back_populates="followups"
    )

    invoice = relationship(
        "Invoice",
        back_populates="followups"
    )


# =========================================================
# DOCUMENT
# =========================================================

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)

    document_type = Column(
        String(50),
        nullable=False
    )

    file_name = Column(String(255))

    file_path = Column(Text)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=True
    )

    quotation_id = Column(
        Integer,
        ForeignKey("quotations.id"),
        nullable=True
    )

    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id"),
        nullable=True
    )

    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=True
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    processing_status = Column(
        String(30),
        default="UPLOADED"
    )

    validation_status = Column(
        String(30),
        default="PENDING"
    )

    extracted_data = Column(Text)