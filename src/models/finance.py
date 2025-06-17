from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.property import db

# جدول الحسابات
class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    account_code = db.Column(db.String(50), unique=True, nullable=False)
    account_name = db.Column(db.String(255), nullable=False)
    account_name_en = db.Column(db.String(255))
    account_type = db.Column(db.String(50))  # asset, liability, equity, revenue, expense
    parent_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    parent_account = db.relationship('Account', remote_side=[id], backref='sub_accounts')
    journal_entries = db.relationship('JournalEntryDetail', backref='account', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'account_code': self.account_code,
            'account_name': self.account_name,
            'account_name_en': self.account_name_en,
            'account_type': self.account_type,
            'parent_account_id': self.parent_account_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول القيود اليومية
class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    entry_number = db.Column(db.String(100), unique=True, nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    reference_type = db.Column(db.String(50))  # contract, payment, expense, etc.
    reference_id = db.Column(db.Integer)
    total_debit = db.Column(db.Numeric(15, 2), nullable=False)
    total_credit = db.Column(db.Numeric(15, 2), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    details = db.relationship('JournalEntryDetail', backref='journal_entry', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'entry_number': self.entry_number,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'description': self.description,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'total_debit': float(self.total_debit) if self.total_debit else None,
            'total_credit': float(self.total_credit) if self.total_credit else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول تفاصيل القيود
class JournalEntryDetail(db.Model):
    __tablename__ = 'journal_entry_details'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit_amount = db.Column(db.Numeric(15, 2), default=0)
    credit_amount = db.Column(db.Numeric(15, 2), default=0)
    description = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'journal_entry_id': self.journal_entry_id,
            'account_id': self.account_id,
            'debit_amount': float(self.debit_amount) if self.debit_amount else None,
            'credit_amount': float(self.credit_amount) if self.credit_amount else None,
            'description': self.description
        }

# جدول فئات المصروفات
class ExpenseCategory(db.Model):
    __tablename__ = 'expense_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    expenses = db.relationship('Expense', backref='category', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول المصروفات
class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    expense_number = db.Column(db.String(100), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id'))
    property_id = db.Column(db.Integer)  # can reference buildings or units
    property_type = db.Column(db.String(20))  # 'building' or 'unit' or 'general'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    vendor_name = db.Column(db.String(255))
    invoice_number = db.Column(db.String(100))
    payment_method = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')  # pending, paid, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'expense_number': self.expense_number,
            'category_id': self.category_id,
            'property_id': self.property_id,
            'property_type': self.property_type,
            'amount': float(self.amount) if self.amount else None,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'description': self.description,
            'vendor_name': self.vendor_name,
            'invoice_number': self.invoice_number,
            'payment_method': self.payment_method,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول طلبات الصيانة
class MaintenanceRequest(db.Model):
    __tablename__ = 'maintenance_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    request_number = db.Column(db.String(100), unique=True, nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'))
    tenant_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    category = db.Column(db.String(100))
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='open')  # open, assigned, in_progress, completed, cancelled
    reported_date = db.Column(db.Date, nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    scheduled_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    estimated_cost = db.Column(db.Numeric(10, 2))
    actual_cost = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    unit = db.relationship('Unit', backref='maintenance_requests')
    tenant = db.relationship('Person', backref='maintenance_requests')
    assigned_user = db.relationship('User', backref='assigned_maintenance_requests')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'request_number': self.request_number,
            'unit_id': self.unit_id,
            'tenant_id': self.tenant_id,
            'category': self.category,
            'priority': self.priority,
            'description': self.description,
            'status': self.status,
            'reported_date': self.reported_date.isoformat() if self.reported_date else None,
            'assigned_to': self.assigned_to,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

