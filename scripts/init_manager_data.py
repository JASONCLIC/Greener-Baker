import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, Store, User, UserRole, Device, Product, Material, SalesRecord, DeviceData
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import random

load_dotenv()

# 数据库连接配置
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 创建会话
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def init_manager_data():
    try:
        # 首先清理已存在的数据
        print("Clearing existing data...")
        session.query(DeviceData).delete()
        session.query(SalesRecord).delete()
        session.query(Material).delete()
        session.query(Product).delete()
        session.query(Device).delete()
        session.query(User).filter(User.role == UserRole.MANAGER).delete()
        session.query(Store).delete()
        session.commit()
        print("Existing data cleared")

        # 创建第一个示例门店
        store1 = Store(
            name="Greener Bake Flagship Store",
            address="500 Zhangyang Road, Pudong, Shanghai"
        )
        session.add(store1)
        
        # 创建第二个示例门店
        store2 = Store(
            name="Greener Bake Xujiahui Store",
            address="1 Hongqiao Road, Xuhui, Shanghai"
        )
        session.add(store2)
        session.flush()

        # 创建店铺经理账号
        managers = [
            User(
                username="store_manager1",
                email="manager1@greenerbake.com",
                password=generate_password_hash("manager123"),
                role=UserRole.MANAGER,
                store_id=store1.id
            ),
            User(
                username="store_manager2",
                email="manager2@greenerbake.com",
                password=generate_password_hash("manager123"),
                role=UserRole.MANAGER,
                store_id=store2.id
            )
        ]
        session.add_all(managers)

        # 为两个店铺添加设备
        for store in [store1, store2]:
            devices = [
                Device(
                    name=f"{store.name}-Main Oven",
                    device_type="oven",
                    power_rating=3500,
                    store_id=store.id,
                    status="active"
                ),
                Device(
                    name=f"{store.name}-Refrigerator 1",
                    device_type="refrigerator",
                    power_rating=500,
                    store_id=store.id,
                    status="active"
                ),
                Device(
                    name=f"{store.name}-Mixer",
                    device_type="mixer",
                    power_rating=1200,
                    store_id=store.id,
                    status="active"
                )
            ]
            session.add_all(devices)

        # 为两个店铺添加产品
        for store in [store1, store2]:
            products = [
                Product(name="Whole Wheat Bread", store_id=store.id, unit="piece"),
                Product(name="Croissant", store_id=store.id, unit="piece"),
                Product(name="Chocolate Cake", store_id=store.id, unit="piece")
            ]
            session.add_all(products)
            session.flush()

            # 添加原材料
            materials = [
                Material(name="Flour", store_id=store.id, current_stock=100.0, unit="kg"),
                Material(name="Sugar", store_id=store.id, current_stock=50.0, unit="kg"),
                Material(name="Butter", store_id=store.id, current_stock=30.0, unit="kg"),
                Material(name="Eggs", store_id=store.id, current_stock=200.0, unit="piece")
            ]
            session.add_all(materials)

            # 添加销售记录
            today = datetime.now().date()
            for i in range(7):  # 添加过去7天的销售记录
                date = today - timedelta(days=i)
                for product in products:
                    sales_record = SalesRecord(
                        product_id=product.id,
                        store_id=store.id,
                        quantity=30 + i * 2,  # 模拟每天不同的销量
                        sale_date=date
                    )
                    session.add(sales_record)

        # 为每个设备添加过去24小时的能耗数据
        def generate_device_data(device, days=1):
            # 生成初始的7天历史数据
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # 根据设备类型设置不同的高峰时段
            if device.device_type == "oven":
                peak_hours = [(6, 10), (14, 22)]  # 烤箱的高峰使用时段
            elif device.device_type == "refrigerator":
                peak_hours = [(11, 14), (17, 20)]  # 冷藏柜的高峰时段
            else:  # mixer
                peak_hours = [(5, 8), (13, 16)]    # 搅拌机的高峰时段
            
            # 每15分钟记录一个数据点
            data_points = []
            base_power = device.power_rating * 0.8  # 基础功率为额定功率的80%
            
            current_time = start_time
            while current_time <= end_time:
                hour = current_time.hour
                # 判断是否在高峰时段
                is_peak = any(start <= hour <= end for start, end in peak_hours)
                
                if device.status == 'active':
                    # 在高峰时段功率波动较大
                    if is_peak:
                        power = base_power + random.uniform(-base_power * 0.3, base_power * 0.2)
                    else:
                        power = base_power * 0.6 + random.uniform(-base_power * 0.1, base_power * 0.1)
                else:
                    power = 0

                # 添加一些随机的温度数据（仅针对烤箱）
                temperature = None
                if device.device_type == "oven" and device.status == 'active' and is_peak:
                    temperature = 180 + random.uniform(-20, 20)

                data_point = DeviceData(
                    device_id=device.id,
                    timestamp=current_time,
                    power_consumption=round(power, 2),
                    temperature=round(temperature, 1) if temperature is not None else None
                )
                data_points.append(data_point)
                current_time += timedelta(minutes=15)  # 每15分钟一个数据点
            
            return data_points

        # 获取所有设备并生成数据
        devices = session.query(Device).all()
        for device in devices:
            print(f"Generating energy data for device {device.name}...")
            device_data = generate_device_data(device, days=7)  # 生成7天的数据
            session.add_all(device_data)
            print(f"Generated {len(device_data)} data records for device {device.name}")

        # 提交所有更改
        session.commit()
        print("Store manager data initialization complete!")
        
        # 打印登录信息
        print("\nTest account information:")
        print("Flagship Store Manager:")
        print("- Email: manager1@greenerbake.com")
        print("- Password: manager123")
        print("\nXujiahui Store Manager:")
        print("- Email: manager2@greenerbake.com")
        print("- Password: manager123")

    except Exception as e:
        session.rollback()
        print(f"Data initialization failed: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    init_manager_data() 