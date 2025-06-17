from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.property import db, User, Company, Project, Building, Unit, PropertyType, PropertyCategory
from datetime import datetime
from sqlalchemy import and_, or_

property_bp = Blueprint('property', __name__)

def get_user_company():
    """الحصول على شركة المستخدم الحالي"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.company_id if user else None

# ===== إدارة المشاريع =====

@property_bp.route('/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """الحصول على قائمة المشاريع"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        query = Project.query.filter_by(company_id=company_id, is_active=True)
        
        if search:
            query = query.filter(or_(
                Project.name.contains(search),
                Project.name_en.contains(search),
                Project.location.contains(search)
            ))
        
        projects = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'projects': [project.to_dict() for project in projects.items],
            'total': projects.total,
            'pages': projects.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@property_bp.route('/projects', methods=['POST'])
@jwt_required()
def create_project():
    """إنشاء مشروع جديد"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'اسم المشروع مطلوب'}), 400
        
        project = Project(
            company_id=company_id,
            name=data['name'],
            name_en=data.get('name_en'),
            description=data.get('description'),
            description_en=data.get('description_en'),
            location=data.get('location'),
            location_en=data.get('location_en'),
            developer_name=data.get('developer_name'),
            total_units=data.get('total_units'),
            completion_date=datetime.strptime(data['completion_date'], '%Y-%m-%d').date() if data.get('completion_date') else None
        )
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء المشروع بنجاح',
            'project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== إدارة المباني =====

@property_bp.route('/buildings', methods=['GET'])
@jwt_required()
def get_buildings():
    """الحصول على قائمة المباني"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        project_id = request.args.get('project_id', type=int)
        
        query = Building.query.filter_by(company_id=company_id, is_active=True)
        
        if search:
            query = query.filter(or_(
                Building.name.contains(search),
                Building.name_en.contains(search),
                Building.address.contains(search)
            ))
        
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        buildings = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # إضافة معلومات إضافية لكل مبنى
        buildings_data = []
        for building in buildings.items:
            building_dict = building.to_dict()
            
            # إحصائيات الوحدات
            total_units = Unit.query.filter_by(building_id=building.id, is_active=True).count()
            occupied_units = Unit.query.filter_by(building_id=building.id, status='occupied', is_active=True).count()
            available_units = Unit.query.filter_by(building_id=building.id, status='available', is_active=True).count()
            
            building_dict.update({
                'total_units': total_units,
                'occupied_units': occupied_units,
                'available_units': available_units,
                'occupancy_rate': (occupied_units / total_units * 100) if total_units > 0 else 0
            })
            
            buildings_data.append(building_dict)
        
        return jsonify({
            'buildings': buildings_data,
            'total': buildings.total,
            'pages': buildings.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@property_bp.route('/buildings', methods=['POST'])
@jwt_required()
def create_building():
    """إنشاء مبنى جديد"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'اسم المبنى مطلوب'}), 400
        
        building = Building(
            company_id=company_id,
            project_id=data.get('project_id'),
            name=data['name'],
            name_en=data.get('name_en'),
            address=data.get('address'),
            address_en=data.get('address_en'),
            total_floors=data.get('total_floors'),
            total_units=data.get('total_units'),
            building_type_id=data.get('building_type_id'),
            electricity_account=data.get('electricity_account'),
            water_account=data.get('water_account'),
            municipality_account=data.get('municipality_account')
        )
        
        db.session.add(building)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء المبنى بنجاح',
            'building': building.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@property_bp.route('/buildings/<int:building_id>', methods=['GET'])
@jwt_required()
def get_building(building_id):
    """الحصول على تفاصيل مبنى"""
    try:
        company_id = get_user_company()
        building = Building.query.filter_by(id=building_id, company_id=company_id).first()
        
        if not building:
            return jsonify({'error': 'المبنى غير موجود'}), 404
        
        building_dict = building.to_dict()
        
        # إضافة الوحدات
        units = Unit.query.filter_by(building_id=building_id, is_active=True).all()
        building_dict['units'] = [unit.to_dict() for unit in units]
        
        return jsonify({'building': building_dict}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== إدارة الوحدات =====

@property_bp.route('/units', methods=['GET'])
@jwt_required()
def get_units():
    """الحصول على قائمة الوحدات"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        building_id = request.args.get('building_id', type=int)
        status = request.args.get('status')
        unit_type_id = request.args.get('unit_type_id', type=int)
        
        query = Unit.query.filter_by(company_id=company_id, is_active=True)
        
        if search:
            query = query.filter(or_(
                Unit.unit_number.contains(search),
                Unit.description.contains(search)
            ))
        
        if building_id:
            query = query.filter_by(building_id=building_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if unit_type_id:
            query = query.filter_by(unit_type_id=unit_type_id)
        
        units = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # إضافة معلومات إضافية لكل وحدة
        units_data = []
        for unit in units.items:
            unit_dict = unit.to_dict()
            
            # إضافة معلومات المبنى
            if unit.building:
                unit_dict['building'] = {
                    'id': unit.building.id,
                    'name': unit.building.name,
                    'address': unit.building.address
                }
            
            # إضافة معلومات نوع الوحدة
            if unit.unit_type:
                unit_dict['unit_type'] = unit.unit_type.to_dict()
            
            # إضافة معلومات الفئة
            if unit.category:
                unit_dict['category'] = unit.category.to_dict()
            
            units_data.append(unit_dict)
        
        return jsonify({
            'units': units_data,
            'total': units.total,
            'pages': units.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@property_bp.route('/units', methods=['POST'])
@jwt_required()
def create_unit():
    """إنشاء وحدة جديدة"""
    try:
        company_id = get_user_company()
        if not company_id:
            return jsonify({'error': 'غير مصرح'}), 403
        
        data = request.get_json()
        
        if not data.get('building_id') or not data.get('unit_number'):
            return jsonify({'error': 'رقم المبنى ورقم الوحدة مطلوبان'}), 400
        
        # التحقق من عدم تكرار رقم الوحدة في نفس المبنى
        existing_unit = Unit.query.filter_by(
            building_id=data['building_id'],
            unit_number=data['unit_number'],
            is_active=True
        ).first()
        
        if existing_unit:
            return jsonify({'error': 'رقم الوحدة موجود بالفعل في هذا المبنى'}), 400
        
        unit = Unit(
            company_id=company_id,
            building_id=data['building_id'],
            unit_number=data['unit_number'],
            floor_number=data.get('floor_number'),
            unit_type_id=data.get('unit_type_id'),
            category_id=data.get('category_id'),
            area=data.get('area'),
            bedrooms=data.get('bedrooms'),
            bathrooms=data.get('bathrooms'),
            balconies=data.get('balconies'),
            parking_spaces=data.get('parking_spaces'),
            furnished=data.get('furnished', False),
            view_type=data.get('view_type'),
            ownership_type=data.get('ownership_type'),
            purchase_price=data.get('purchase_price'),
            current_rent=data.get('current_rent'),
            status=data.get('status', 'available'),
            description=data.get('description'),
            description_en=data.get('description_en')
        )
        
        db.session.add(unit)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء الوحدة بنجاح',
            'unit': unit.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@property_bp.route('/units/<int:unit_id>', methods=['PUT'])
@jwt_required()
def update_unit(unit_id):
    """تحديث وحدة"""
    try:
        company_id = get_user_company()
        unit = Unit.query.filter_by(id=unit_id, company_id=company_id).first()
        
        if not unit:
            return jsonify({'error': 'الوحدة غير موجودة'}), 404
        
        data = request.get_json()
        
        # تحديث البيانات
        for field in ['unit_number', 'floor_number', 'unit_type_id', 'category_id', 
                     'area', 'bedrooms', 'bathrooms', 'balconies', 'parking_spaces',
                     'furnished', 'view_type', 'ownership_type', 'purchase_price',
                     'current_rent', 'status', 'description', 'description_en']:
            if field in data:
                setattr(unit, field, data[field])
        
        unit.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث الوحدة بنجاح',
            'unit': unit.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== أنواع وفئات العقارات =====

@property_bp.route('/property-types', methods=['GET'])
@jwt_required()
def get_property_types():
    """الحصول على أنواع العقارات"""
    try:
        company_id = get_user_company()
        property_types = PropertyType.query.filter_by(company_id=company_id).all()
        
        return jsonify({
            'property_types': [pt.to_dict() for pt in property_types]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@property_bp.route('/property-categories', methods=['GET'])
@jwt_required()
def get_property_categories():
    """الحصول على فئات العقارات"""
    try:
        company_id = get_user_company()
        categories = PropertyCategory.query.filter_by(company_id=company_id).all()
        
        return jsonify({
            'categories': [cat.to_dict() for cat in categories]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== إحصائيات العقارات =====

@property_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_property_stats():
    """الحصول على إحصائيات العقارات"""
    try:
        company_id = get_user_company()
        
        # إحصائيات المباني
        total_buildings = Building.query.filter_by(company_id=company_id, is_active=True).count()
        
        # إحصائيات الوحدات
        total_units = Unit.query.filter_by(company_id=company_id, is_active=True).count()
        occupied_units = Unit.query.filter_by(company_id=company_id, status='occupied', is_active=True).count()
        available_units = Unit.query.filter_by(company_id=company_id, status='available', is_active=True).count()
        maintenance_units = Unit.query.filter_by(company_id=company_id, status='maintenance', is_active=True).count()
        
        # معدل الإشغال
        occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0
        
        return jsonify({
            'buildings': {
                'total': total_buildings
            },
            'units': {
                'total': total_units,
                'occupied': occupied_units,
                'available': available_units,
                'maintenance': maintenance_units,
                'occupancy_rate': round(occupancy_rate, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

