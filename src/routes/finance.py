from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.property import db, User
from src.models.finance import Expense, ExpenseCategory, MaintenanceRequest
from src.models.contract import Contract, ContractPayment
from datetime import datetime, date
from sqlalchemy import and_, or_, func, extract
from dateutil.relativedelta import relativedelta

finance_bp = Blueprint('finance', __name__)

def get_user_company():
    """الحصول على شركة المستخدم الحالي"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.company_id if user else None

# ===== إدارة المصروفات =====

@finance_bp.route('/expenses', methods=['GET'])
@jwt_required()
def get_expenses():
    """الحصول على قائمة المصروفات"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        category_id = request.args.get('category_id', type=int)
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Expense.query.filter_by(company_id=company_id)
        
        if search:
            query = query.filter(or_(
                Expense.expense_number.contains(search),
                Expense.description.contains(search),
                Expense.vendor_name.contains(search)
            ))
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if start_date:
            query = query.filter(Expense.expense_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        
        if end_date:
            query = query.filter(Expense.expense_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        expenses = query.order_by(Expense.expense_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # إضافة معلومات إضافية
        expenses_data = []
        for expense in expenses.items:
            expense_dict = expense.to_dict()
            
            if expense.category:
                expense_dict['category'] = expense.category.to_dict()
            
            expenses_data.append(expense_dict)
        
        return jsonify({
            'expenses': expenses_data,
            'total': expenses.total,
            'pages': expenses.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@finance_bp.route('/expenses', methods=['POST'])
@jwt_required()
def create_expense():
    """إنشاء مصروف جديد"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('amount') or not data.get('expense_date'):
            return jsonify({'error': 'المبلغ وتاريخ المصروف مطلوبان'}), 400
        
        # إنشاء رقم مصروف تلقائي
        expense_count = Expense.query.filter_by(company_id=company_id).count()
        expense_number = f"EXP-{datetime.now().year}-{expense_count + 1:04d}"
        
        expense = Expense(
            company_id=company_id,
            expense_number=expense_number,
            category_id=data.get('category_id'),
            property_id=data.get('property_id'),
            property_type=data.get('property_type', 'general'),
            amount=data['amount'],
            expense_date=datetime.strptime(data['expense_date'], '%Y-%m-%d').date(),
            description=data.get('description'),
            vendor_name=data.get('vendor_name'),
            invoice_number=data.get('invoice_number'),
            payment_method=data.get('payment_method'),
            status=data.get('status', 'pending'),
            created_by=get_jwt_identity()
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء المصروف بنجاح',
            'expense': expense.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@finance_bp.route('/expenses/<int:expense_id>', methods=['PUT'])
@jwt_required()
def update_expense(expense_id):
    """تحديث مصروف"""
    try:
        company_id = get_user_company()
        expense = Expense.query.filter_by(id=expense_id, company_id=company_id).first()
        
        if not expense:
            return jsonify({'error': 'المصروف غير موجود'}), 404
        
        data = request.get_json()
        
        # تحديث البيانات
        for field in ['category_id', 'property_id', 'property_type', 'amount', 
                     'expense_date', 'description', 'vendor_name', 'invoice_number',
                     'payment_method', 'status']:
            if field in data:
                if field == 'expense_date':
                    setattr(expense, field, datetime.strptime(data[field], '%Y-%m-%d').date())
                else:
                    setattr(expense, field, data[field])
        
        expense.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث المصروف بنجاح',
            'expense': expense.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== فئات المصروفات =====

@finance_bp.route('/expense-categories', methods=['GET'])
@jwt_required()
def get_expense_categories():
    """الحصول على فئات المصروفات"""
    try:
        company_id = get_user_company()
        categories = ExpenseCategory.query.filter_by(company_id=company_id).all()
        
        return jsonify({
            'categories': [cat.to_dict() for cat in categories]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@finance_bp.route('/expense-categories', methods=['POST'])
@jwt_required()
def create_expense_category():
    """إنشاء فئة مصروف جديدة"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'اسم الفئة مطلوب'}), 400
        
        category = ExpenseCategory(
            company_id=company_id,
            name=data['name'],
            name_en=data.get('name_en'),
            description=data.get('description')
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء فئة المصروف بنجاح',
            'category': category.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== إدارة طلبات الصيانة =====

@finance_bp.route('/maintenance-requests', methods=['GET'])
@jwt_required()
def get_maintenance_requests():
    """الحصول على قائمة طلبات الصيانة"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        unit_id = request.args.get('unit_id', type=int)
        
        query = MaintenanceRequest.query.filter_by(company_id=company_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if priority:
            query = query.filter_by(priority=priority)
        
        if unit_id:
            query = query.filter_by(unit_id=unit_id)
        
        requests = query.order_by(MaintenanceRequest.reported_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # إضافة معلومات إضافية
        requests_data = []
        for req in requests.items:
            req_dict = req.to_dict()
            
            if req.unit:
                req_dict['unit'] = {
                    'unit_number': req.unit.unit_number,
                    'building_name': req.unit.building.name if req.unit.building else None
                }
            
            if req.tenant:
                req_dict['tenant'] = {
                    'name': f"{req.tenant.first_name} {req.tenant.last_name}",
                    'phone': req.tenant.phone
                }
            
            requests_data.append(req_dict)
        
        return jsonify({
            'maintenance_requests': requests_data,
            'total': requests.total,
            'pages': requests.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@finance_bp.route('/maintenance-requests', methods=['POST'])
@jwt_required()
def create_maintenance_request():
    """إنشاء طلب صيانة جديد"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('description'):
            return jsonify({'error': 'وصف المشكلة مطلوب'}), 400
        
        # إنشاء رقم طلب تلقائي
        request_count = MaintenanceRequest.query.filter_by(company_id=company_id).count()
        request_number = f"MNT-{datetime.now().year}-{request_count + 1:04d}"
        
        maintenance_request = MaintenanceRequest(
            company_id=company_id,
            request_number=request_number,
            unit_id=data.get('unit_id'),
            tenant_id=data.get('tenant_id'),
            category=data.get('category'),
            priority=data.get('priority', 'medium'),
            description=data['description'],
            status=data.get('status', 'open'),
            reported_date=datetime.strptime(data['reported_date'], '%Y-%m-%d').date() if data.get('reported_date') else date.today(),
            assigned_to=data.get('assigned_to'),
            scheduled_date=datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date() if data.get('scheduled_date') else None,
            estimated_cost=data.get('estimated_cost'),
            notes=data.get('notes')
        )
        
        db.session.add(maintenance_request)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء طلب الصيانة بنجاح',
            'maintenance_request': maintenance_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== التقارير المالية =====

@finance_bp.route('/reports/income-statement', methods=['GET'])
@jwt_required()
def get_income_statement():
    """تقرير قائمة الدخل"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            # افتراضي: الشهر الحالي
            today = date.today()
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # حساب الإيرادات
        revenue_query = db.session.query(func.sum(ContractPayment.paid_amount)).join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'paid',
                ContractPayment.payment_date >= start_date,
                ContractPayment.payment_date <= end_date
            )
        )
        total_revenue = revenue_query.scalar() or 0
        
        # حساب المصروفات
        expense_query = db.session.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.company_id == company_id,
                Expense.status == 'paid',
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date
            )
        )
        total_expenses = expense_query.scalar() or 0
        
        # حساب المصروفات حسب الفئة
        expenses_by_category = db.session.query(
            ExpenseCategory.name,
            func.sum(Expense.amount)
        ).join(Expense).filter(
            and_(
                Expense.company_id == company_id,
                Expense.status == 'paid',
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date
            )
        ).group_by(ExpenseCategory.name).all()
        
        net_income = total_revenue - total_expenses
        
        return jsonify({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'revenue': {
                'total': float(total_revenue)
            },
            'expenses': {
                'total': float(total_expenses),
                'by_category': [
                    {'category': cat, 'amount': float(amount)}
                    for cat, amount in expenses_by_category
                ]
            },
            'net_income': float(net_income)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@finance_bp.route('/reports/cash-flow', methods=['GET'])
@jwt_required()
def get_cash_flow():
    """تقرير التدفق النقدي"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        months = request.args.get('months', 6, type=int)
        
        # حساب التدفق النقدي للأشهر الماضية
        cash_flow_data = []
        
        for i in range(months):
            month_start = date.today().replace(day=1) - relativedelta(months=i)
            month_end = month_start + relativedelta(months=1) - relativedelta(days=1)
            
            # الإيرادات
            revenue = db.session.query(func.sum(ContractPayment.paid_amount)).join(Contract).filter(
                and_(
                    Contract.company_id == company_id,
                    ContractPayment.status == 'paid',
                    ContractPayment.payment_date >= month_start,
                    ContractPayment.payment_date <= month_end
                )
            ).scalar() or 0
            
            # المصروفات
            expenses = db.session.query(func.sum(Expense.amount)).filter(
                and_(
                    Expense.company_id == company_id,
                    Expense.status == 'paid',
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= month_end
                )
            ).scalar() or 0
            
            cash_flow_data.append({
                'month': month_start.strftime('%Y-%m'),
                'revenue': float(revenue),
                'expenses': float(expenses),
                'net_cash_flow': float(revenue - expenses)
            })
        
        # ترتيب البيانات من الأقدم للأحدث
        cash_flow_data.reverse()
        
        return jsonify({
            'cash_flow': cash_flow_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@finance_bp.route('/reports/receivables', methods=['GET'])
@jwt_required()
def get_receivables_report():
    """تقرير المبالغ المستحقة"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        # المبالغ المستحقة (غير مدفوعة)
        pending_payments = db.session.query(
            Contract.contract_number,
            func.concat(Person.first_name, ' ', Person.last_name).label('tenant_name'),
            func.sum(ContractPayment.amount).label('total_amount'),
            func.count(ContractPayment.id).label('payment_count')
        ).join(Contract).join(Person, Contract.tenant_id == Person.id).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending'
            )
        ).group_by(Contract.id, Person.id).all()
        
        # المبالغ المتأخرة
        overdue_payments = db.session.query(
            Contract.contract_number,
            func.concat(Person.first_name, ' ', Person.last_name).label('tenant_name'),
            func.sum(ContractPayment.amount).label('total_amount'),
            func.count(ContractPayment.id).label('payment_count')
        ).join(Contract).join(Person, Contract.tenant_id == Person.id).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending',
                ContractPayment.due_date < date.today()
            )
        ).group_by(Contract.id, Person.id).all()
        
        return jsonify({
            'pending_payments': [
                {
                    'contract_number': row.contract_number,
                    'tenant_name': row.tenant_name,
                    'total_amount': float(row.total_amount),
                    'payment_count': row.payment_count
                }
                for row in pending_payments
            ],
            'overdue_payments': [
                {
                    'contract_number': row.contract_number,
                    'tenant_name': row.tenant_name,
                    'total_amount': float(row.total_amount),
                    'payment_count': row.payment_count
                }
                for row in overdue_payments
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== إحصائيات مالية =====

@finance_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_finance_stats():
    """الحصول على الإحصائيات المالية"""
    try:
        company_id = get_user_company()
        
        # الشهر الحالي
        today = date.today()
        month_start = today.replace(day=1)
        
        # الإيرادات الشهرية
        monthly_revenue = db.session.query(func.sum(ContractPayment.paid_amount)).join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'paid',
                ContractPayment.payment_date >= month_start,
                ContractPayment.payment_date <= today
            )
        ).scalar() or 0
        
        # المصروفات الشهرية
        monthly_expenses = db.session.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.company_id == company_id,
                Expense.status == 'paid',
                Expense.expense_date >= month_start,
                Expense.expense_date <= today
            )
        ).scalar() or 0
        
        # المبالغ المعلقة
        pending_amount = db.session.query(func.sum(ContractPayment.amount)).join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending'
            )
        ).scalar() or 0
        
        # المبالغ المتأخرة
        overdue_amount = db.session.query(func.sum(ContractPayment.amount)).join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending',
                ContractPayment.due_date < today
            )
        ).scalar() or 0
        
        return jsonify({
            'monthly_revenue': float(monthly_revenue),
            'monthly_expenses': float(monthly_expenses),
            'net_income': float(monthly_revenue - monthly_expenses),
            'pending_amount': float(pending_amount),
            'overdue_amount': float(overdue_amount)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

