from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from src.models.property import db

# جدول الأشخاص
class Person(db.Model):
    __tablename__ = 'persons'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    person_type = db.Column(db.String(50), nullable=False)  # tenant, landlord, buyer, seller, etc.
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name_en = db.Column(db.String(100))
    last_name_en = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    id_number = db.Column(db.String(100))
    passport_number = db.Column(db.String(100))
    visa_number = db.Column(db.String(100))
    id_expiry_date = db.Column(db.Date)
    passport_expiry_date = db.Column(db.Date)
    visa_expiry_date = db.Column(db.Date)
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10))
    marital_status = db.Column(db.String(20))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))
    address = db.Column(db.Text)
    address_en = db.Column(db.Text)
    emergency_contact_name = db.Column(db.String(255))
    emergency_contact_phone = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # العلاقات
    tenant_contracts = db.relationship('Contract', foreign_keys='Contract.tenant_id', backref='tenant', lazy=True)
    landlord_contracts = db.relationship('Contract', foreign_keys='Contract.landlord_id', backref='landlord', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'person_type': self.person_type,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'first_name_en': self.first_name_en,
            'last_name_en': self.last_name_en,
            'nationality': self.nationality,
            'id_number': self.id_number,
            'passport_number': self.passport_number,
            'visa_number': self.visa_number,
            'id_expiry_date': self.id_expiry_date.isoformat() if self.id_expiry_date else None,
            'passport_expiry_date': self.passport_expiry_date.isoformat() if self.passport_expiry_date else None,
            'visa_expiry_date': self.visa_expiry_date.isoformat() if self.visa_expiry_date else None,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'gender': self.gender,
            'marital_status': self.marital_status,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'address': self.address,
            'address_en': self.address_en,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

# جدول أنواع العقود
class ContractType(db.Model):
    __tablename__ = 'contract_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول العقود
class Contract(db.Model):
    __tablename__ = 'contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    contract_number = db.Column(db.String(100), unique=True, nullable=False)
    contract_type_id = db.Column(db.Integer, db.ForeignKey('contract_types.id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=False)
    landlord_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=False)
    security_deposit = db.Column(db.Numeric(10, 2))
    commission_amount = db.Column(db.Numeric(10, 2))
    commission_percentage = db.Column(db.Numeric(5, 2))
    payment_frequency = db.Column(db.String(20))  # monthly, quarterly, semi_annual, annual
    payment_method = db.Column(db.String(50))
    auto_renewal = db.Column(db.Boolean, default=False)
    renewal_notice_days = db.Column(db.Integer, default=30)
    status = db.Column(db.String(50), default='active')  # active, expired, terminated, renewed
    terms_and_conditions = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    contract_type = db.relationship('ContractType', backref='contracts')
    payments = db.relationship('ContractPayment', backref='contract', lazy=True)
    cheques = db.relationship('Cheque', backref='contract', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'contract_number': self.contract_number,
            'contract_type_id': self.contract_type_id,
            'unit_id': self.unit_id,
            'tenant_id': self.tenant_id,
            'landlord_id': self.landlord_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'rent_amount': float(self.rent_amount) if self.rent_amount else None,
            'security_deposit': float(self.security_deposit) if self.security_deposit else None,
            'commission_amount': float(self.commission_amount) if self.commission_amount else None,
            'commission_percentage': float(self.commission_percentage) if self.commission_percentage else None,
            'payment_frequency': self.payment_frequency,
            'payment_method': self.payment_method,
            'auto_renewal': self.auto_renewal,
            'renewal_notice_days': self.renewal_notice_days,
            'status': self.status,
            'terms_and_conditions': self.terms_and_conditions,
            'notes': self.notes,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول دفعات العقود
class ContractPayment(db.Model):
    __tablename__ = 'contract_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    payment_number = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(10, 2), default=0)
    payment_date = db.Column(db.Date)
    payment_method = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')  # pending, paid, overdue, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    cheques = db.relationship('Cheque', backref='payment', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'payment_number': self.payment_number,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'amount': float(self.amount) if self.amount else None,
            'paid_amount': float(self.paid_amount) if self.paid_amount else None,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول الشيكات
class Cheque(db.Model):
    __tablename__ = 'cheques'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'))
    payment_id = db.Column(db.Integer, db.ForeignKey('contract_payments.id'))
    cheque_number = db.Column(db.String(100), nullable=False)
    bank_name = db.Column(db.String(255))
    account_number = db.Column(db.String(100))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    issue_date = db.Column(db.Date)
    due_date = db.Column(db.Date, nullable=False)
    received_date = db.Column(db.Date)
    deposit_date = db.Column(db.Date)
    clear_date = db.Column(db.Date)
    return_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='received')  # received, deposited, cleared, returned, cancelled
    return_reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'contract_id': self.contract_id,
            'payment_id': self.payment_id,
            'cheque_number': self.cheque_number,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'amount': float(self.amount) if self.amount else None,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'deposit_date': self.deposit_date.isoformat() if self.deposit_date else None,
            'clear_date': self.clear_date.isoformat() if self.clear_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'status': self.status,
            'return_reason': self.return_reason,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

