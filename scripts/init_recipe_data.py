#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 初始化配方数据脚本

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, Product, Material, Recipe

# 加载环境变量
load_dotenv()

# 数据库连接URI
DB_URI = f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}/{os.getenv('DB_NAME', 'greenerbake')}"

# 创建引擎和会话
engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

def init_recipe_data():
    """初始化配方数据"""
    print("Starting recipe data initialization...")
    
    # 检查是否已有配方数据
    existing_recipes = session.query(Recipe).count()
    if existing_recipes > 0:
        print(f"{existing_recipes} recipe records already exist, skipping initialization")
        return
    
    # 获取所有商店
    stores = session.query(Product.store_id).distinct().all()
    
    for (store_id,) in stores:
        print(f"Adding recipe data for store {store_id}...")
        
        # 获取该商店的产品和原料
        products = session.query(Product).filter(Product.store_id == store_id).all()
        materials = session.query(Material).filter(Material.store_id == store_id).all()
        
        # 创建配方数据
        recipes_data = []
        
        for product in products:
            if product.name == "Whole Wheat Bread":
                recipes_data.extend([
                    (product.id, next(m.id for m in materials if m.name == "Flour"), 0.5),  # 每个面包需要0.5kg面粉
                    (product.id, next(m.id for m in materials if m.name == "Sugar"), 0.05),   # 每个面包需要0.05kg糖
                    (product.id, next(m.id for m in materials if m.name == "Butter"), 0.03),  # 每个面包需要0.03kg黄油
                    (product.id, next(m.id for m in materials if m.name == "Eggs"), 1),     # 每个面包需要1个鸡蛋
                ])
            elif product.name == "Croissant":
                recipes_data.extend([
                    (product.id, next(m.id for m in materials if m.name == "Flour"), 0.3),   # 每个可颂需要0.3kg面粉
                    (product.id, next(m.id for m in materials if m.name == "Sugar"), 0.03),    # 每个可颂需要0.03kg糖
                    (product.id, next(m.id for m in materials if m.name == "Butter"), 0.15),   # 每个可颂需要0.15kg黄油
                    (product.id, next(m.id for m in materials if m.name == "Eggs"), 1),      # 每个可颂需要1个鸡蛋
                ])
            elif product.name == "Chocolate Cake":
                recipes_data.extend([
                    (product.id, next(m.id for m in materials if m.name == "Flour"), 0.4),   # 每个蛋糕需要0.4kg面粉
                    (product.id, next(m.id for m in materials if m.name == "Sugar"), 0.2),     # 每个蛋糕需要0.2kg糖
                    (product.id, next(m.id for m in materials if m.name == "Butter"), 0.2),    # 每个蛋糕需要0.2kg黄油
                    (product.id, next(m.id for m in materials if m.name == "Eggs"), 4),      # 每个蛋糕需要4个鸡蛋
                ])
        
        # 添加配方记录
        recipe_count = 0
        for product_id, material_id, amount in recipes_data:
            recipe = Recipe(
                product_id=product_id,
                material_id=material_id,
                amount=amount,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(recipe)
            recipe_count += 1
        
        session.commit()
        print(f"Successfully added {recipe_count} recipe records for store {store_id}")

if __name__ == '__main__':
    try:
        init_recipe_data()
        print("Recipe data initialization complete!")
    except Exception as e:
        print(f"Error initializing recipe data: {str(e)}")
    finally:
        session.close() 