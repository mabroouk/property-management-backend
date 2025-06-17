import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models.property import db
from src.routes.auth import auth_bp
from src.routes.property import property_bp
from src.routes.contract import contract_bp
from src.routes.finance import finance_bp
from src.routes.dashboard import dashboard_bp
from src.routes.reports import reports_bp
from src.routes.templates import templates_bp
from src.routes.notifications import notifications_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'property_management_secret_key_2024'
app.config['JWT_SECRET_KEY'] = 'jwt_secret_key_property_management_2024'

# تمكين CORS للسماح بالطلبات من مصادر مختلفة
CORS(app, origins="*")

# تهيئة JWT
jwt = JWTManager(app)

# تسجيل البلوبرينتس
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(property_bp, url_prefix='/api/properties')
app.register_blueprint(contract_bp, url_prefix='/api/contracts')
app.register_blueprint(finance_bp, url_prefix='/api/finance')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(reports_bp, url_prefix='/api/reports')
app.register_blueprint(templates_bp, url_prefix='/api/templates')
app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

# تهيئة قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# إنشاء الجداول
with app.app_context():
    # استيراد جميع النماذج لضمان إنشاء الجداول
    from src.models.property import Company, Branch, Role, User, PropertyType, PropertyCategory, Project, Building, Unit, Property
    from src.models.contract import Person, ContractType, Contract, ContractPayment, Cheque
    from src.models.finance import Account, JournalEntry, JournalEntryDetail, ExpenseCategory, Expense, MaintenanceRequest
    from src.models.notification import Notification, NotificationType, NotificationTemplate, NotificationRule, EmailLog, SMSLog, WhatsAppLog
    
    db.create_all()
    
    # إنشاء بيانات أولية إذا لم تكن موجودة
    if not Company.query.first():
        # إنشاء شركة افتراضية
        default_company = Company(
            name="شركة إدارة العقارات النموذجية",
            name_en="Sample Property Management Company",
            commercial_registration="1234567890",
            tax_number="300123456789003",
            address="الرياض، المملكة العربية السعودية",
            address_en="Riyadh, Saudi Arabia",
            phone="+966 11 123 4567",
            email="info@propertymanagement.com"
        )
        db.session.add(default_company)
        
        # إنشاء أدوار افتراضية
        admin_role = Role(
            name="مدير النظام",
            name_en="System Administrator",
            description="صلاحيات كاملة لإدارة النظام",
            company_id=1
        )
        manager_role = Role(
            name="مدير",
            name_en="Manager",
            description="صلاحيات إدارية للعقارات والعقود",
            company_id=1
        )
        employee_role = Role(
            name="موظف",
            name_en="Employee",
            description="صلاحيات محدودة للعمليات اليومية",
            company_id=1
        )
        
        db.session.add_all([admin_role, manager_role, employee_role])
        
        # إنشاء مستخدم افتراضي
        admin_user = User(
            company_id=1,
            username="admin",
            email="admin@propertymanagement.com",
            first_name="مدير",
            last_name="النظام",
            phone="+966 50 123 4567",
            role_id=1
        )
        admin_user.set_password("admin123")
        db.session.add(admin_user)
        
        # إنشاء أنواع عقارات افتراضية
        property_types = [
            PropertyType(name="شقة", name_en="Apartment", company_id=1),
            PropertyType(name="فيلا", name_en="Villa", company_id=1),
            PropertyType(name="مكتب", name_en="Office", company_id=1),
            PropertyType(name="محل تجاري", name_en="Shop", company_id=1),
            PropertyType(name="مخزن", name_en="Warehouse", company_id=1)
        ]
        db.session.add_all(property_types)
        
        # إنشاء فئات عقارات افتراضية
        property_categories = [
            PropertyCategory(name="سكني", name_en="Residential", company_id=1),
            PropertyCategory(name="تجاري", name_en="Commercial", company_id=1),
            PropertyCategory(name="إداري", name_en="Administrative", company_id=1),
            PropertyCategory(name="صناعي", name_en="Industrial", company_id=1)
        ]
        db.session.add_all(property_categories)
        
        # إنشاء أنواع عقود افتراضية
        contract_types = [
            ContractType(name="عقد إيجار سكني", name_en="Residential Lease", company_id=1),
            ContractType(name="عقد إيجار تجاري", name_en="Commercial Lease", company_id=1),
            ContractType(name="عقد بيع", name_en="Sale Contract", company_id=1),
            ContractType(name="عقد سمسرة", name_en="Brokerage Contract", company_id=1)
        ]
        db.session.add_all(contract_types)
        
        # إنشاء فئات مصروفات افتراضية
        expense_categories = [
            ExpenseCategory(name="صيانة", name_en="Maintenance", company_id=1),
            ExpenseCategory(name="كهرباء", name_en="Electricity", company_id=1),
            ExpenseCategory(name="مياه", name_en="Water", company_id=1),
            ExpenseCategory(name="أمن", name_en="Security", company_id=1),
            ExpenseCategory(name="نظافة", name_en="Cleaning", company_id=1),
            ExpenseCategory(name="إدارية", name_en="Administrative", company_id=1)
        ]
        db.session.add_all(expense_categories)
        
        # إنشاء حسابات محاسبية افتراضية
        accounts = [
            Account(company_id=1, account_code="1000", account_name="الأصول", account_name_en="Assets", account_type="asset"),
            Account(company_id=1, account_code="1100", account_name="الأصول المتداولة", account_name_en="Current Assets", account_type="asset", parent_account_id=1),
            Account(company_id=1, account_code="1110", account_name="النقدية", account_name_en="Cash", account_type="asset", parent_account_id=2),
            Account(company_id=1, account_code="1120", account_name="البنك", account_name_en="Bank", account_type="asset", parent_account_id=2),
            Account(company_id=1, account_code="1130", account_name="المدينون", account_name_en="Accounts Receivable", account_type="asset", parent_account_id=2),
            
            Account(company_id=1, account_code="2000", account_name="الخصوم", account_name_en="Liabilities", account_type="liability"),
            Account(company_id=1, account_code="2100", account_name="الخصوم المتداولة", account_name_en="Current Liabilities", account_type="liability", parent_account_id=6),
            Account(company_id=1, account_code="2110", account_name="الدائنون", account_name_en="Accounts Payable", account_type="liability", parent_account_id=7),
            
            Account(company_id=1, account_code="3000", account_name="حقوق الملكية", account_name_en="Equity", account_type="equity"),
            Account(company_id=1, account_code="3100", account_name="رأس المال", account_name_en="Capital", account_type="equity", parent_account_id=9),
            
            Account(company_id=1, account_code="4000", account_name="الإيرادات", account_name_en="Revenue", account_type="revenue"),
            Account(company_id=1, account_code="4100", account_name="إيرادات الإيجار", account_name_en="Rental Revenue", account_type="revenue", parent_account_id=11),
            
            Account(company_id=1, account_code="5000", account_name="المصروفات", account_name_en="Expenses", account_type="expense"),
            Account(company_id=1, account_code="5100", account_name="مصروفات التشغيل", account_name_en="Operating Expenses", account_type="expense", parent_account_id=13),
            Account(company_id=1, account_code="5110", account_name="مصروفات الصيانة", account_name_en="Maintenance Expenses", account_type="expense", parent_account_id=14),
            Account(company_id=1, account_code="5120", account_name="مصروفات الكهرباء", account_name_en="Electricity Expenses", account_type="expense", parent_account_id=14),
            Account(company_id=1, account_code="5130", account_name="مصروفات المياه", account_name_en="Water Expenses", account_type="expense", parent_account_id=14)
        ]
        db.session.add_all(accounts)
        
        # إنشاء أنواع تنبيهات افتراضية
        notification_types = [
            NotificationType(name="انتهاء العقد", name_en="Contract Expiry", company_id=1),
            NotificationType(name="استحقاق الدفعة", name_en="Payment Due", company_id=1),
            NotificationType(name="طلب صيانة", name_en="Maintenance Request", company_id=1),
            NotificationType(name="تنبيه عام", name_en="General Alert", company_id=1)
        ]
        db.session.add_all(notification_types)
        
        # إنشاء قوالب تنبيهات افتراضية
        notification_templates = [
            NotificationTemplate(
                company_id=1,
                notification_type_id=1,
                name="قالب انتهاء العقد",
                email_subject="تنبيه: انتهاء العقد",
                email_body="عزيزي المستأجر، ينتهي عقد الإيجار الخاص بك قريباً. يرجى التواصل معنا لتجديد العقد.",
                sms_message="تنبيه: ينتهي عقد الإيجار الخاص بك قريباً",
                system_message="ينتهي العقد قريباً",
                auto_send_email=True,
                send_before_days=30
            ),
            NotificationTemplate(
                company_id=1,
                notification_type_id=2,
                name="قالب استحقاق الدفعة",
                email_subject="تذكير: استحقاق دفعة الإيجار",
                email_body="عزيزي المستأجر، تستحق دفعة الإيجار قريباً. يرجى السداد في الموعد المحدد.",
                sms_message="تذكير: تستحق دفعة الإيجار قريباً",
                system_message="دفعة مستحقة",
                auto_send_email=True,
                auto_send_sms=True,
                send_before_days=7
            )
        ]
        db.session.add_all(notification_templates)
        
        # إنشاء قواعد تنبيهات افتراضية
        notification_rules = [
            NotificationRule(
                company_id=1,
                template_id=1,
                name="تنبيه انتهاء العقد",
                description="تنبيه تلقائي قبل انتهاء العقد بـ 30 يوم",
                trigger_event="contract_expiring",
                days_before=30,
                send_to_tenant=True,
                send_to_manager=True
            ),
            NotificationRule(
                company_id=1,
                template_id=2,
                name="تذكير استحقاق الدفعة",
                description="تذكير تلقائي قبل استحقاق الدفعة بـ 7 أيام",
                trigger_event="payment_due",
                days_before=7,
                send_to_tenant=True,
                send_to_manager=True
            )
        ]
        db.session.add_all(notification_rules)
        
        db.session.commit()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "Property Management API is running", 200

@app.errorhandler(404)
def not_found(error):
    return {"error": "Resource not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal server error"}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

