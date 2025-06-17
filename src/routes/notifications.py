from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.property import db, User, Company
from src.models.contract import Contract, ContractPayment, Person
from src.models.finance import Expense, MaintenanceRequest
from src.models.notification import (
    Notification, NotificationType, NotificationTemplate, 
    NotificationRule, EmailLog, SMSLog, WhatsAppLog
)
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, func
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

notifications_bp = Blueprint('notifications', __name__)

def get_user_company():
    """الحصول على شركة المستخدم الحالي"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.company if user else None

class NotificationService:
    """خدمة إدارة التنبيهات"""
    
    @staticmethod
    def create_notification(company_id, notification_type_id, title, message, 
                          priority='normal', user_id=None, **kwargs):
        """إنشاء تنبيه جديد"""
        try:
            notification = Notification(
                company_id=company_id,
                notification_type_id=notification_type_id,
                user_id=user_id,
                title=title,
                message=message,
                priority=priority,
                **kwargs
            )
            
            db.session.add(notification)
            db.session.commit()
            
            return notification
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def send_email(to_email, subject, body, company_id, notification_id=None):
        """إرسال بريد إلكتروني"""
        try:
            # إنشاء سجل البريد الإلكتروني
            email_log = EmailLog(
                company_id=company_id,
                notification_id=notification_id,
                to_email=to_email,
                subject=subject,
                body=body,
                status='pending'
            )
            db.session.add(email_log)
            db.session.commit()
            
            # هنا يمكن إضافة كود إرسال البريد الإلكتروني الفعلي
            # باستخدام SMTP أو خدمة مثل SendGrid
            
            # محاكاة الإرسال الناجح
            email_log.status = 'sent'
            email_log.sent_at = datetime.utcnow()
            db.session.commit()
            
            return True
            
        except Exception as e:
            if 'email_log' in locals():
                email_log.status = 'failed'
                email_log.error_message = str(e)
                db.session.commit()
            return False
    
    @staticmethod
    def send_sms(to_phone, message, company_id, notification_id=None):
        """إرسال رسالة نصية"""
        try:
            # إنشاء سجل الرسالة النصية
            sms_log = SMSLog(
                company_id=company_id,
                notification_id=notification_id,
                to_phone=to_phone,
                message=message,
                status='pending'
            )
            db.session.add(sms_log)
            db.session.commit()
            
            # هنا يمكن إضافة كود إرسال الرسالة النصية الفعلي
            # باستخدام خدمة مثل Twilio أو مزود محلي
            
            # محاكاة الإرسال الناجح
            sms_log.status = 'sent'
            sms_log.sent_at = datetime.utcnow()
            db.session.commit()
            
            return True
            
        except Exception as e:
            if 'sms_log' in locals():
                sms_log.status = 'failed'
                sms_log.error_message = str(e)
                db.session.commit()
            return False
    
    @staticmethod
    def send_whatsapp(to_phone, message, company_id, notification_id=None):
        """إرسال رسالة واتساب"""
        try:
            # إنشاء سجل رسالة الواتساب
            whatsapp_log = WhatsAppLog(
                company_id=company_id,
                notification_id=notification_id,
                to_phone=to_phone,
                message=message,
                status='pending'
            )
            db.session.add(whatsapp_log)
            db.session.commit()
            
            # هنا يمكن إضافة كود إرسال رسالة الواتساب الفعلي
            # باستخدام WhatsApp Business API
            
            # محاكاة الإرسال الناجح
            whatsapp_log.status = 'sent'
            whatsapp_log.sent_at = datetime.utcnow()
            db.session.commit()
            
            return True
            
        except Exception as e:
            if 'whatsapp_log' in locals():
                whatsapp_log.status = 'failed'
                whatsapp_log.error_message = str(e)
                db.session.commit()
            return False
    
    @staticmethod
    def process_notification_rules():
        """معالجة قواعد التنبيهات التلقائية"""
        try:
            today = date.today()
            
            # قواعد انتهاء العقود
            NotificationService._process_contract_expiry_rules(today)
            
            # قواعد استحقاق الدفعات
            NotificationService._process_payment_due_rules(today)
            
            # قواعد طلبات الصيانة
            NotificationService._process_maintenance_rules(today)
            
            return True
            
        except Exception as e:
            print(f"خطأ في معالجة قواعد التنبيهات: {e}")
            return False
    
    @staticmethod
    def _process_contract_expiry_rules(today):
        """معالجة قواعد انتهاء العقود"""
        rules = NotificationRule.query.filter_by(
            trigger_event='contract_expiring',
            is_active=True
        ).all()
        
        for rule in rules:
            # البحث عن العقود التي ستنتهي
            expiry_date = today + timedelta(days=rule.days_before)
            
            contracts = Contract.query.filter(
                and_(
                    Contract.company_id == rule.company_id,
                    Contract.end_date == expiry_date,
                    Contract.status == 'active'
                )
            ).all()
            
            for contract in contracts:
                # التحقق من عدم إرسال التنبيه مسبقاً
                existing = Notification.query.filter(
                    and_(
                        Notification.company_id == rule.company_id,
                        Notification.contract_id == contract.id,
                        Notification.notification_type_id == rule.template.notification_type_id,
                        Notification.created_at >= today
                    )
                ).first()
                
                if not existing:
                    NotificationService._create_contract_expiry_notification(contract, rule)
    
    @staticmethod
    def _process_payment_due_rules(today):
        """معالجة قواعد استحقاق الدفعات"""
        rules = NotificationRule.query.filter_by(
            trigger_event='payment_due',
            is_active=True
        ).all()
        
        for rule in rules:
            # البحث عن الدفعات المستحقة
            due_date = today + timedelta(days=rule.days_before)
            
            payments = ContractPayment.query.join(Contract).filter(
                and_(
                    Contract.company_id == rule.company_id,
                    ContractPayment.due_date == due_date,
                    ContractPayment.status == 'pending'
                )
            ).all()
            
            for payment in payments:
                # التحقق من عدم إرسال التنبيه مسبقاً
                existing = Notification.query.filter(
                    and_(
                        Notification.company_id == rule.company_id,
                        Notification.payment_id == payment.id,
                        Notification.notification_type_id == rule.template.notification_type_id,
                        Notification.created_at >= today
                    )
                ).first()
                
                if not existing:
                    NotificationService._create_payment_due_notification(payment, rule)
    
    @staticmethod
    def _process_maintenance_rules(today):
        """معالجة قواعد طلبات الصيانة"""
        rules = NotificationRule.query.filter_by(
            trigger_event='maintenance_overdue',
            is_active=True
        ).all()
        
        for rule in rules:
            # البحث عن طلبات الصيانة المتأخرة
            overdue_date = today - timedelta(days=rule.days_before)
            
            maintenance_requests = MaintenanceRequest.query.filter(
                and_(
                    MaintenanceRequest.company_id == rule.company_id,
                    MaintenanceRequest.requested_date <= overdue_date,
                    MaintenanceRequest.status.in_(['pending', 'in_progress'])
                )
            ).all()
            
            for maintenance in maintenance_requests:
                # التحقق من عدم إرسال التنبيه مسبقاً
                existing = Notification.query.filter(
                    and_(
                        Notification.company_id == rule.company_id,
                        Notification.maintenance_id == maintenance.id,
                        Notification.notification_type_id == rule.template.notification_type_id,
                        Notification.created_at >= today
                    )
                ).first()
                
                if not existing:
                    NotificationService._create_maintenance_overdue_notification(maintenance, rule)
    
    @staticmethod
    def _create_contract_expiry_notification(contract, rule):
        """إنشاء تنبيه انتهاء العقد"""
        template = rule.template
        
        title = f"انتهاء العقد رقم {contract.contract_number}"
        message = f"ينتهي العقد رقم {contract.contract_number} في تاريخ {contract.end_date.strftime('%Y-%m-%d')}"
        
        notification = NotificationService.create_notification(
            company_id=rule.company_id,
            notification_type_id=template.notification_type_id,
            title=title,
            message=message,
            priority='high',
            contract_id=contract.id,
            send_email=template.auto_send_email,
            send_sms=template.auto_send_sms,
            send_whatsapp=template.auto_send_whatsapp
        )
        
        # إرسال التنبيهات حسب الإعدادات
        if rule.send_to_tenant and contract.tenant and template.auto_send_email:
            NotificationService.send_email(
                contract.tenant.email,
                title,
                message,
                rule.company_id,
                notification.id
            )
    
    @staticmethod
    def _create_payment_due_notification(payment, rule):
        """إنشاء تنبيه استحقاق الدفعة"""
        template = rule.template
        
        title = f"استحقاق دفعة العقد رقم {payment.contract.contract_number}"
        message = f"تستحق دفعة بمبلغ {payment.amount:,.2f} ريال في تاريخ {payment.due_date.strftime('%Y-%m-%d')}"
        
        notification = NotificationService.create_notification(
            company_id=rule.company_id,
            notification_type_id=template.notification_type_id,
            title=title,
            message=message,
            priority='normal',
            payment_id=payment.id,
            contract_id=payment.contract_id,
            send_email=template.auto_send_email,
            send_sms=template.auto_send_sms,
            send_whatsapp=template.auto_send_whatsapp
        )
        
        # إرسال التنبيهات حسب الإعدادات
        if rule.send_to_tenant and payment.contract.tenant and template.auto_send_email:
            NotificationService.send_email(
                payment.contract.tenant.email,
                title,
                message,
                rule.company_id,
                notification.id
            )
    
    @staticmethod
    def _create_maintenance_overdue_notification(maintenance, rule):
        """إنشاء تنبيه تأخر الصيانة"""
        template = rule.template
        
        title = f"تأخر طلب الصيانة رقم {maintenance.id}"
        message = f"طلب الصيانة المقدم في {maintenance.requested_date.strftime('%Y-%m-%d')} لم يتم إنجازه بعد"
        
        notification = NotificationService.create_notification(
            company_id=rule.company_id,
            notification_type_id=template.notification_type_id,
            title=title,
            message=message,
            priority='high',
            maintenance_id=maintenance.id,
            unit_id=maintenance.unit_id,
            send_email=template.auto_send_email,
            send_sms=template.auto_send_sms,
            send_whatsapp=template.auto_send_whatsapp
        )

@notifications_bp.route('/', methods=['GET'])
@jwt_required()
def get_notifications():
    """الحصول على قائمة التنبيهات"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        query = Notification.query.filter_by(company_id=company.id)
        
        if status:
            query = query.filter_by(status=status)
        
        if priority:
            query = query.filter_by(priority=priority)
        
        notifications = query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'notifications': [{
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'priority': n.priority,
                'status': n.status,
                'created_at': n.created_at.isoformat(),
                'read_at': n.read_at.isoformat() if n.read_at else None,
                'contract_id': n.contract_id,
                'payment_id': n.payment_id,
                'unit_id': n.unit_id
            } for n in notifications.items],
            'total': notifications.total,
            'pages': notifications.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    """تمييز التنبيه كمقروء"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        notification = Notification.query.filter_by(
            id=notification_id,
            company_id=company.id
        ).first()
        
        if not notification:
            return jsonify({'error': 'التنبيه غير موجود'}), 404
        
        notification.status = 'read'
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'تم تمييز التنبيه كمقروء'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/mark-all-read', methods=['PUT'])
@jwt_required()
def mark_all_notifications_read():
    """تمييز جميع التنبيهات كمقروءة"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        Notification.query.filter_by(
            company_id=company.id,
            status='unread'
        ).update({
            'status': 'read',
            'read_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return jsonify({'message': 'تم تمييز جميع التنبيهات كمقروءة'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_notification_stats():
    """إحصائيات التنبيهات"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        total = Notification.query.filter_by(company_id=company.id).count()
        unread = Notification.query.filter_by(company_id=company.id, status='unread').count()
        high_priority = Notification.query.filter_by(
            company_id=company.id, 
            priority='high',
            status='unread'
        ).count()
        urgent = Notification.query.filter_by(
            company_id=company.id, 
            priority='urgent',
            status='unread'
        ).count()
        
        return jsonify({
            'total': total,
            'unread': unread,
            'high_priority': high_priority,
            'urgent': urgent
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/send', methods=['POST'])
@jwt_required()
def send_notification():
    """إرسال تنبيه جديد"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        # إنشاء التنبيه
        notification = NotificationService.create_notification(
            company_id=company.id,
            notification_type_id=data.get('notification_type_id', 1),
            title=data.get('title'),
            message=data.get('message'),
            priority=data.get('priority', 'normal'),
            user_id=data.get('user_id'),
            send_email=data.get('send_email', False),
            send_sms=data.get('send_sms', False),
            send_whatsapp=data.get('send_whatsapp', False)
        )
        
        # إرسال البريد الإلكتروني إذا كان مطلوباً
        if data.get('send_email') and data.get('email'):
            NotificationService.send_email(
                data.get('email'),
                data.get('title'),
                data.get('message'),
                company.id,
                notification.id
            )
        
        # إرسال الرسالة النصية إذا كان مطلوباً
        if data.get('send_sms') and data.get('phone'):
            NotificationService.send_sms(
                data.get('phone'),
                data.get('message'),
                company.id,
                notification.id
            )
        
        # إرسال رسالة الواتساب إذا كان مطلوباً
        if data.get('send_whatsapp') and data.get('phone'):
            NotificationService.send_whatsapp(
                data.get('phone'),
                data.get('message'),
                company.id,
                notification.id
            )
        
        return jsonify({
            'message': 'تم إرسال التنبيه بنجاح',
            'notification_id': notification.id
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/process-rules', methods=['POST'])
@jwt_required()
def process_notification_rules():
    """معالجة قواعد التنبيهات التلقائية"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        success = NotificationService.process_notification_rules()
        
        if success:
            return jsonify({'message': 'تم معالجة قواعد التنبيهات بنجاح'}), 200
        else:
            return jsonify({'error': 'فشل في معالجة قواعد التنبيهات'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/templates', methods=['GET'])
@jwt_required()
def get_notification_templates():
    """الحصول على قوالب التنبيهات"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        templates = NotificationTemplate.query.filter_by(
            company_id=company.id,
            is_active=True
        ).all()
        
        return jsonify({
            'templates': [{
                'id': t.id,
                'name': t.name,
                'email_subject': t.email_subject,
                'email_body': t.email_body,
                'sms_message': t.sms_message,
                'whatsapp_message': t.whatsapp_message,
                'auto_send_email': t.auto_send_email,
                'auto_send_sms': t.auto_send_sms,
                'auto_send_whatsapp': t.auto_send_whatsapp
            } for t in templates]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/rules', methods=['GET'])
@jwt_required()
def get_notification_rules():
    """الحصول على قواعد التنبيهات"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        rules = NotificationRule.query.filter_by(
            company_id=company.id,
            is_active=True
        ).all()
        
        return jsonify({
            'rules': [{
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'trigger_event': r.trigger_event,
                'days_before': r.days_before,
                'send_to_tenant': r.send_to_tenant,
                'send_to_owner': r.send_to_owner,
                'send_to_manager': r.send_to_manager,
                'template': {
                    'name': r.template.name,
                    'auto_send_email': r.template.auto_send_email,
                    'auto_send_sms': r.template.auto_send_sms,
                    'auto_send_whatsapp': r.template.auto_send_whatsapp
                } if r.template else None
            } for r in rules]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

