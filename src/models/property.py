from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# جدول الشركات
class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    name_en = db.Column(db.String(255))
    commercial_registration = db.Column(db.String(100))
    tax_number = db.Column(db.String(100))
    address = db.Column(db.Text)
    address_en = db.Column(db.Text)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    website = db.Column(db.String(255))
    logo_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # العلاقات
    branches = db.relationship('Branch', backref='company', lazy=True)
    users = db.relationship('User', backref='company', lazy=True)
    properties = db.relationship('Property', backref='company', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'commercial_registration': self.commercial_registration,
            'tax_number': self.tax_number,
            'address': self.address,
            'address_en': self.address_en,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

# جدول الفروع
class Branch(db.Model):
    __tablename__ = 'branches'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    name_en = db.Column(db.String(255))
    address = db.Column(db.Text)
    address_en = db.Column(db.Text)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    manager_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'name_en': self.name_en,
            'address': self.address,
            'address_en': self.address_en,
            'phone': self.phone,
            'email': self.email,
            'manager_name': self.manager_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

# جدول الأدوار
class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    users = db.relationship('User', backref='role', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول المستخدمين
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'branch_id': self.branch_id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'role_id': self.role_id,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول أنواع العقارات
class PropertyType(db.Model):
    __tablename__ = 'property_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول فئات العقارات
class PropertyCategory(db.Model):
    __tablename__ = 'property_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# جدول المشاريع
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    name_en = db.Column(db.String(255))
    description = db.Column(db.Text)
    description_en = db.Column(db.Text)
    location = db.Column(db.Text)
    location_en = db.Column(db.Text)
    developer_name = db.Column(db.String(255))
    total_units = db.Column(db.Integer)
    completion_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # العلاقات
    buildings = db.relationship('Building', backref='project', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'description_en': self.description_en,
            'location': self.location,
            'location_en': self.location_en,
            'developer_name': self.developer_name,
            'total_units': self.total_units,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

# جدول المباني
class Building(db.Model):
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    name = db.Column(db.String(255), nullable=False)
    name_en = db.Column(db.String(255))
    address = db.Column(db.Text)
    address_en = db.Column(db.Text)
    total_floors = db.Column(db.Integer)
    total_units = db.Column(db.Integer)
    building_type_id = db.Column(db.Integer, db.ForeignKey('property_types.id'))
    electricity_account = db.Column(db.String(100))
    water_account = db.Column(db.String(100))
    municipality_account = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # العلاقات
    units = db.relationship('Unit', backref='building', lazy=True)
    building_type = db.relationship('PropertyType', backref='buildings')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'project_id': self.project_id,
            'name': self.name,
            'name_en': self.name_en,
            'address': self.address,
            'address_en': self.address_en,
            'total_floors': self.total_floors,
            'total_units': self.total_units,
            'building_type_id': self.building_type_id,
            'electricity_account': self.electricity_account,
            'water_account': self.water_account,
            'municipality_account': self.municipality_account,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

# جدول الوحدات
class Unit(db.Model):
    __tablename__ = 'units'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    unit_number = db.Column(db.String(50), nullable=False)
    floor_number = db.Column(db.Integer)
    unit_type_id = db.Column(db.Integer, db.ForeignKey('property_types.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('property_categories.id'))
    area = db.Column(db.Numeric(10, 2))
    bedrooms = db.Column(db.Integer)
    bathrooms = db.Column(db.Integer)
    balconies = db.Column(db.Integer)
    parking_spaces = db.Column(db.Integer)
    furnished = db.Column(db.Boolean, default=False)
    view_type = db.Column(db.String(100))
    ownership_type = db.Column(db.String(50))  # owned, managed, brokerage
    purchase_price = db.Column(db.Numeric(15, 2))
    current_rent = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(50), default='available')  # available, occupied, maintenance, reserved
    description = db.Column(db.Text)
    description_en = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # العلاقات
    unit_type = db.relationship('PropertyType', backref='units')
    category = db.relationship('PropertyCategory', backref='units')
    contracts = db.relationship('Contract', backref='unit', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'building_id': self.building_id,
            'unit_number': self.unit_number,
            'floor_number': self.floor_number,
            'unit_type_id': self.unit_type_id,
            'category_id': self.category_id,
            'area': float(self.area) if self.area else None,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'balconies': self.balconies,
            'parking_spaces': self.parking_spaces,
            'furnished': self.furnished,
            'view_type': self.view_type,
            'ownership_type': self.ownership_type,
            'purchase_price': float(self.purchase_price) if self.purchase_price else None,
            'current_rent': float(self.current_rent) if self.current_rent else None,
            'status': self.status,
            'description': self.description,
            'description_en': self.description_en,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

# جدول العقارات (مرجع عام للمباني والوحدات)
class Property(db.Model):
    __tablename__ = 'properties'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    property_type = db.Column(db.String(20), nullable=False)  # 'building' or 'unit'
    property_id = db.Column(db.Integer, nullable=False)  # ID of building or unit
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_type': self.property_type,
            'property_id': self.property_id
        }

