from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.property import db, User
from src.models.contract import Person, Contract, ContractType, ContractPayment, Cheque
from datetime import datetime, date
from sqlalchemy import and_, or_, func
from dateutil.relativedelta import relativedelta

contract_bp = Blueprint('contract', __name__)

def get_user_company():
    """الحصول على شركة المستخدم الحالي"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.company_id if user else None

# ===== إدارة الأشخاص =====

@contract_bp.route('/persons', methods=['GET'])
@jwt_required()
def get_persons():
    """الحصول على قائمة الأشخاص"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        person_type = request.args.get('person_type')
        
        query = Person.query.filter_by(company_id=company_id, is_active=True)
        
        if search:
            query = query.filter(or_(
                Person.first_name.contains(search),
                Person.last_name.contains(search),
                Person.id_number.contains(search),
                Person.phone.contains(search),
                Person.email.contains(search)
            ))
        
        if person_type:
            query = query.filter_by(person_type=person_type)
        
        persons = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'persons': [person.to_dict() for person in persons.items],
            'total': persons.total,
            'pages': persons.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@contract_bp.route('/persons', methods=['POST'])
@jwt_required()
def create_person():
    """إنشاء شخص جديد"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('first_name') or not data.get('last_name'):
            return jsonify({'error': 'الاسم الأول والأخير مطلوبان'}), 400
        
        person = Person(
            company_id=company_id,
            person_type=data.get('person_type', 'tenant'),
            first_name=data['first_name'],
            last_name=data['last_name'],
            first_name_en=data.get('first_name_en'),
            last_name_en=data.get('last_name_en'),
            nationality=data.get('nationality'),
            id_number=data.get('id_number'),
            passport_number=data.get('passport_number'),
            visa_number=data.get('visa_number'),
            id_expiry_date=datetime.strptime(data['id_expiry_date'], '%Y-%m-%d').date() if data.get('id_expiry_date') else None,
            passport_expiry_date=datetime.strptime(data['passport_expiry_date'], '%Y-%m-%d').date() if data.get('passport_expiry_date') else None,
            visa_expiry_date=datetime.strptime(data['visa_expiry_date'], '%Y-%m-%d').date() if data.get('visa_expiry_date') else None,
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d').date() if data.get('birth_date') else None,
            gender=data.get('gender'),
            marital_status=data.get('marital_status'),
            email=data.get('email'),
            phone=data.get('phone'),
            mobile=data.get('mobile'),
            address=data.get('address'),
            address_en=data.get('address_en'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            notes=data.get('notes')
        )
        
        db.session.add(person)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء الشخص بنجاح',
            'person': person.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== إدارة العقود =====

@contract_bp.route('/', methods=['GET'])
@jwt_required()
def get_contracts():
    """الحصول على قائمة العقود"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status')
        building_id = request.args.get('building_id', type=int)
        
        query = Contract.query.filter_by(company_id=company_id)
        
        if search:
            query = query.filter(or_(
                Contract.contract_number.contains(search)
            ))
        
        if status:
            query = query.filter_by(status=status)
        
        if building_id:
            from src.models.property import Unit
            query = query.join(Unit).filter(Unit.building_id == building_id)
        
        contracts = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # إضافة معلومات إضافية لكل عقد
        contracts_data = []
        for contract in contracts.items:
            contract_dict = contract.to_dict()
            
            # إضافة معلومات المستأجر
            if contract.tenant:
                contract_dict['tenant'] = {
                    'id': contract.tenant.id,
                    'name': f"{contract.tenant.first_name} {contract.tenant.last_name}",
                    'phone': contract.tenant.phone,
                    'email': contract.tenant.email
                }
            
            # إضافة معلومات المالك
            if contract.landlord:
                contract_dict['landlord'] = {
                    'id': contract.landlord.id,
                    'name': f"{contract.landlord.first_name} {contract.landlord.last_name}",
                    'phone': contract.landlord.phone
                }
            
            # إضافة معلومات الوحدة
            if contract.unit:
                contract_dict['unit'] = {
                    'id': contract.unit.id,
                    'unit_number': contract.unit.unit_number,
                    'building_name': contract.unit.building.name if contract.unit.building else None
                }
            
            # حساب الدفعات المتأخرة
            overdue_payments = ContractPayment.query.filter(
                and_(
                    ContractPayment.contract_id == contract.id,
                    ContractPayment.status == 'pending',
                    ContractPayment.due_date < date.today()
                )
            ).count()
            
            contract_dict['overdue_payments'] = overdue_payments
            
            contracts_data.append(contract_dict)
        
        return jsonify({
            'contracts': contracts_data,
            'total': contracts.total,
            'pages': contracts.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@contract_bp.route('/', methods=['POST'])
@jwt_required()
def create_contract():
    """إنشاء عقد جديد"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        # التحقق من البيانات المطلوبة
        required_fields = ['unit_id', 'tenant_id', 'start_date', 'end_date', 'rent_amount']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} مطلوب'}), 400
        
        # إنشاء رقم عقد تلقائي
        contract_count = Contract.query.filter_by(company_id=company_id).count()
        contract_number = f"CNT-{datetime.now().year}-{contract_count + 1:04d}"
        
        contract = Contract(
            company_id=company_id,
            contract_number=contract_number,
            contract_type_id=data.get('contract_type_id'),
            unit_id=data['unit_id'],
            tenant_id=data['tenant_id'],
            landlord_id=data.get('landlord_id'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
            rent_amount=data['rent_amount'],
            security_deposit=data.get('security_deposit'),
            commission_amount=data.get('commission_amount'),
            commission_percentage=data.get('commission_percentage'),
            payment_frequency=data.get('payment_frequency', 'monthly'),
            payment_method=data.get('payment_method'),
            auto_renewal=data.get('auto_renewal', False),
            renewal_notice_days=data.get('renewal_notice_days', 30),
            terms_and_conditions=data.get('terms_and_conditions'),
            notes=data.get('notes'),
            created_by=get_jwt_identity()
        )
        
        db.session.add(contract)
        db.session.flush()  # للحصول على ID العقد
        
        # إنشاء جدولة الدفعات
        create_contract_payments(contract, data['payment_frequency'])
        
        # تحديث حالة الوحدة
        from src.models.property import Unit
        unit = Unit.query.get(data['unit_id'])
        if unit:
            unit.status = 'occupied'
            unit.current_rent = data['rent_amount']
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء العقد بنجاح',
            'contract': contract.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def create_contract_payments(contract, frequency):
    """إنشاء جدولة الدفعات للعقد"""
    start_date = contract.start_date
    end_date = contract.end_date
    rent_amount = contract.rent_amount
    
    # تحديد فترة الدفع
    if frequency == 'monthly':
        delta = relativedelta(months=1)
        payment_amount = rent_amount
    elif frequency == 'quarterly':
        delta = relativedelta(months=3)
        payment_amount = rent_amount * 3
    elif frequency == 'semi_annual':
        delta = relativedelta(months=6)
        payment_amount = rent_amount * 6
    elif frequency == 'annual':
        delta = relativedelta(years=1)
        payment_amount = rent_amount * 12
    else:
        delta = relativedelta(months=1)
        payment_amount = rent_amount
    
    current_date = start_date
    payment_number = 1
    
    while current_date <= end_date:
        # تعديل المبلغ للدفعة الأخيرة إذا لزم الأمر
        next_date = current_date + delta
        if next_date > end_date:
            # حساب المبلغ المتناسب للفترة المتبقية
            if frequency == 'monthly':
                remaining_days = (end_date - current_date).days + 1
                days_in_month = 30  # متوسط أيام الشهر
                payment_amount = rent_amount * (remaining_days / days_in_month)
        
        payment = ContractPayment(
            contract_id=contract.id,
            payment_number=payment_number,
            due_date=current_date,
            amount=payment_amount
        )
        
        db.session.add(payment)
        
        current_date = next_date
        payment_number += 1

@contract_bp.route('/<int:contract_id>', methods=['GET'])
@jwt_required()
def get_contract(contract_id):
    """الحصول على تفاصيل عقد"""
    try:
        company_id = get_user_company()
        contract = Contract.query.filter_by(id=contract_id, company_id=company_id).first()
        
        if not contract:
            return jsonify({'error': 'العقد غير موجود'}), 404
        
        contract_dict = contract.to_dict()
        
        # إضافة معلومات تفصيلية
        if contract.tenant:
            contract_dict['tenant'] = contract.tenant.to_dict()
        
        if contract.landlord:
            contract_dict['landlord'] = contract.landlord.to_dict()
        
        if contract.unit:
            contract_dict['unit'] = contract.unit.to_dict()
            if contract.unit.building:
                contract_dict['unit']['building'] = contract.unit.building.to_dict()
        
        # إضافة الدفعات
        payments = ContractPayment.query.filter_by(contract_id=contract_id).order_by(ContractPayment.due_date).all()
        contract_dict['payments'] = [payment.to_dict() for payment in payments]
        
        # إضافة الشيكات
        cheques = Cheque.query.filter_by(contract_id=contract_id).order_by(Cheque.due_date).all()
        contract_dict['cheques'] = [cheque.to_dict() for cheque in cheques]
        
        return jsonify({'contract': contract_dict}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== إدارة الدفعات =====

@contract_bp.route('/payments', methods=['GET'])
@jwt_required()
def get_payments():
    """الحصول على قائمة الدفعات"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        overdue_only = request.args.get('overdue_only', 'false').lower() == 'true'
        
        query = ContractPayment.query.join(Contract).filter(Contract.company_id == company_id)
        
        if status:
            query = query.filter(ContractPayment.status == status)
        
        if overdue_only:
            query = query.filter(
                and_(
                    ContractPayment.status == 'pending',
                    ContractPayment.due_date < date.today()
                )
            )
        
        payments = query.order_by(ContractPayment.due_date).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # إضافة معلومات إضافية
        payments_data = []
        for payment in payments.items:
            payment_dict = payment.to_dict()
            
            if payment.contract:
                payment_dict['contract'] = {
                    'contract_number': payment.contract.contract_number,
                    'tenant_name': f"{payment.contract.tenant.first_name} {payment.contract.tenant.last_name}" if payment.contract.tenant else None,
                    'unit_number': payment.contract.unit.unit_number if payment.contract.unit else None
                }
            
            payments_data.append(payment_dict)
        
        return jsonify({
            'payments': payments_data,
            'total': payments.total,
            'pages': payments.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@contract_bp.route('/payments/<int:payment_id>/pay', methods=['POST'])
@jwt_required()
def mark_payment_paid(payment_id):
    """تسجيل دفعة كمدفوعة"""
    try:
        company_id = get_user_company()
        payment = ContractPayment.query.join(Contract).filter(
            and_(
                ContractPayment.id == payment_id,
                Contract.company_id == company_id
            )
        ).first()
        
        if not payment:
            return jsonify({'error': 'الدفعة غير موجودة'}), 404
        
        data = request.get_json()
        
        payment.paid_amount = data.get('paid_amount', payment.amount)
        payment.payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date() if data.get('payment_date') else date.today()
        payment.payment_method = data.get('payment_method')
        payment.status = 'paid'
        payment.notes = data.get('notes')
        payment.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم تسجيل الدفعة بنجاح',
            'payment': payment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== إدارة الشيكات =====

@contract_bp.route('/cheques', methods=['GET'])
@jwt_required()
def get_cheques():
    """الحصول على قائمة الشيكات"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        due_soon = request.args.get('due_soon', 'false').lower() == 'true'
        
        query = Cheque.query.filter_by(company_id=company_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if due_soon:
            # الشيكات المستحقة خلال 30 يوم
            due_date_limit = date.today() + relativedelta(days=30)
            query = query.filter(
                and_(
                    Cheque.due_date <= due_date_limit,
                    Cheque.status.in_(['received', 'deposited'])
                )
            )
        
        cheques = query.order_by(Cheque.due_date).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'cheques': [cheque.to_dict() for cheque in cheques.items],
            'total': cheques.total,
            'pages': cheques.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@contract_bp.route('/cheques', methods=['POST'])
@jwt_required()
def create_cheque():
    """إنشاء شيك جديد"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('cheque_number') or not data.get('amount') or not data.get('due_date'):
            return jsonify({'error': 'رقم الشيك والمبلغ وتاريخ الاستحقاق مطلوبة'}), 400
        
        cheque = Cheque(
            company_id=company_id,
            contract_id=data.get('contract_id'),
            payment_id=data.get('payment_id'),
            cheque_number=data['cheque_number'],
            bank_name=data.get('bank_name'),
            account_number=data.get('account_number'),
            amount=data['amount'],
            issue_date=datetime.strptime(data['issue_date'], '%Y-%m-%d').date() if data.get('issue_date') else None,
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date(),
            received_date=datetime.strptime(data['received_date'], '%Y-%m-%d').date() if data.get('received_date') else date.today(),
            status=data.get('status', 'received'),
            notes=data.get('notes')
        )
        
        db.session.add(cheque)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء الشيك بنجاح',
            'cheque': cheque.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== إحصائيات العقود =====

@contract_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_contract_stats():
    """الحصول على إحصائيات العقود"""
    try:
        company_id = get_user_company()
        
        # إحصائيات العقود
        total_contracts = Contract.query.filter_by(company_id=company_id).count()
        active_contracts = Contract.query.filter_by(company_id=company_id, status='active').count()
        expiring_contracts = Contract.query.filter(
            and_(
                Contract.company_id == company_id,
                Contract.status == 'active',
                Contract.end_date <= date.today() + relativedelta(days=30)
            )
        ).count()
        
        # إحصائيات الدفعات
        overdue_payments = ContractPayment.query.join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending',
                ContractPayment.due_date < date.today()
            )
        ).count()
        
        # إجمالي الإيرادات الشهرية
        monthly_revenue = db.session.query(func.sum(Contract.rent_amount)).filter(
            and_(
                Contract.company_id == company_id,
                Contract.status == 'active'
            )
        ).scalar() or 0
        
        return jsonify({
            'contracts': {
                'total': total_contracts,
                'active': active_contracts,
                'expiring_soon': expiring_contracts
            },
            'payments': {
                'overdue': overdue_payments
            },
            'revenue': {
                'monthly': float(monthly_revenue)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

