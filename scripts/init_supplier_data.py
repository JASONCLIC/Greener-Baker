#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 初始化供应商数据脚本

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, Supplier, Material, MaterialPrice

# 加载环境变量
load_dotenv()

# 数据库连接URI
DB_URI = f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}/{os.getenv('DB_NAME', 'greenerbake')}"

# 创建引擎和会话
engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

def init_supplier_data():
    """初始化供应商数据"""
    print("Starting supplier data initialization...")
    
    # 检查是否已有供应商数据
    existing_suppliers = session.query(Supplier).count()
    if existing_suppliers > 0:
        print(f"{existing_suppliers} supplier records already exist, skipping initialization")
        return
    
    # 添加供应商数据
    suppliers = [
        ('Flour Supplier A', '123 Chaoyang District, Beijing', 'Manager Zhang', '13800138001', 'flour_supplierA@example.com', 2.5),
        ('Flour Supplier B', '456 Pudong District, Shanghai', 'Manager Li', '13800138002', 'flour_supplierB@example.com', 1.8),
        ('Flour Supplier C', '789 Tianhe District, Guangzhou', 'Manager Wang', '13800138003', 'flour_supplierC@example.com', 3.2),
        ('Sugar Supplier A', '234 Wuhou District, Chengdu', 'Manager Zhao', '13800138004', 'sugar_supplierA@example.com', 3.8),
        ('Sugar Supplier B', '567 Yuzhong District, Chongqing', 'Manager Qian', '13800138005', 'sugar_supplierB@example.com', 4.2),
        ('Butter Supplier A', '890 Nanshan District, Shenzhen', 'Manager Sun', '13800138006', 'butter_supplierA@example.com', 5.6),
        ('Butter Supplier B', '345 Xihu District, Hangzhou', 'Manager Zhou', '13800138007', 'butter_supplierB@example.com', 6.2),
        ('Egg Supplier A', '678 Gulou District, Nanjing', 'Manager Wu', '13800138008', 'egg_supplierA@example.com', 1.2),
        ('Egg Supplier B', '901 Jianghan District, Wuhan', 'Manager Zheng', '13800138009', 'egg_supplierB@example.com', 1.5)
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
    print(f"Successfully added {len(supplier_objects)} supplier records")
    
    # 为每个商店添加材料价格数据
    stores = session.query(Material.store_id).distinct().all()
    store_ids = [store[0] for store in stores]
    
    for store_id in store_ids:
        print(f"Adding material price data for store {store_id}...")
        
        # 获取该商店的材料
        materials = session.query(Material).filter(Material.store_id == store_id).all()
        
        # 材料价格数据
        price_data = [
            ('Flour Supplier A', 'Flour', 5.5, 0.8),
            ('Flour Supplier B', 'Flour', 6.2, 0.5),
            ('Flour Supplier C', 'Flour', 4.8, 1.2),
            ('Sugar Supplier A', 'Sugar', 7.2, 1.5),
            ('Sugar Supplier B', 'Sugar', 6.8, 1.8),
            ('Butter Supplier A', 'Butter', 12.5, 2.3),
            ('Butter Supplier B', 'Butter', 11.8, 2.8),
            ('Egg Supplier A', 'Eggs', 0.8, 0.3),
            ('Egg Supplier B', 'Eggs', 0.75, 0.4)
        ]
        
        price_count = 0
        for price_item in price_data:
            supplier_name, material_name, price, emission = price_item
            
            # 查找供应商
            supplier = session.query(Supplier).filter(Supplier.name == supplier_name).first()
            if not supplier:
                continue
                
            # 查找材料
            material = session.query(Material).filter(
                Material.name == material_name,
                Material.store_id == store_id
            ).first()
            if not material:
                continue
            
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
        print(f"Successfully added {price_count} price records for store {store_id}")

if __name__ == '__main__':
    try:
        init_supplier_data()
        print("Supplier data initialization complete")
    except Exception as e:
        print(f"Error during initialization: {str(e)}")
        session.rollback()
    finally:
        session.close() 