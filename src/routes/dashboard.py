from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.property import db, User, Building, Unit
from src.models.contract import Contract, ContractPayment, Person
from src.models.finance import Expense, MaintenanceRequest
from datetime import datetime, date
from sqlalchemy import and_, or_, func, extract
from dateutil.relativedelta import relativedelta

dashboard_bp = Blueprint('dashboard', __name__)

def get_user_company():
    """الحصول على شركة المستخدم الحالي"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.company_id if user else None

@dashboard_bp.route('/overview', methods=['GET'])
@jwt_required()
def get_dashboard_overview():
    """الحصول على نظرة عامة للوحة التحكم"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        today = date.today()
        month_start = today.replace(day=1)
        
        # إحصائيات العقارات
        total_buildings = Building.query.filter_by(company_id=company_id, is_active=True).count()
        total_units = Unit.query.filter_by(company_id=company_id, is_active=True).count()
        occupied_units = Unit.query.filter_by(company_id=company_id, status='occupied', is_active=True).count()
        available_units = Unit.query.filter_by(company_id=company_id, status='available', is_active=True).count()
        
        # معدل الإشغال
        occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0
        
        # إحصائيات العقود
        active_contracts = Contract.query.filter_by(company_id=company_id, status='active').count()
        expiring_contracts = Contract.query.filter(
            and_(
                Contract.company_id == company_id,
                Contract.status == 'active',
                Contract.end_date <= today + relativedelta(days=30)
            )
        ).count()
        
        # الإحصائيات المالية
        monthly_revenue = db.session.query(func.sum(ContractPayment.paid_amount)).join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'paid',
                ContractPayment.payment_date >= month_start,
                ContractPayment.payment_date <= today
            )
        ).scalar() or 0
        
        monthly_expenses = db.session.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.company_id == company_id,
                Expense.status == 'paid',
                Expense.expense_date >= month_start,
                Expense.expense_date <= today
            )
        ).scalar() or 0
        
        # المبالغ المتأخرة
        overdue_payments = ContractPayment.query.join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending',
                ContractPayment.due_date < today
            )
        ).count()
        
        overdue_amount = db.session.query(func.sum(ContractPayment.amount)).join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending',
                ContractPayment.due_date < today
            )
        ).scalar() or 0
        
        # طلبات الصيانة المفتوحة
        open_maintenance = MaintenanceRequest.query.filter_by(
            company_id=company_id, 
            status='open'
        ).count()
        
        return jsonify({
            'properties': {
                'total_buildings': total_buildings,
                'total_units': total_units,
                'occupied_units': occupied_units,
                'available_units': available_units,
                'occupancy_rate': round(occupancy_rate, 2)
            },
            'contracts': {
                'active_contracts': active_contracts,
                'expiring_contracts': expiring_contracts
            },
            'finance': {
                'monthly_revenue': float(monthly_revenue),
                'monthly_expenses': float(monthly_expenses),
                'net_income': float(monthly_revenue - monthly_expenses),
                'overdue_payments': overdue_payments,
                'overdue_amount': float(overdue_amount)
            },
            'maintenance': {
                'open_requests': open_maintenance
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/recent-activities', methods=['GET'])
@jwt_required()
def get_recent_activities():
    """الحصول على الأنشطة الحديثة"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        limit = request.args.get('limit', 10, type=int)
        
        activities = []
        
        # العقود الحديثة
        recent_contracts = Contract.query.filter_by(company_id=company_id).order_by(
            Contract.created_at.desc()
        ).limit(5).all()
        
        for contract in recent_contracts:
            activities.append({
                'type': 'contract_created',
                'title': f'عقد جديد: {contract.contract_number}',
                'description': f'تم إنشاء عقد جديد للوحدة {contract.unit.unit_number if contract.unit else "غير محدد"}',
                'date': contract.created_at.isoformat(),
                'link': f'/contracts/{contract.id}'
            })
        
        # الدفعات الحديثة
        recent_payments = ContractPayment.query.join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'paid'
            )
        ).order_by(ContractPayment.payment_date.desc()).limit(5).all()
        
        for payment in recent_payments:
            activities.append({
                'type': 'payment_received',
                'title': f'دفعة مستلمة: {payment.amount} ريال',
                'description': f'تم استلام دفعة للعقد {payment.contract.contract_number}',
                'date': payment.payment_date.isoformat(),
                'link': f'/contracts/{payment.contract_id}'
            })
        
        # طلبات الصيانة الحديثة
        recent_maintenance = MaintenanceRequest.query.filter_by(company_id=company_id).order_by(
            MaintenanceRequest.created_at.desc()
        ).limit(5).all()
        
        for request in recent_maintenance:
            activities.append({
                'type': 'maintenance_request',
                'title': f'طلب صيانة: {request.request_number}',
                'description': f'طلب صيانة جديد للوحدة {request.unit.unit_number if request.unit else "غير محدد"}',
                'date': request.created_at.isoformat(),
                'link': f'/maintenance/{request.id}'
            })
        
        # ترتيب الأنشطة حسب التاريخ
        activities.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            'activities': activities[:limit]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/charts/revenue', methods=['GET'])
@jwt_required()
def get_revenue_chart():
    """الحصول على بيانات مخطط الإيرادات"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        months = request.args.get('months', 6, type=int)
        
        revenue_data = []
        
        for i in range(months):
            month_start = date.today().replace(day=1) - relativedelta(months=i)
            month_end = month_start + relativedelta(months=1) - relativedelta(days=1)
            
            revenue = db.session.query(func.sum(ContractPayment.paid_amount)).join(Contract).filter(
                and_(
                    Contract.company_id == company_id,
                    ContractPayment.status == 'paid',
                    ContractPayment.payment_date >= month_start,
                    ContractPayment.payment_date <= month_end
                )
            ).scalar() or 0
            
            revenue_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'revenue': float(revenue)
            })
        
        # ترتيب البيانات من الأقدم للأحدث
        revenue_data.reverse()
        
        return jsonify({
            'revenue_data': revenue_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/charts/occupancy', methods=['GET'])
@jwt_required()
def get_occupancy_chart():
    """الحصول على بيانات مخطط الإشغال"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        # إحصائيات الإشغال حسب المبنى
        buildings_occupancy = db.session.query(
            Building.name,
            func.count(Unit.id).label('total_units'),
            func.sum(func.case([(Unit.status == 'occupied', 1)], else_=0)).label('occupied_units')
        ).join(Unit).filter(
            and_(
                Building.company_id == company_id,
                Building.is_active == True,
                Unit.is_active == True
            )
        ).group_by(Building.id).all()
        
        occupancy_data = []
        for building in buildings_occupancy:
            occupancy_rate = (building.occupied_units / building.total_units * 100) if building.total_units > 0 else 0
            occupancy_data.append({
                'building_name': building.name,
                'total_units': building.total_units,
                'occupied_units': building.occupied_units,
                'occupancy_rate': round(occupancy_rate, 2)
            })
        
        # إحصائيات عامة
        total_units = Unit.query.filter_by(company_id=company_id, is_active=True).count()
        occupied_units = Unit.query.filter_by(company_id=company_id, status='occupied', is_active=True).count()
        available_units = Unit.query.filter_by(company_id=company_id, status='available', is_active=True).count()
        maintenance_units = Unit.query.filter_by(company_id=company_id, status='maintenance', is_active=True).count()
        
        return jsonify({
            'buildings_occupancy': occupancy_data,
            'overall_stats': {
                'total_units': total_units,
                'occupied_units': occupied_units,
                'available_units': available_units,
                'maintenance_units': maintenance_units,
                'occupancy_rate': round((occupied_units / total_units * 100) if total_units > 0 else 0, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/upcoming-events', methods=['GET'])
@jwt_required()
def get_upcoming_events():
    """الحصول على الأحداث القادمة"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        today = date.today()
        next_month = today + relativedelta(days=30)
        
        events = []
        
        # العقود المنتهية قريباً
        expiring_contracts = Contract.query.filter(
            and_(
                Contract.company_id == company_id,
                Contract.status == 'active',
                Contract.end_date >= today,
                Contract.end_date <= next_month
            )
        ).order_by(Contract.end_date).all()
        
        for contract in expiring_contracts:
            events.append({
                'type': 'contract_expiry',
                'title': f'انتهاء عقد: {contract.contract_number}',
                'description': f'ينتهي العقد للوحدة {contract.unit.unit_number if contract.unit else "غير محدد"}',
                'date': contract.end_date.isoformat(),
                'priority': 'high' if contract.end_date <= today + relativedelta(days=7) else 'medium',
                'link': f'/contracts/{contract.id}'
            })
        
        # الدفعات المستحقة
        upcoming_payments = ContractPayment.query.join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending',
                ContractPayment.due_date >= today,
                ContractPayment.due_date <= next_month
            )
        ).order_by(ContractPayment.due_date).all()
        
        for payment in upcoming_payments:
            events.append({
                'type': 'payment_due',
                'title': f'دفعة مستحقة: {payment.amount} ريال',
                'description': f'دفعة مستحقة للعقد {payment.contract.contract_number}',
                'date': payment.due_date.isoformat(),
                'priority': 'high' if payment.due_date <= today + relativedelta(days=3) else 'medium',
                'link': f'/contracts/{payment.contract_id}'
            })
        
        # طلبات الصيانة المجدولة
        scheduled_maintenance = MaintenanceRequest.query.filter(
            and_(
                MaintenanceRequest.company_id == company_id,
                MaintenanceRequest.status.in_(['assigned', 'in_progress']),
                MaintenanceRequest.scheduled_date >= today,
                MaintenanceRequest.scheduled_date <= next_month
            )
        ).order_by(MaintenanceRequest.scheduled_date).all()
        
        for request in scheduled_maintenance:
            events.append({
                'type': 'maintenance_scheduled',
                'title': f'صيانة مجدولة: {request.request_number}',
                'description': f'صيانة مجدولة للوحدة {request.unit.unit_number if request.unit else "غير محدد"}',
                'date': request.scheduled_date.isoformat(),
                'priority': 'medium',
                'link': f'/maintenance/{request.id}'
            })
        
        # ترتيب الأحداث حسب التاريخ
        events.sort(key=lambda x: x['date'])
        
        return jsonify({
            'events': events
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    """الحصول على التنبيهات"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        today = date.today()
        alerts = []
        
        # الدفعات المتأخرة
        overdue_payments = ContractPayment.query.join(Contract).filter(
            and_(
                Contract.company_id == company_id,
                ContractPayment.status == 'pending',
                ContractPayment.due_date < today
            )
        ).count()
        
        if overdue_payments > 0:
            alerts.append({
                'type': 'warning',
                'title': 'دفعات متأخرة',
                'message': f'يوجد {overdue_payments} دفعة متأخرة',
                'action': 'عرض الدفعات المتأخرة',
                'link': '/payments?status=overdue'
            })
        
        # العقود المنتهية
        expired_contracts = Contract.query.filter(
            and_(
                Contract.company_id == company_id,
                Contract.status == 'active',
                Contract.end_date < today
            )
        ).count()
        
        if expired_contracts > 0:
            alerts.append({
                'type': 'error',
                'title': 'عقود منتهية',
                'message': f'يوجد {expired_contracts} عقد منتهي يحتاج تجديد أو إنهاء',
                'action': 'عرض العقود المنتهية',
                'link': '/contracts?status=expired'
            })
        
        # طلبات الصيانة العاجلة
        urgent_maintenance = MaintenanceRequest.query.filter(
            and_(
                MaintenanceRequest.company_id == company_id,
                MaintenanceRequest.priority == 'urgent',
                MaintenanceRequest.status.in_(['open', 'assigned'])
            )
        ).count()
        
        if urgent_maintenance > 0:
            alerts.append({
                'type': 'error',
                'title': 'صيانة عاجلة',
                'message': f'يوجد {urgent_maintenance} طلب صيانة عاجل',
                'action': 'عرض طلبات الصيانة العاجلة',
                'link': '/maintenance?priority=urgent'
            })
        
        # الوحدات الشاغرة لفترة طويلة
        long_vacant_units = Unit.query.filter(
            and_(
                Unit.company_id == company_id,
                Unit.status == 'available',
                Unit.updated_at < today - relativedelta(days=90)
            )
        ).count()
        
        if long_vacant_units > 0:
            alerts.append({
                'type': 'info',
                'title': 'وحدات شاغرة لفترة طويلة',
                'message': f'يوجد {long_vacant_units} وحدة شاغرة لأكثر من 90 يوم',
                'action': 'عرض الوحدات الشاغرة',
                'link': '/units?status=available&long_vacant=true'
            })
        
        return jsonify({
            'alerts': alerts
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

