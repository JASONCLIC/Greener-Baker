import sys
import os
from config.database import engine, SessionLocal
from models import Base, User, UserRole
from werkzeug.security import generate_password_hash


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_database():
    try:
        # 删除所有现有表（如果存在）
        Base.metadata.drop_all(bind=engine)
        print("Existing tables deleted")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("New tables created")

        # 创建会话
        session = SessionLocal()

        try:
            # 创建管理员用户
            admin_user = User(
                email="admin@example.com",
                username="admin",
                password=generate_password_hash("admin123"),
                role=UserRole.ADMIN
            )
            session.add(admin_user)
            
            # 提交更改
            session.commit()
            print("Admin account initialization complete")
            print("\nAdmin account information:")
            print("- Email: admin@example.com")
            print("- Password: admin123")
            
        except Exception as e:
            session.rollback()
            print(f"Data initialization failed: {str(e)}")
        finally:
            session.close()
            
    except Exception as e:
        print(f"Database initialization failed: {str(e)}")

if __name__ == "__main__":
    init_database() 