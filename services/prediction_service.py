import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from models import SalesRecord, Recipe, MaterialPrice, Supplier

class PredictionService:
    @staticmethod
    def predict_sales(db, store_id, product_id, months_to_predict=1):
        """使用简单的线性回归预测未来销售量
        
        Args:
            db: 数据库会话
            store_id: 店铺ID
            product_id: 产品ID
            months_to_predict: 预测未来几个月的销售量
            
        Returns:
            预测的销售量
        """
        # 获取过去12个月的销售数据
        today = datetime.now()
        start_date = today - timedelta(days=365)
        
        # 按月分组查询销售数据
        monthly_sales = db.query(
            func.date_format(SalesRecord.sale_date, '%Y-%m').label('month'),
            func.sum(SalesRecord.quantity).label('total')
        ).filter(
            SalesRecord.store_id == store_id,
            SalesRecord.product_id == product_id,
            SalesRecord.sale_date >= start_date
        ).group_by(
            func.date_format(SalesRecord.sale_date, '%Y-%m')
        ).order_by(
            func.date_format(SalesRecord.sale_date, '%Y-%m')
        ).all()
        
        # 如果没有数据，返回预测值为10
        if not monthly_sales:
            return 10
        
        # 预处理销售数据用于线性回归
        x = np.array(range(1, len(monthly_sales) + 1))
        y = np.array([sale[1] for sale in monthly_sales])
        
        if len(x) < 2:
            # 数据不足以进行回归，直接返回最近一次的销售量
            return y[0]
        
        # 简单线性回归：y = mx + b
        A = np.vstack([x, np.ones(len(x))]).T
        
        try:
            # 使用最小二乘法求解线性回归参数
            m, b = np.linalg.lstsq(A, y, rcond=None)[0]
            
            # 预测未来销售量
            next_month = len(monthly_sales) + months_to_predict
            predicted_sales = m * next_month + b
            
            # 确保预测结果为正数
            predicted_sales = max(0, predicted_sales)
            
            # 四舍五入到整数
            return round(predicted_sales)
        except:
            # 回归计算出错，返回过去几个月的平均值
            return round(np.mean(y))
    
    @staticmethod
    def calculate_material_needs(db, product_id, quantity):
        """计算指定产品数量需要的原料量
        
        Args:
            db: 数据库会话
            product_id: 产品ID
            quantity: 产品数量
            
        Returns:
            字典，键是原料ID，值是需要的数量
        """
        # 查询产品配方
        recipes = db.query(Recipe).filter(Recipe.product_id == product_id).all()
        
        material_needs = {}
        for recipe in recipes:
            material_id = recipe.material_id
            amount = recipe.amount * quantity
            
            if material_id not in material_needs:
                material_needs[material_id] = 0
                
            material_needs[material_id] += amount
            
        return material_needs
    
    @staticmethod
    def find_best_supplier(db, material_id, amount_needed, carbon_weight=20):
        """找到给定原料的最佳供应商
        
        Args:
            db: 数据库会话
            material_id: 原料ID
            amount_needed: 需要的原料数量
            carbon_weight: 碳排放权重因子
            
        Returns:
            最佳MaterialPrice对象
        """
        # 查询原料的最新价格
        prices = db.query(MaterialPrice).filter(
            MaterialPrice.material_id == material_id
        ).order_by(
            MaterialPrice.effective_date.desc()
        ).all()
        
        if not prices:
            return None
            
        # 选择评分最高的供应商
        best_supplier = None
        best_score = float('inf')  # 较低的得分更好
        
        for price in prices:
            # 评分 = 价格 + 碳排放量 * 权重
            score = price.price + price.carbon_emission * carbon_weight
            
            if score < best_score:
                best_score = score
                best_supplier = price
                
        return best_supplier 