from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
import sys
from urllib.parse import quote_plus

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base

# 加载环境变量
load_dotenv()

# 从环境变量获取数据库配置
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', ''))  # 使用 quote_plus 编码密码
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'greener_bake')

# 修改数据库连接URL，将编码参数移到查询字符串中
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

# 创建引擎时配置连接池
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # 增加连接池大小
    max_overflow=30,  # 增加最大溢出连接数
    pool_timeout=60,  # 增加超时时间
    pool_recycle=3600,  # 每小时回收连接
    pool_pre_ping=True  # 在使用前检查连接是否有效
)

# 创建会话工厂
SessionFactory = sessionmaker(bind=engine)

# 创建线程安全的会话
Session = scoped_session(SessionFactory)

# 添加SessionLocal作为Session的别名，用于初始化脚本
SessionLocal = Session

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话的生成器函数"""
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Session.remove()  # 确保清理会话

# 初始化 SQLAlchemy
db = SQLAlchemy()

def init_app(app):
    db.init_app(app)
    # 初始化迁移
    migrate = Migrate(app, db)
    return db 