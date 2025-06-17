from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.property import db, User, Building, Unit
from src.models.contract import Contract, ContractPayment, Person
from src.models.finance import Expense, ExpenseCategory
from datetime import datetime, date
from sqlalchemy import and_, or_, func
from dateutil.relativedelta import relativedelta
import io
import base64
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

reports_bp = Blueprint('reports', __name__)

def get_user_company():
    """الحصول على شركة المستخدم الحالي"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.company_id if user else None

def setup_arabic_fonts():
    """إعداد الخطوط العربية"""
    try:
        # يمكن إضافة خط عربي هنا إذا كان متوفراً
        # pdfmetrics.registerFont(TTFont('Arabic', 'path/to/arabic/font.ttf'))
        pass
    except:
        pass

def create_arabic_styles():
    """إنشاء أنماط للنصوص العربية"""
    styles = getSampleStyleSheet()
    
    # نمط العنوان الرئيسي
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # نمط العنوان الفرعي
    heading_style = ParagraphStyle(
        'ArabicHeading',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=12,
        alignment=TA_RIGHT,
        fontName='Helvetica-Bold'
    )
    
    # نمط النص العادي
    normal_style = ParagraphStyle(
        'ArabicNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT,
        fontName='Helvetica'
    )
    
    return {
        'title': title_style,
        'heading': heading_style,
        'normal': normal_style
    }

@reports_bp.route('/contract-report/<int:contract_id>', methods=['GET'])
@jwt_required()
def generate_contract_report(contract_id):
    """تقرير تفصيلي للعقد"""
    try:
        company_id = get_user_company()
        contract = Contract.query.filter_by(id=contract_id, company_id=company_id).first()
        
        if not contract:
            return jsonify({'error': 'العقد غير موجود'}), 404
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        # إعداد الأنماط
        styles = create_arabic_styles()
        story = []
        
        # العنوان الرئيسي
        title = Paragraph("تقرير العقد", styles['title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # معلومات العقد الأساسية
        contract_info = [
            ['رقم العقد:', contract.contract_number],
            ['تاريخ البداية:', contract.start_date.strftime('%Y-%m-%d')],
            ['تاريخ النهاية:', contract.end_date.strftime('%Y-%m-%d')],
            ['قيمة الإيجار:', f"{contract.rent_amount:,.2f} ريال"],
            ['الحالة:', 'نشط' if contract.status == 'active' else 'غير نشط'],
        ]
        
        if contract.tenant:
            contract_info.extend([
                ['المستأجر:', f"{contract.tenant.first_name} {contract.tenant.last_name}"],
                ['هاتف المستأجر:', contract.tenant.phone or 'غير محدد'],
            ])
        
        if contract.unit:
            contract_info.extend([
                ['رقم الوحدة:', contract.unit.unit_number],
                ['المبنى:', contract.unit.building.name if contract.unit.building else 'غير محدد'],
            ])
        
        # جدول معلومات العقد
        contract_table = Table(contract_info, colWidths=[4*cm, 8*cm])
        contract_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(contract_table)
        story.append(Spacer(1, 20))
        
        # جدول الدفعات
        payments = ContractPayment.query.filter_by(contract_id=contract_id).order_by(ContractPayment.due_date).all()
        
        if payments:
            story.append(Paragraph("جدول الدفعات", styles['heading']))
            story.append(Spacer(1, 10))
            
            payment_data = [['رقم الدفعة', 'تاريخ الاستحقاق', 'المبلغ', 'تاريخ الدفع', 'الحالة']]
            
            for payment in payments:
                payment_data.append([
                    str(payment.payment_number),
                    payment.due_date.strftime('%Y-%m-%d'),
                    f"{payment.amount:,.2f}",
                    payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else 'لم يدفع',
                    'مدفوع' if payment.status == 'paid' else 'معلق'
                ])
            
            payment_table = Table(payment_data, colWidths=[2*cm, 3*cm, 3*cm, 3*cm, 2*cm])
            payment_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(payment_table)
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'contract_report_{contract.contract_number}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/financial-statement', methods=['GET'])
@jwt_required()
def generate_financial_statement():
    """تقرير القوائم المالية"""
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
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        styles = create_arabic_styles()
        story = []
        
        # العنوان الرئيسي
        title = Paragraph("قائمة الدخل", styles['title'])
        story.append(title)
        story.append(Spacer(1, 10))
        
        # فترة التقرير
        period = Paragraph(f"من {start_date} إلى {end_date}", styles['normal'])
        story.append(period)
        story.append(Spacer(1, 20))
        
        # الإيرادات
        story.append(Paragraph("الإيرادات", styles['heading']))
        revenue_data = [
            ['إيرادات الإيجارات', f"{total_revenue:,.2f} ريال"],
            ['إجمالي الإيرادات', f"{total_revenue:,.2f} ريال"]
        ]
        
        revenue_table = Table(revenue_data, colWidths=[6*cm, 4*cm])
        revenue_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(revenue_table)
        story.append(Spacer(1, 20))
        
        # المصروفات
        story.append(Paragraph("المصروفات", styles['heading']))
        
        expense_data = [['نوع المصروف', 'المبلغ']]
        for category, amount in expenses_by_category:
            expense_data.append([category or 'غير مصنف', f"{amount:,.2f} ريال"])
        
        expense_data.append(['إجمالي المصروفات', f"{total_expenses:,.2f} ريال"])
        
        expense_table = Table(expense_data, colWidths=[6*cm, 4*cm])
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightcoral),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(expense_table)
        story.append(Spacer(1, 20))
        
        # صافي الدخل
        net_income = total_revenue - total_expenses
        story.append(Paragraph("النتيجة النهائية", styles['heading']))
        
        result_data = [
            ['إجمالي الإيرادات', f"{total_revenue:,.2f} ريال"],
            ['إجمالي المصروفات', f"{total_expenses:,.2f} ريال"],
            ['صافي الدخل', f"{net_income:,.2f} ريال"]
        ]
        
        result_table = Table(result_data, colWidths=[6*cm, 4*cm])
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgreen),
            ('BACKGROUND', (0, -1), (-1, -1), colors.yellow if net_income >= 0 else colors.lightcoral),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(result_table)
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'financial_statement_{start_date}_{end_date}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/property-report', methods=['GET'])
@jwt_required()
def generate_property_report():
    """تقرير العقارات"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        building_id = request.args.get('building_id', type=int)
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        styles = create_arabic_styles()
        story = []
        
        # العنوان الرئيسي
        title = Paragraph("تقرير العقارات", styles['title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        if building_id:
            # تقرير مبنى محدد
            building = Building.query.filter_by(id=building_id, company_id=company_id).first()
            if not building:
                return jsonify({'error': 'المبنى غير موجود'}), 404
            
            story.append(Paragraph(f"تقرير المبنى: {building.name}", styles['heading']))
            story.append(Spacer(1, 10))
            
            # معلومات المبنى
            building_info = [
                ['اسم المبنى:', building.name],
                ['العنوان:', building.address or 'غير محدد'],
                ['عدد الطوابق:', str(building.total_floors or 0)],
                ['إجمالي الوحدات:', str(building.total_units or 0)],
            ]
            
            building_table = Table(building_info, colWidths=[4*cm, 8*cm])
            building_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(building_table)
            story.append(Spacer(1, 20))
            
            # قائمة الوحدات
            units = Unit.query.filter_by(building_id=building_id, is_active=True).all()
            
            if units:
                story.append(Paragraph("قائمة الوحدات", styles['heading']))
                story.append(Spacer(1, 10))
                
                unit_data = [['رقم الوحدة', 'الطابق', 'المساحة', 'الحالة', 'الإيجار الحالي']]
                
                for unit in units:
                    status_text = {
                        'available': 'متاحة',
                        'occupied': 'مؤجرة',
                        'maintenance': 'صيانة'
                    }.get(unit.status, unit.status)
                    
                    unit_data.append([
                        unit.unit_number,
                        str(unit.floor_number or ''),
                        f"{unit.area or 0} م²",
                        status_text,
                        f"{unit.current_rent or 0:,.0f} ريال"
                    ])
                
                unit_table = Table(unit_data, colWidths=[2.5*cm, 2*cm, 2.5*cm, 2.5*cm, 3*cm])
                unit_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(unit_table)
        
        else:
            # تقرير عام لجميع العقارات
            buildings = Building.query.filter_by(company_id=company_id, is_active=True).all()
            
            story.append(Paragraph("ملخص العقارات", styles['heading']))
            story.append(Spacer(1, 10))
            
            summary_data = [['المبنى', 'إجمالي الوحدات', 'الوحدات المؤجرة', 'الوحدات المتاحة', 'معدل الإشغال']]
            
            for building in buildings:
                total_units = Unit.query.filter_by(building_id=building.id, is_active=True).count()
                occupied_units = Unit.query.filter_by(building_id=building.id, status='occupied', is_active=True).count()
                available_units = Unit.query.filter_by(building_id=building.id, status='available', is_active=True).count()
                occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0
                
                summary_data.append([
                    building.name,
                    str(total_units),
                    str(occupied_units),
                    str(available_units),
                    f"{occupancy_rate:.1f}%"
                ])
            
            summary_table = Table(summary_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        filename = f'property_report_{building_id}.pdf' if building_id else 'properties_summary.pdf'
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/tenant-statement/<int:tenant_id>', methods=['GET'])
@jwt_required()
def generate_tenant_statement(tenant_id):
    """كشف حساب المستأجر"""
    try:
        company_id = get_user_company()
        tenant = Person.query.filter_by(id=tenant_id, company_id=company_id, person_type='tenant').first()
        
        if not tenant:
            return jsonify({'error': 'المستأجر غير موجود'}), 404
        
        # الحصول على عقود المستأجر
        contracts = Contract.query.filter_by(tenant_id=tenant_id, company_id=company_id).all()
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        styles = create_arabic_styles()
        story = []
        
        # العنوان الرئيسي
        title = Paragraph("كشف حساب المستأجر", styles['title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # معلومات المستأجر
        tenant_info = [
            ['اسم المستأجر:', f"{tenant.first_name} {tenant.last_name}"],
            ['رقم الهوية:', tenant.id_number or 'غير محدد'],
            ['الهاتف:', tenant.phone or 'غير محدد'],
            ['البريد الإلكتروني:', tenant.email or 'غير محدد'],
        ]
        
        tenant_table = Table(tenant_info, colWidths=[4*cm, 8*cm])
        tenant_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(tenant_table)
        story.append(Spacer(1, 20))
        
        # تفاصيل العقود والدفعات
        for contract in contracts:
            story.append(Paragraph(f"العقد رقم: {contract.contract_number}", styles['heading']))
            story.append(Spacer(1, 10))
            
            # معلومات العقد
            contract_info = [
                ['الوحدة:', contract.unit.unit_number if contract.unit else 'غير محدد'],
                ['المبنى:', contract.unit.building.name if contract.unit and contract.unit.building else 'غير محدد'],
                ['قيمة الإيجار:', f"{contract.rent_amount:,.2f} ريال"],
                ['فترة العقد:', f"من {contract.start_date} إلى {contract.end_date}"],
            ]
            
            contract_table = Table(contract_info, colWidths=[3*cm, 9*cm])
            contract_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(contract_table)
            story.append(Spacer(1, 10))
            
            # دفعات العقد
            payments = ContractPayment.query.filter_by(contract_id=contract.id).order_by(ContractPayment.due_date).all()
            
            if payments:
                payment_data = [['تاريخ الاستحقاق', 'المبلغ', 'تاريخ الدفع', 'الحالة']]
                
                total_due = 0
                total_paid = 0
                
                for payment in payments:
                    total_due += payment.amount
                    if payment.status == 'paid':
                        total_paid += payment.paid_amount or payment.amount
                    
                    payment_data.append([
                        payment.due_date.strftime('%Y-%m-%d'),
                        f"{payment.amount:,.2f}",
                        payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else 'لم يدفع',
                        'مدفوع' if payment.status == 'paid' else 'معلق'
                    ])
                
                # إضافة الإجماليات
                payment_data.append(['الإجمالي', f"{total_due:,.2f}", f"{total_paid:,.2f}", f"{total_due - total_paid:,.2f} متبقي"])
                
                payment_table = Table(payment_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm])
                payment_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.yellow),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(payment_table)
            
            story.append(Spacer(1, 20))
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'tenant_statement_{tenant.first_name}_{tenant.last_name}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/available-reports', methods=['GET'])
@jwt_required()
def get_available_reports():
    """الحصول على قائمة التقارير المتاحة"""
    try:
        reports = [
            {
                'id': 'financial_statement',
                'name': 'قائمة الدخل',
                'description': 'تقرير الإيرادات والمصروفات وصافي الدخل',
                'parameters': ['start_date', 'end_date']
            },
            {
                'id': 'property_report',
                'name': 'تقرير العقارات',
                'description': 'تقرير شامل عن العقارات والوحدات',
                'parameters': ['building_id']
            },
            {
                'id': 'contract_report',
                'name': 'تقرير العقد',
                'description': 'تقرير تفصيلي لعقد محدد',
                'parameters': ['contract_id']
            },
            {
                'id': 'tenant_statement',
                'name': 'كشف حساب المستأجر',
                'description': 'كشف حساب شامل للمستأجر',
                'parameters': ['tenant_id']
            }
        ]
        
        return jsonify({'reports': reports}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

