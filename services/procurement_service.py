import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import requests
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, List, Tuple, Any

from models import Product, SalesRecord, Recipe, Material, MaterialPrice, Supplier


class ProcurementService:
    @staticmethod
    def predict_sales(db: Session, store_id: int, days_to_predict: int = 90) -> Dict[int, int]:
        """
        使用线性回归预测未来销售量
        
        Args:
            db: 数据库会话
            store_id: 商店ID
            days_to_predict: 预测未来多少天的销售量（默认90天，约3个月）
            
        Returns:
            字典，键为产品ID，值为预测销售量
        """
        # 获取所有产品
        products = db.query(Product).filter(Product.store_id == store_id).all()
        
        # 获取最近6个月的销售数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # 6个月历史数据
        
        # 存储预测结果
        predictions = {}
        
        for product in products:
            # 获取产品的历史销售数据
            sales_data = db.query(
                SalesRecord.sale_date,
                func.sum(SalesRecord.quantity).label('quantity')
            ).filter(
                SalesRecord.product_id == product.id,
                SalesRecord.store_id == store_id,
                SalesRecord.sale_date.between(start_date, end_date)
            ).group_by(
                SalesRecord.sale_date
            ).order_by(
                SalesRecord.sale_date
            ).all()
            
            if not sales_data or len(sales_data) < 10:
                # 数据不足以进行可靠预测，使用简单平均值
                if sales_data:
                    avg_sales = sum(record.quantity for record in sales_data) / len(sales_data)
                    predictions[product.id] = int(avg_sales * days_to_predict / 30)  # 转换为月销量
                else:
                    predictions[product.id] = 0
                continue
            
            # 准备训练数据
            dates = [(record.sale_date - start_date).days for record in sales_data]
            sales = [record.quantity for record in sales_data]
            
            # 转换为numpy数组并重塑
            X = np.array(dates).reshape(-1, 1)
            y = np.array(sales)
            
            # 创建并训练线性回归模型
            model = LinearRegression()
            model.fit(X, y)
            
            # 预测未来销售
            last_day = (end_date - start_date).days
            future_days = np.array(range(last_day + 1, last_day + days_to_predict + 1)).reshape(-1, 1)
            future_sales = model.predict(future_days)
            
            # 处理负值预测
            future_sales = np.maximum(future_sales, 0)
            
            # 累加预测的总销售量
            total_predicted_sales = int(np.sum(future_sales))
            predictions[product.id] = total_predicted_sales
        
        return predictions
    
    @staticmethod
    def calculate_material_needs(db: Session, predicted_sales: Dict[int, int]) -> Dict[int, float]:
        """
        根据预测的销售量计算所需原料
        
        Args:
            db: 数据库会话
            predicted_sales: 预测的销售量字典，键为产品ID，值为销售量
            
        Returns:
            字典，键为原料ID，值为所需总量
        """
        material_needs = {}
        
        for product_id, quantity in predicted_sales.items():
            # 获取产品的配方
            recipes = db.query(Recipe).filter(Recipe.product_id == product_id).all()
            
            for recipe in recipes:
                material_id = recipe.material_id
                required_amount = recipe.amount * float(quantity)
                
                if material_id in material_needs:
                    material_needs[material_id] += required_amount
                else:
                    material_needs[material_id] = required_amount
        
        return material_needs
    
    @staticmethod
    def find_best_suppliers(db: Session, material_needs: Dict[int, float]) -> Dict[str, Any]:
        """
        为所需原料找到最佳供应商
        
        Args:
            db: 数据库会话
            material_needs: 字典，键为原料ID，值为所需总量
            
        Returns:
            采购计划字典
        """
        purchase_plan = {
            'materials': {},
            'purchase_plan': {},
            'total_cost': 0
        }
        
        for material_id, needed_amount in material_needs.items():
            material = db.get(Material, material_id)
            if not material:
                continue
                
            # 减去当前库存
            purchase_amount = max(0, needed_amount - material.current_stock)
            
            if purchase_amount <= 0:
                continue
                
            # 获取材料的所有供应商价格
            prices = db.query(MaterialPrice).filter(
                MaterialPrice.material_id == material_id
            ).order_by(
                MaterialPrice.effective_date.desc()
            ).all()
            
            if not prices:
                continue
            
            # 选择综合评分最高的供应商（价格和碳排放的加权平均）
            best_supplier = None
            best_score = float('inf')
            
            for price in prices:
                # 综合评分：价格 + 碳排放量 * 权重
                carbon_weight = 20  # 碳排放权重系数
                score = price.price + price.carbon_emission * carbon_weight
                
                if score < best_score:
                    best_score = score
                    best_supplier = price
            
            if best_supplier:
                supplier = db.get(Supplier, best_supplier.supplier_id)
                if supplier:
                    # 添加到采购计划
                    purchase_plan['materials'][material_id] = {
                        'name': material.name,
                        'total_amount': needed_amount,
                        'unit': material.unit,
                        'current_stock': material.current_stock,
                        'need_purchase': round(purchase_amount, 2)
                    }
                    
                    purchase_plan['purchase_plan'][material_id] = {
                        'material_name': material.name,
                        'amount': round(purchase_amount, 2),
                        'unit': material.unit,
                        'supplier_name': supplier.name,
                        'price': best_supplier.price,
                        'carbon_emission': best_supplier.carbon_emission,
                        'total_price': round(best_supplier.price * purchase_amount, 2)
                    }
                    
                    purchase_plan['total_cost'] += best_supplier.price * purchase_amount
        
        purchase_plan['total_cost'] = round(purchase_plan['total_cost'], 2)
        return purchase_plan
    
    @staticmethod
    def get_market_prices(material_names: List[str]) -> Dict[str, Dict[str, float]]:
        """
        模拟从公开市场获取价格数据
        实际实现应使用Web爬虫或API调用获取真实数据
        
        Args:
            material_names: 原料名称列表
            
        Returns:
            嵌套字典，外层键为原料名称，内层键为供应商名称，值为价格
        """
        # 这里模拟市场价格数据
        # 实际实现应调用真实API或爬取网页
        market_data = {}
        
        common_suppliers = ["阳光农场", "绿色食材", "有机之源", "环保食品", "低碳供应链"]
        
        for material in material_names:
            market_data[material] = {}
            base_price = 10 + hash(material) % 20  # 生成一个基础价格
            
            for supplier in common_suppliers:
                # 模拟不同供应商的价格差异
                variation = (hash(supplier) % 10) / 10  # -10%到+10%的变化
                price = base_price * (1 + variation)
                carbon = base_price * 0.1 * (1 - variation/2)  # 价格低的通常碳排放高一些
                
                market_data[material][supplier] = {
                    "price": round(price, 2),
                    "carbon_emission": round(carbon, 2)
                }
        
        return market_data 