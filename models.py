import os
from dotenv import load_dotenv
from enum import Enum
from sqlalchemy import Column, String, Integer, Enum as SQLAEnum, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import relationship

load_dotenv()

Base = declarative_base()

class UserRole(Enum):
    ADMIN = "管理员"
    MANAGER = "商店经理"
    USER = "普通用户"

class Store(Base):
    __tablename__ = 'stores'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(120), unique=True, nullable=False)
    username = Column(String(80), nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(SQLAEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=True)
    store = relationship("Store", backref="managers")

class Role(Base):
    __tablename__ = 'roles'
    
    email = Column(String(120), primary_key=True)
    role_name = Column(SQLAEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')  # Secret key for session management and CSRF protection

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )  # Database URI using environment variables for username, password, host, port, and db name

    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable modification tracking to save resources
    WTF_CSRF_ENABLED = True  # Enable CSRF protection
    LOGGING_LEVEL = 'DEBUG'  # Log level (can be DEBUG, INFO, WARNING, ERROR, or CRITICAL)


class DevelopmentConfig(Config):
    DEBUG = True  # Enable debugging in the development environment


class ProductionConfig(Config):
    DEBUG = False  # Disable debugging in the production environment

class Device(Base):
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)  # oven, refrigerator, mixer
    power_rating = Column(Float, nullable=False)  # 额定功率(W)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    status = Column(String(20), default='inactive')  # active, inactive, maintenance
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", backref="devices")

class DeviceData(Base):
    __tablename__ = 'device_data'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    power_consumption = Column(Float, nullable=False)  # 当前功率(W)
    temperature = Column(Float)  # 温度（针对烤箱）
    
    device = relationship("Device", backref="power_data")

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    unit = Column(String(20), default='个')
    
    store = relationship("Store", backref="products")

class SalesRecord(Base):
    __tablename__ = 'sales_records'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    sale_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product")
    store = relationship("Store", backref="sales_records")

class Material(Base):
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    current_stock = Column(Float, nullable=False)
    unit = Column(String(20), default='kg')
    
    store = relationship("Store", backref="materials")

class DeviceStatusHistory(Base):
    __tablename__ = 'device_status_history'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    status = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device", backref="status_history")


# 新增模型：产品配方表
class Recipe(Base):
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    amount = Column(Float, nullable=False)  # 每一单位产品需要的原料数量
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", backref="recipes")
    material = relationship("Material", backref="recipes")


# 新增模型：供应商表
class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    contact = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))
    carbon_footprint_rating = Column(Float, default=0)  # 碳足迹评级(0-10)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 新增模型：原料价格表
class MaterialPrice(Base):
    __tablename__ = 'material_prices'

    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    price = Column(Float, nullable=False)  # 单位价格
    carbon_emission = Column(Float, default=0)  # 单位碳排放量(kg)
    effective_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    material = relationship("Material", backref="prices")
    supplier = relationship("Supplier", backref="material_prices")