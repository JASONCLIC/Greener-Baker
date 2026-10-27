from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import User, UserRole

class UserService:
    @staticmethod
    def create_user(db: Session, email: str, username: str, password: str, role: UserRole):
        # 检查邮箱是否已存在
        if db.query(User).filter(User.email == email).first():
            raise ValueError("该邮箱已被注册")
            
        hashed_password = generate_password_hash(password)
        user = User(
            email=email,
            username=username,
            password=hashed_password,
            role=role
        )
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def verify_user(db: Session, email: str, password: str):
        try:
            user = db.query(User).filter(User.email == email).first()
            if user and check_password_hash(user.password, password):
                return user
            return None
        except Exception as e:
            print(f"Error verifying user: {str(e)}")  # 添加错误日志
            raise e 