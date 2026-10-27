#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 数据库迁移脚本 - 添加供应商和材料价格表

from flask import Flask
from sqlalchemy import create_engine, MetaData, Column, String, Integer, ForeignKey, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv
from datetime import datetime
from models import Base, Supplier, MaterialPrice, Material

# 加载环境变量
load_dotenv()

# 创建临时Flask应用
app = Flask(__name__)

# 数据库连接URI
DB_URI = f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}/{os.getenv('DB_NAME', 'greenerbake')}"

# 创建引擎和会话
engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

def create_suppliers_table():
    """创建供应商表"""
    print("正在检查供应商表是否存在...")
    
    # 获取元数据
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    if 'suppliers' in metadata.tables:
        print("供应商表已存在，跳过创建")
    else:
        print("供应商表不存在，开始创建...")
        
        # 创建供应商表
        Base.metadata.tables['suppliers'].create(engine)
        print("供应商表创建成功")

def create_material_prices_table():
    """创建材料价格表"""
    print("正在检查材料价格表是否存在...")
    
    # 获取元数据
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    if 'material_prices' in metadata.tables:
        print("材料价格表已存在，跳过创建")
    else:
        print("材料价格表不存在，开始创建...")
        
        # 创建材料价格表
        Base.metadata.tables['material_prices'].create(engine)
        print("材料价格表创建成功")

def insert_sample_data():
    """插入示例数据"""
    print("开始插入示例数据...")
    
    # 检查是否已有供应商数据
    existing_suppliers = session.query(Supplier).count()
    if existing_suppliers > 0:
        print(f"已存在 {existing_suppliers} 个供应商记录，跳过示例数据插入")
        return
    
    # 添加供应商数据
    suppliers = [
        ('面粉供应商A', '北京市朝阳区123号', '张经理', '13800138001', 'flour_supplierA@example.com', 2.5),
        ('面粉供应商B', '上海市浦东新区456号', '李经理', '13800138002', 'flour_supplierB@example.com', 1.8),
        ('面粉供应商C', '广州市天河区789号', '王经理', '13800138003', 'flour_supplierC@example.com', 3.2),
        ('糖供应商A', '成都市武侯区234号', '赵经理', '13800138004', 'sugar_supplierA@example.com', 3.8),
        ('糖供应商B', '重庆市渝中区567号', '钱经理', '13800138005', 'sugar_supplierB@example.com', 4.2),
        ('黄油供应商A', '深圳市南山区890号', '孙经理', '13800138006', 'butter_supplierA@example.com', 5.6),
        ('黄油供应商B', '杭州市西湖区345号', '周经理', '13800138007', 'butter_supplierB@example.com', 6.2),
        ('鸡蛋供应商A', '南京市鼓楼区678号', '吴经理', '13800138008', 'egg_supplierA@example.com', 1.2),
        ('鸡蛋供应商B', '武汉市江汉区901号', '郑经理', '13800138009', 'egg_supplierB@example.com', 1.5)
    ]
    
    supplier_objects = []
    for supplier_data in suppliers:
        name, address, contact, phone, email, carbon_rating = supplier_data
        new_supplier = Supplier(
            name=name,
            address=address,
            contact=contact,
            phone=phone,
            email=email,
            carbon_footprint_rating=carbon_rating
        )
        supplier_objects.append(new_supplier)
        session.add(new_supplier)
    
    session.commit()
    print(f"成功添加 {len(supplier_objects)} 个供应商记录")
    
    # 检查材料是否存在，并添加价格记录
    store_id = 1  # 假设使用ID为1的商店
    
    materials = {
        '面粉': {'stock': 50.0, 'unit': 'kg'},
        '糖': {'stock': 30.0, 'unit': 'kg'},
        '黄油': {'stock': 20.0, 'unit': 'kg'},
        '鸡蛋': {'stock': 100.0, 'unit': '个'}
    }
    
    material_objects = {}
    
    for material_name, data in materials.items():
        # 检查材料是否存在
        material = session.query(Material).filter(
            Material.name == material_name,
            Material.store_id == store_id
        ).first()
        
        if not material:
            # 创建新材料
            print(f"材料 '{material_name}' 不存在，创建新记录...")
            material = Material(
                name=material_name,
                store_id=store_id,
                current_stock=data['stock'],
                unit=data['unit']
            )
            session.add(material)
            session.commit()
            
        material_objects[material_name] = material
    
    # 添加材料价格数据
    price_data = [
        ('面粉供应商A', '面粉', 5.5, 0.8),
        ('面粉供应商B', '面粉', 6.2, 0.5),
        ('面粉供应商C', '面粉', 4.8, 1.2),
        ('糖供应商A', '糖', 7.2, 1.5),
        ('糖供应商B', '糖', 6.8, 1.8),
        ('黄油供应商A', '黄油', 12.5, 2.3),
        ('黄油供应商B', '黄油', 11.8, 2.8),
        ('鸡蛋供应商A', '鸡蛋', 0.8, 0.3),
        ('鸡蛋供应商B', '鸡蛋', 0.75, 0.4)
    ]
    
    price_count = 0
    for price_item in price_data:
        supplier_name, material_name, price, emission = price_item
        
        supplier = session.query(Supplier).filter(Supplier.name == supplier_name).first()
        material = material_objects.get(material_name)
        
        if supplier and material:
            # 检查是否已存在价格记录
            existing_price = session.query(MaterialPrice).filter(
                MaterialPrice.material_id == material.id,
                MaterialPrice.supplier_id == supplier.id
            ).first()
            
            if not existing_price:
                new_price = MaterialPrice(
                    material_id=material.id,
                    supplier_id=supplier.id,
                    price=price,
                    carbon_emission=emission,
                    effective_date=datetime.utcnow()
                )
                session.add(new_price)
                price_count += 1
    
    session.commit()
    print(f"成功添加 {price_count} 条价格记录")

def main():
    """执行迁移程序"""
    try:
        print("开始执行数据库迁移...")
        
        # 创建表
        create_suppliers_table()
        create_material_prices_table()
        
        # 插入示例数据
        insert_sample_data()
        
        print("数据库迁移完成")
    except Exception as e:
        print(f"迁移过程中出错: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main() 