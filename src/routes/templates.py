from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.property import db, User, Company
from src.models.contract import Contract, ContractPayment, Person
from datetime import datetime, date
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

templates_bp = Blueprint('templates', __name__)

def get_user_company():
    """الحصول على شركة المستخدم الحالي"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.company if user else None

def create_arabic_styles():
    """إنشاء أنماط للنصوص العربية"""
    styles = getSampleStyleSheet()
    
    # نمط العنوان الرئيسي
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # نمط العنوان الفرعي
    heading_style = ParagraphStyle(
        'ArabicHeading',
        parent=styles['Heading1'],
        fontSize=12,
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

@templates_bp.route('/receipt/<int:payment_id>', methods=['GET'])
@jwt_required()
def generate_receipt(payment_id):
    """إنشاء سند قبض"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        payment = ContractPayment.query.filter_by(id=payment_id).first()
        if not payment or payment.contract.company_id != company.id:
            return jsonify({'error': 'الدفعة غير موجودة'}), 404
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        styles = create_arabic_styles()
        story = []
        
        # رأس الشركة
        company_header = [
            [company.name, 'سند قبض'],
            [company.address or '', f'رقم السند: {payment.id}'],
            [company.phone or '', f'التاريخ: {payment.payment_date.strftime("%Y-%m-%d") if payment.payment_date else date.today().strftime("%Y-%m-%d")}']
        ]
        
        header_table = Table(company_header, colWidths=[8*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 30))
        
        # معلومات الدفعة
        payment_info = [
            ['استلمنا من السيد/ة:', f"{payment.contract.tenant.first_name} {payment.contract.tenant.last_name}" if payment.contract.tenant else ''],
            ['مبلغ وقدره:', f"{payment.paid_amount or payment.amount:,.2f} ريال سعودي"],
            ['وذلك عن:', f"إيجار الوحدة رقم {payment.contract.unit.unit_number}" if payment.contract.unit else 'إيجار'],
            ['للفترة من:', f"{payment.due_date.strftime('%Y-%m-%d')} إلى {(payment.due_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1) if payment.due_date else ''}"],
            ['طريقة الدفع:', 'نقداً' if payment.payment_method == 'cash' else 'شيك' if payment.payment_method == 'cheque' else 'تحويل بنكي'],
        ]
        
        if payment.payment_method == 'cheque' and payment.cheque_number:
            payment_info.append(['رقم الشيك:', payment.cheque_number])
        
        payment_table = Table(payment_info, colWidths=[4*cm, 10*cm])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(payment_table)
        story.append(Spacer(1, 40))
        
        # التوقيعات
        signature_data = [
            ['توقيع المستلم', '', 'توقيع المسلم'],
            ['', '', ''],
            ['', '', '']
        ]
        
        signature_table = Table(signature_data, colWidths=[5*cm, 4*cm, 5*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('LINEBELOW', (0, 1), (0, 1), 1, colors.black),
            ('LINEBELOW', (2, 1), (2, 1), 1, colors.black),
        ]))
        
        story.append(signature_table)
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'receipt_{payment.id}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@templates_bp.route('/payment-voucher', methods=['POST'])
@jwt_required()
def generate_payment_voucher():
    """إنشاء سند صرف"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        styles = create_arabic_styles()
        story = []
        
        # رأس الشركة
        company_header = [
            [company.name, 'سند صرف'],
            [company.address or '', f'رقم السند: {data.get("voucher_number", "")}'],
            [company.phone or '', f'التاريخ: {data.get("date", date.today().strftime("%Y-%m-%d"))}']
        ]
        
        header_table = Table(company_header, colWidths=[8*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 30))
        
        # معلومات الصرف
        payment_info = [
            ['دفع إلى:', data.get('payee_name', '')],
            ['مبلغ وقدره:', f"{float(data.get('amount', 0)):,.2f} ريال سعودي"],
            ['وذلك عن:', data.get('description', '')],
            ['طريقة الدفع:', data.get('payment_method', 'نقداً')],
        ]
        
        if data.get('cheque_number'):
            payment_info.append(['رقم الشيك:', data.get('cheque_number')])
        
        payment_table = Table(payment_info, colWidths=[4*cm, 10*cm])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(payment_table)
        story.append(Spacer(1, 40))
        
        # التوقيعات
        signature_data = [
            ['توقيع المستلم', '', 'توقيع المسؤول'],
            ['', '', ''],
            ['', '', '']
        ]
        
        signature_table = Table(signature_data, colWidths=[5*cm, 4*cm, 5*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('LINEBELOW', (0, 1), (0, 1), 1, colors.black),
            ('LINEBELOW', (2, 1), (2, 1), 1, colors.black),
        ]))
        
        story.append(signature_table)
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'payment_voucher_{data.get("voucher_number", "")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@templates_bp.route('/contract/<int:contract_id>', methods=['GET'])
@jwt_required()
def generate_contract(contract_id):
    """إنشاء عقد إيجار"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        contract = Contract.query.filter_by(id=contract_id, company_id=company.id).first()
        if not contract:
            return jsonify({'error': 'العقد غير موجود'}), 404
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        styles = create_arabic_styles()
        story = []
        
        # العنوان الرئيسي
        title = Paragraph("عقد إيجار", styles['title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # معلومات الأطراف
        parties_text = f"""
        إنه في يوم {contract.start_date.strftime('%Y/%m/%d')} تم الاتفاق بين كل من:
        
        <b>الطرف الأول (المؤجر):</b> {company.name}
        العنوان: {company.address or ''}
        الهاتف: {company.phone or ''}
        
        <b>الطرف الثاني (المستأجر):</b> {contract.tenant.first_name} {contract.tenant.last_name if contract.tenant else ''}
        رقم الهوية: {contract.tenant.id_number if contract.tenant else ''}
        الهاتف: {contract.tenant.phone if contract.tenant else ''}
        """
        
        parties_para = Paragraph(parties_text, styles['normal'])
        story.append(parties_para)
        story.append(Spacer(1, 20))
        
        # تفاصيل العقد
        contract_details = f"""
        <b>تفاصيل العقد:</b>
        
        • رقم العقد: {contract.contract_number}
        • العقار المؤجر: الوحدة رقم {contract.unit.unit_number if contract.unit else ''} - {contract.unit.building.name if contract.unit and contract.unit.building else ''}
        • مدة الإيجار: من {contract.start_date.strftime('%Y/%m/%d')} إلى {contract.end_date.strftime('%Y/%m/%d')}
        • قيمة الإيجار السنوية: {contract.rent_amount:,.2f} ريال سعودي
        • طريقة الدفع: {contract.payment_frequency or 'شهرياً'}
        
        <b>الشروط والأحكام:</b>
        
        1. يلتزم المستأجر بدفع الإيجار في المواعيد المحددة
        2. يلتزم المستأجر بالمحافظة على العقار وعدم إحداث أي تغييرات بدون موافقة المؤجر
        3. يحق للمؤجر فسخ العقد في حالة عدم الالتزام بالشروط
        4. يتم تجديد العقد بموافقة الطرفين
        
        وقد تم توقيع هذا العقد من الطرفين في التاريخ المذكور أعلاه.
        """
        
        details_para = Paragraph(contract_details, styles['normal'])
        story.append(details_para)
        story.append(Spacer(1, 40))
        
        # التوقيعات
        signature_data = [
            ['توقيع المؤجر', '', 'توقيع المستأجر'],
            ['', '', ''],
            [company.name, '', f"{contract.tenant.first_name} {contract.tenant.last_name}" if contract.tenant else '']
        ]
        
        signature_table = Table(signature_data, colWidths=[6*cm, 4*cm, 6*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('LINEBELOW', (0, 1), (0, 1), 1, colors.black),
            ('LINEBELOW', (2, 1), (2, 1), 1, colors.black),
        ]))
        
        story.append(signature_table)
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'contract_{contract.contract_number}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@templates_bp.route('/invoice', methods=['POST'])
@jwt_required()
def generate_invoice():
    """إنشاء فاتورة"""
    try:
        company = get_user_company()
        if not company:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        # إنشاء ملف PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        styles = create_arabic_styles()
        story = []
        
        # رأس الفاتورة
        invoice_header = [
            [company.name, 'فاتورة'],
            [company.address or '', f'رقم الفاتورة: {data.get("invoice_number", "")}'],
            [f'الرقم الضريبي: {company.tax_number or ""}', f'التاريخ: {data.get("date", date.today().strftime("%Y-%m-%d"))}']
        ]
        
        header_table = Table(invoice_header, colWidths=[8*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        # معلومات العميل
        customer_info = [
            ['فاتورة إلى:', data.get('customer_name', '')],
            ['العنوان:', data.get('customer_address', '')],
            ['الرقم الضريبي:', data.get('customer_tax_number', '')],
        ]
        
        customer_table = Table(customer_info, colWidths=[3*cm, 11*cm])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(customer_table)
        story.append(Spacer(1, 20))
        
        # بنود الفاتورة
        items = data.get('items', [])
        invoice_data = [['الوصف', 'الكمية', 'السعر', 'المجموع']]
        
        total_amount = 0
        for item in items:
            quantity = float(item.get('quantity', 1))
            price = float(item.get('price', 0))
            total = quantity * price
            total_amount += total
            
            invoice_data.append([
                item.get('description', ''),
                str(quantity),
                f"{price:,.2f}",
                f"{total:,.2f}"
            ])
        
        # إضافة الضريبة إذا كانت موجودة
        tax_rate = float(data.get('tax_rate', 0))
        tax_amount = total_amount * (tax_rate / 100)
        
        if tax_rate > 0:
            invoice_data.append(['', '', f'الضريبة ({tax_rate}%)', f"{tax_amount:,.2f}"])
        
        invoice_data.append(['', '', 'الإجمالي', f"{total_amount + tax_amount:,.2f} ريال"])
        
        invoice_table = Table(invoice_data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm])
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(invoice_table)
        story.append(Spacer(1, 30))
        
        # ملاحظات
        if data.get('notes'):
            notes_para = Paragraph(f"<b>ملاحظات:</b><br/>{data.get('notes')}", styles['normal'])
            story.append(notes_para)
        
        # بناء PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'invoice_{data.get("invoice_number", "")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

