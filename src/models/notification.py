from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.property import db

class NotificationType(db.Model):
    """أنواع التنبيهات"""
    __tablename__ = 'notification_types'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    company = db.relationship('Company', backref='notification_types')
    notifications = db.relationship('Notification', backref='notification_type', lazy='dynamic')

class Notification(db.Model):
    """التنبيهات"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    notification_type_id = db.Column(db.Integer, db.ForeignKey('notification_types.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    status = db.Column(db.String(20), default='unread')  # unread, read, archived
    
    # معرفات الكائنات المرتبطة
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'))
    payment_id = db.Column(db.Integer, db.ForeignKey('contract_payments.id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'))
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'))
    maintenance_id = db.Column(db.Integer, db.ForeignKey('maintenance_requests.id'))
    
    # معلومات الإرسال
    send_email = db.Column(db.Boolean, default=False)
    send_sms = db.Column(db.Boolean, default=False)
    send_whatsapp = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    sms_sent = db.Column(db.Boolean, default=False)
    whatsapp_sent = db.Column(db.Boolean, default=False)
    
    # التواريخ
    scheduled_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    company = db.relationship('Company', backref='notifications')
    user = db.relationship('User', backref='notifications')
    contract = db.relationship('Contract', backref='notifications')
    payment = db.relationship('ContractPayment', backref='notifications')
    unit = db.relationship('Unit', backref='notifications')
    expense = db.relationship('Expense', backref='notifications')
    maintenance = db.relationship('MaintenanceRequest', backref='notifications')

class NotificationTemplate(db.Model):
    """قوالب التنبيهات"""
    __tablename__ = 'notification_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    notification_type_id = db.Column(db.Integer, db.ForeignKey('notification_types.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    
    # قوالب الرسائل
    email_subject = db.Column(db.String(200))
    email_body = db.Column(db.Text)
    sms_message = db.Column(db.Text)
    whatsapp_message = db.Column(db.Text)
    system_message = db.Column(db.Text)
    
    # إعدادات الإرسال
    auto_send_email = db.Column(db.Boolean, default=False)
    auto_send_sms = db.Column(db.Boolean, default=False)
    auto_send_whatsapp = db.Column(db.Boolean, default=False)
    
    # إعدادات التوقيت
    send_before_days = db.Column(db.Integer, default=0)
    send_at_time = db.Column(db.Time)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    company = db.relationship('Company', backref='notification_templates')

class NotificationRule(db.Model):
    """قواعد التنبيهات التلقائية"""
    __tablename__ = 'notification_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('notification_templates.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # شروط التفعيل
    trigger_event = db.Column(db.String(50), nullable=False)  # contract_expiring, payment_due, maintenance_due, etc.
    trigger_conditions = db.Column(db.JSON)  # شروط إضافية
    
    # إعدادات التوقيت
    days_before = db.Column(db.Integer, default=0)
    repeat_interval = db.Column(db.Integer)  # بالأيام
    max_repeats = db.Column(db.Integer, default=1)
    
    # إعدادات المستقبلين
    send_to_tenant = db.Column(db.Boolean, default=False)
    send_to_owner = db.Column(db.Boolean, default=False)
    send_to_manager = db.Column(db.Boolean, default=True)
    send_to_users = db.Column(db.JSON)  # قائمة معرفات المستخدمين
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    company = db.relationship('Company', backref='notification_rules')
    template = db.relationship('NotificationTemplate', backref='rules')

class EmailLog(db.Model):
    """سجل الرسائل الإلكترونية"""
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    notification_id = db.Column(db.Integer, db.ForeignKey('notifications.id'))
    
    to_email = db.Column(db.String(255), nullable=False)
    from_email = db.Column(db.String(255))
    subject = db.Column(db.String(500))
    body = db.Column(db.Text)
    
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed, bounced
    error_message = db.Column(db.Text)
    
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    company = db.relationship('Company', backref='email_logs')
    notification = db.relationship('Notification', backref='email_logs')

class SMSLog(db.Model):
    """سجل الرسائل النصية"""
    __tablename__ = 'sms_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    notification_id = db.Column(db.Integer, db.ForeignKey('notifications.id'))
    
    to_phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed, delivered
    provider_id = db.Column(db.String(100))
    error_message = db.Column(db.Text)
    
    sent_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    company = db.relationship('Company', backref='sms_logs')
    notification = db.relationship('Notification', backref='sms_logs')

class WhatsAppLog(db.Model):
    """سجل رسائل الواتساب"""
    __tablename__ = 'whatsapp_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    notification_id = db.Column(db.Integer, db.ForeignKey('notifications.id'))
    
    to_phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed, delivered, read
    message_id = db.Column(db.String(100))
    error_message = db.Column(db.Text)
    
    sent_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    company = db.relationship('Company', backref='whatsapp_logs')
    notification = db.relationship('Notification', backref='whatsapp_logs')

