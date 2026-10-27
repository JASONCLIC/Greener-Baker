from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash, session, jsonify
from services.user_service import UserService
from services.procurement_service import ProcurementService
from models import UserRole, Config, User, Store, Device, Material, Product, DeviceData, DeviceStatusHistory, Base
from models import Recipe, Supplier, MaterialPrice, SalesRecord
from config.database import get_db
import os
from dotenv import load_dotenv
from functools import wraps
from datetime import datetime, timedelta
import random  # 用于生成示例数据
from sqlalchemy import func


load_dotenv()

app = Flask(__name__, 
    static_folder='static',  # 指定静态文件夹
    static_url_path='/static'  # 指定静态文件URL路径
)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

app.config.from_object(Config)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('css', filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('js', filename)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('请输入邮箱和密码')
            return redirect(url_for('login'))
        
        try:
            db = next(get_db())
            user = UserService.verify_user(db=db, email=email, password=password)
            
            if user:
                # 设置session
                session.clear()
                session['user_id'] = user.id
                session['username'] = user.username
                session['email'] = user.email
                session['role'] = user.role.name  # 使用枚举的名称
                
                print(f"User logged in: {user.username}, Role: {user.role.name}")  # 调试信息
                
                # 根据角色重定向
                if user.role == UserRole.ADMIN:
                    return redirect(url_for('admin_dashboard'))
                elif user.role == UserRole.MANAGER:
                    session['store_id'] = user.store_id  # 为商店经理添加店铺ID
                    return redirect(url_for('manager_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('邮箱或密码错误')
        except Exception as e:
            print(f"Login error: {str(e)}")  # 打印错误信息
            flash('登录失败，请稍后重试')
            
        return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)


@app.route('/about')
def about():
    return render_template('about.html')


# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'ADMIN':
            flash('需要管理员权限')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = next(get_db())
    total_users = db.query(User).count()
    new_users_today = db.query(User).filter(
        User.created_at >= datetime.now().date()
    ).count()
    # 这里可以添加更多统计数据
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         new_users_today=new_users_today,
                         online_users=0)  # 在线用户统计需要额外实现


@app.route('/admin/users')
@admin_required
def admin_users():
    db = next(get_db())
    users = db.query(User).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/users', methods=['POST'])
@admin_required
def admin_add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        try:
            db = next(get_db())
            user = UserService.create_user(db, email, username, password, UserRole[role])
            flash('用户创建成功')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'创建用户失败：{str(e)}')
            return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    try:
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return jsonify({'message': '用户删除成功'}), 200
        return jsonify({'error': '用户不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 添加商店经理权限装饰器
def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'MANAGER':
            flash('需要商店经理权限')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# 添加商店经理路由
@app.route('/manager/dashboard')
@manager_required
def manager_dashboard():
    db = next(get_db())
    store_id = session.get('store_id')
    store = db.query(Store).get(store_id)
    devices = db.query(Device).filter(Device.store_id == store_id).all()
    
    return render_template('manager/dashboard.html',
                         store=store,
                         devices=devices)


@app.route('/manager/energy')
@manager_required
def manager_energy():
    db = next(get_db())
    store_id = session.get('store_id')
    store = db.query(Store).get(store_id)
    devices = db.query(Device).filter(Device.store_id == store_id).all()
    
    # 计算统计数据
    active_devices = sum(1 for device in devices if device.status == 'active')
    total_devices = len(devices)
    
    # 模拟能耗数据（实际项目中应该从数据库获取）
    total_consumption = round(120.5, 2)  # 保留两位小数
    consumption_change = round(-5.2, 2)  # 保留两位小数
    alert_count = 0  # 示例数据
    
    # 为每个设备添加当前功率和今日能耗数据
    for device in devices:
        device.current_power = round(device.power_rating * 0.8, 2)  # 保留两位小数
        device.today_consumption = round(device.current_power * 8 / 1000, 2)  # 保留两位小数
        device.status_text = 'Running' if device.status == 'active' else 'Stopped'

    return render_template('manager/energy.html',
                         store=store,
                         devices=devices,
                         total_consumption=total_consumption,
                         consumption_change=consumption_change,
                         active_devices=active_devices,
                         total_devices=total_devices,
                         alert_count=alert_count)


@app.route('/manager/inventory')
@manager_required
def manager_inventory():
    db = next(get_db())
    store_id = session.get('store_id')
    store = db.query(Store).get(store_id)
    materials = db.query(Material).filter(Material.store_id == store_id).all()
    products = db.query(Product).filter(Product.store_id == store_id).all()

    # 查询销售记录数据
    sales_records_query = db.query(
        SalesRecord.id,
        SalesRecord.sale_date,
        Product.name.label('product_name'),
        SalesRecord.quantity
    ).join(
        Product, SalesRecord.product_id == Product.id
    ).filter(
        SalesRecord.store_id == store_id
    ).order_by(
        SalesRecord.sale_date.desc()
    ).limit(20)  # 只显示最近20条记录

    # 将查询结果转换为字典列表
    sales_records = []
    for record in sales_records_query:
        sales_records.append({
            'id': record.id,
            'date': record.sale_date.strftime('%Y-%m-%d'),
            'product': record.product_name,
            'quantity': record.quantity
        })

    return render_template('manager/inventory.html',
                           store=store,
                           materials=materials,
                           products=products,
                           sales_records=sales_records)


@app.route('/manager/devices')
@manager_required
def manager_devices():
    db = next(get_db())
    store_id = session.get('store_id')
    store = db.query(Store).get(store_id)
    devices = db.query(Device).filter(Device.store_id == store_id).all()
    return render_template('manager/devices.html', 
                         store=store,
                         devices=devices)


@app.route('/manager/devices/<int:device_id>/toggle', methods=['POST'])
@manager_required
def toggle_device(device_id):
    try:
        db = next(get_db())
        device = db.query(Device).filter(
            Device.id == device_id,
            Device.store_id == session.get('store_id')
        ).first()
        
        if device:
            # 更新设备状态
            new_status = 'inactive' if device.status == 'active' else 'active'
            device.status = new_status
            
            # 记录状态变更历史
            status_history = DeviceStatusHistory(
                device_id=device.id,
                status=new_status,
                timestamp=datetime.now()
            )
            db.add(status_history)
            db.commit()
            
            # 计算当前功率
            current_power = 0
            if new_status == 'active':
                hour = datetime.now().hour
                is_working_hours = 8 <= hour <= 20
                if is_working_hours:
                    current_power = device.power_rating * 0.85
                else:
                    current_power = device.power_rating * 0.35
            
            return jsonify({
                'success': True, 
                'status': new_status,
                'current_power': round(current_power, 2),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify({'success': False, 'message': '设备不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/manager/devices', methods=['POST'])
@manager_required
def manager_add_device():
    try:
        db = next(get_db())
        device = Device(
            name=request.form['device_name'],
            device_type=request.form['device_type'],
            power_rating=float(request.form['power_rating']),
            store_id=session.get('store_id'),
            status='inactive',
            created_at=datetime.now()  # 设置创建时间
        )
        db.add(device)
        db.commit()
        flash('设备添加成功')
    except Exception as e:
        flash(f'添加设备失败：{str(e)}')
    
    return redirect(url_for('manager_devices'))


@app.route('/manager/devices/<int:device_id>', methods=['DELETE'])
@manager_required
def manager_delete_device(device_id):
    try:
        db = next(get_db())
        device = db.query(Device).filter(
            Device.id == device_id,
            Device.store_id == session.get('store_id')
        ).first()
        
        if device:
            db.delete(device)
            db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': '设备不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/manager/devices/<int:device_id>')
@manager_required
def get_device(device_id):
    try:
        db = next(get_db())
        device = db.query(Device).filter(
            Device.id == device_id,
            Device.store_id == session.get('store_id')
        ).first()
        
        if device:
            return jsonify({
                'success': True,
                'device': {
                    'name': device.name,
                    'device_type': device.device_type,
                    'power_rating': device.power_rating
                }
            })
        return jsonify({'success': False, 'message': '设备不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/manager/devices/<int:device_id>/edit', methods=['POST'])
@manager_required
def edit_device(device_id):
    try:
        db = next(get_db())
        device = db.query(Device).filter(
            Device.id == device_id,
            Device.store_id == session.get('store_id')
        ).first()
        
        if device:
            device.name = request.form['device_name']
            device.device_type = request.form['device_type']
            device.power_rating = float(request.form['power_rating'])
            
            db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': '设备不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def generate_mock_device_data(device_id, start_time, end_time, device_status, status_history=None):
    """生成模拟设备数据，考虑状态历史"""
    data = []
    current_time = start_time
    random.seed(device_id)
    base_power = random.uniform(800, 3000)  # 基础功率
    random.seed()
    
    # 按时间排序状态历史记录
    sorted_history = []
    if status_history:
        sorted_history = sorted(status_history, key=lambda x: x.timestamp)
    
    while current_time <= end_time:
        hour = current_time.hour
        is_working_hours = 8 <= hour <= 20
        
        # 检查当前时间点的设备状态
        current_status = 'active'  # 默认状态为运行中
        
        # 找到当前时间点对应的状态
        if sorted_history:
            # 找到当前时间之前的最后一次状态变更
            relevant_history = [h for h in sorted_history if h.timestamp <= current_time]
            if relevant_history:
                current_status = relevant_history[-1].status
        
        # 根据状态和工作时间生成功率数据
        if current_status == 'active' and is_working_hours:
            power = base_power + random.uniform(-base_power * 0.1, base_power * 0.1)
        elif current_status == 'active':
            power = base_power * 0.3 + random.uniform(-base_power * 0.05, base_power * 0.05)
        else:
            # 设备关闭时功率为0
            power = 0
        
        data.append({
            'timestamp': current_time,
            'power_consumption': round(power, 2)
        })
        current_time += timedelta(minutes=5)
    
    return data

@app.route('/api/manager/device-data')
@manager_required
def get_device_data():
    db = next(get_db())
    store_id = session.get('store_id')
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    devices = db.query(Device).filter(Device.store_id == store_id).all()
    device_data = []
    
    for device in devices:
        power_data = []
        # 获取设备的创建时间
        device_created_at = device.created_at if hasattr(device, 'created_at') else today
        
        # 如果设备是今天创建的，则从创建时间开始生成数据
        start_time = max(today, device_created_at)
        current_time = start_time
        
        # 获取设备状态历史记录
        status_history = db.query(DeviceStatusHistory).filter(
            DeviceStatusHistory.device_id == device.id,
            DeviceStatusHistory.timestamp >= start_time,
            DeviceStatusHistory.timestamp <= now
        ).order_by(DeviceStatusHistory.timestamp.asc()).all()
        
        # 获取初始状态
        initial_status = db.query(DeviceStatusHistory).filter(
            DeviceStatusHistory.device_id == device.id,
            DeviceStatusHistory.timestamp < start_time
        ).order_by(DeviceStatusHistory.timestamp.desc()).first()
        
        current_status = initial_status.status if initial_status else device.status
        
        # 创建状态变更时间点的映射  
        status_changes = {h.timestamp: h.status for h in status_history}
        
        # 每5分钟生成一个数据点
        interval = timedelta(minutes=5)
        base_power = device.power_rating
        
        while current_time <= now:
            # 检查当前时间点是否有状态变更
            if current_time in status_changes:
                current_status = status_changes[current_time]
            
            # 生成功率数据
            hour = current_time.hour
            is_working_hours = 8 <= hour <= 20
            
            # 使用设备ID和时间作为随机种子
            random.seed(f"{device.id}_{current_time.timestamp()}")
            
            if current_status == 'active':
                if is_working_hours:
                    base = base_power * 0.85
                    variation = base_power * 0.05
                    power = base + random.uniform(-variation, variation)
                else:
                    base = base_power * 0.35
                    variation = base_power * 0.02
                    power = base + random.uniform(-variation, variation)
            else:
                power = 0
            
            random.seed()
            
            power_data.append([
                current_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                round(power, 2)
            ])
            
            current_time += interval
        
        device_data.append({
            'id': device.id,
            'power_data': power_data
        })
    
    return jsonify(device_data)


@app.route('/api/manager/total-energy')
@manager_required
def get_total_energy_data():
    db = next(get_db())
    try:
        period = request.args.get('period', 'day')
        accumulated = request.args.get('accumulated', 'true').lower() == 'true'
        now = datetime.now()
        store_id = session.get('store_id')
        
        # 获取该商店的所有设备
        devices = db.query(Device).filter(Device.store_id == store_id).all()
        
        # 设置时间范围和数据点间隔
        if period == 'day':
            start_time = now - timedelta(hours=24)
            interval = timedelta(minutes=5)  # 5分钟一个数据点
        elif period == 'week':
            start_time = now - timedelta(days=7)
            interval = timedelta(hours=1)  # 1小时一个数据点
        else:  # month
            start_time = now - timedelta(days=30)
            interval = timedelta(hours=4)  # 4小时一个数据点

        energy_data = []
        current_time = start_time
        accumulated_energy = 0
        
        # 创建一个单独的列表来存储非累积数据
        raw_energy_data = []
        
        while current_time <= now:
            if period == 'day':
                # 24小时视图：使用实际设备数据
                total_power = 0
                
                for device in devices:
                    # 获取设备状态
                    status_history = db.query(DeviceStatusHistory).filter(
                        DeviceStatusHistory.device_id == device.id,
                        DeviceStatusHistory.timestamp <= current_time
                    ).order_by(DeviceStatusHistory.timestamp.desc()).first()
                    
                    current_status = status_history.status if status_history else device.status
                    
                    # 使用设备ID和时间作为随机种子
                    random.seed(f"{device.id}_{current_time.timestamp()}")
                    
                    # 根据设备类型和时间段调整功率计算
                    if current_status == 'active':
                        hour = current_time.hour
                        is_working_hours = 8 <= hour <= 20
                        is_peak_hours = 10 <= hour <= 14 or 17 <= hour <= 19
                        
                        # 根据设备类型设置不同的功率模式
                        if device.device_type == "oven":
                            if is_peak_hours:  # 烤箱在用餐高峰期功率最大
                                base = device.power_rating * 0.9
                                variation = device.power_rating * 0.1
                            elif is_working_hours:  # 工作时间正常使用
                                base = device.power_rating * 0.7
                                variation = device.power_rating * 0.15
                            else:  # 非工作时间可能保温或待机
                                base = device.power_rating * 0.1
                                variation = device.power_rating * 0.05
                        
                        elif device.device_type == "refrigerator":
                            if is_peak_hours:  # 高峰期频繁开关门，制冷更频繁
                                base = device.power_rating * 0.75
                                variation = device.power_rating * 0.15
                            else:  # 其他时间相对稳定
                                base = device.power_rating * 0.6
                                variation = device.power_rating * 0.1
                        
                        else:  # mixer或其他设备
                            if is_working_hours:
                                base = device.power_rating * 0.65
                                variation = device.power_rating * 0.2
                            else:
                                base = device.power_rating * 0.1
                                variation = device.power_rating * 0.05
                        
                        power = base + random.uniform(-variation, variation)
                    else:
                        # 设备关闭时的待机功率
                        if device.device_type == "refrigerator":
                            power = device.power_rating * 0.05  # 冰箱即使关闭也需要维持基本运行
                        else:
                            power = 0
                    
                    total_power += power
                    random.seed()  # 重置随机种子
                
                # 计算这个时间间隔的能耗(kWh)
                interval_hours = interval.total_seconds() / 3600
                energy = (total_power * interval_hours) / 1000
                
            else:
                # 周视图和月视图的能耗计算
                hour = current_time.hour
                day = current_time.weekday()
                
                # 根据时间段和工作日设置基础能耗
                if 8 <= hour <= 20:  # 工作时间
                    if 10 <= hour <= 14 or 17 <= hour <= 19:  # 高峰期
                        if 0 <= day <= 4:  # 工作日
                            base_energy = random.uniform(25, 35)  # 工作日高峰期
                        else:
                            base_energy = random.uniform(30, 40)  # 周末高峰期更高
                    else:  # 非高峰工作时间
                        if 0 <= day <= 4:
                            base_energy = random.uniform(15, 20)  # 工作日平常时段
                        else:
                            base_energy = random.uniform(20, 25)  # 周末平常时段
                else:  # 非工作时间
                    base_energy = random.uniform(5, 8)  # 夜间基础能耗
                
                # 添加季节性波动（示例：夏季空调负载）
                month = current_time.month
                if 6 <= month <= 8:  # 夏季
                    base_energy *= 1.2
                elif 12 <= month or month <= 2:  # 冬季
                    base_energy *= 1.1
                
                energy = base_energy * (1 + random.uniform(-0.1, 0.1))
            
            # 存储原始非累积数据
            raw_energy_data.append([
                current_time.strftime('%Y-%m-%d %H:%M:%S'),
                round(energy, 3)  # 更高精度，因为单位时间能耗较小
            ])
            
            # 只有在需要累积数据时才执行累加
            if accumulated:
                accumulated_energy += energy
                energy_data.append([
                    current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    round(accumulated_energy, 2)
                ])
            
            current_time += interval
        
        # 根据请求参数返回对应的数据
        result_data = energy_data if accumulated else raw_energy_data
        
        return jsonify({
            'success': True,
            'energy_data': result_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/resource-center')
def resource_center():
    return render_template('resource_center.html')

@app.route('/resource-center/white-papers/<paper_id>')
def white_paper(paper_id):
    papers = {
        'sustainable-baking': {
            'title': '2024 Sustainable Baking Practice Guide',
            'publish_date': '2024-01-15',
            'author': 'Green Baking Research Team',
            'content': {
                'introduction': '随着全球对环境保护和可持续发展的关注不断加深，烘焙行业也迎来了转型的机遇和挑战。如何在确保产品质量和企业效益的同时，减少能源消耗、降低碳足迹并优化资源利用，已成为许多烘焙企业亟待解决的问题。本文将深入探讨工业烘焙中的环保实践方案，涵盖从原材料选择到生产工艺的全方位绿色转型指南，帮助烘焙企业实现可持续发展目标。',
                'sections': [
                    {
                        'title': '一、环保生产工艺创新',
                        'content': '1.1 原材料可持续采购\n在原材料采购环节，我们建议选择获得环保认证的供应商...'
                    },
                    {
                        'title': '二、能源效率优化方案',
                        'content': '2.1 智能温控系统应用\n通过引入智能温控系统，可以精确控制烘焙过程中的能源使用...'
                    }
                ]
            }
        },
        'energy-efficiency': {
            'title': '烘焙能源效率优化',
            'publish_date': '2024-02-20',
            'author': '能源管理研究中心',
            'content': {
                'introduction': '能源效率优化是降低运营成本和环境影响的关键...',
                'sections': [
                    {
                        'title': '一、能源消耗分析',
                        'content': '1.1 能源使用现状\n通过对行业内100家烘焙企业的调研，我们发现主要能耗来自以下几个方面...'
                    },
                    {
                        'title': '二、优化策略',
                        'content': '2.1 设备升级改造\n采用新一代节能设备，可显著降低能源消耗...'
                    }
                ]
            }
        }
    }
    return render_template('resource/white_paper.html', paper=papers.get(paper_id))

@app.route('/resource-center/research-reports/<report_id>')
def research_report(report_id):
    reports = {
        'carbon-footprint': {
            'title': '2023碳足迹分析',
            'publish_date': '2023-12-10',
            'author': '环境研究所',
            'content': {
                'introduction': '本报告详细分析了烘焙行业的碳排放情况...',
                'sections': [
                    {
                        'title': '一、碳排放现状',
                        'content': '1.1 排放源分析\n根据我们的研究，烘焙行业的碳排放主要来自以下几个环节...'
                    },
                    {
                        'title': '二、减排建议',
                        'content': '2.1 生产环节优化\n通过工艺改进和设备升级，可实现显著的减排效果...'
                    }
                ]
            }
        },
        'waste-reduction': {
            'title': '废弃物减量研究',
            'publish_date': '2024-01-25',
            'author': '可持续发展中心',
            'content': {
                'introduction': '废弃物管理是实现零碳目标的重要组成部分...',
                'sections': [
                    {
                        'title': '一、废弃物构成分析',
                        'content': '1.1 主要废弃物类型\n通过对生产过程的跟踪研究，我们识别出以下主要废弃物类型...'
                    },
                    {
                        'title': '二、减量化方案',
                        'content': '2.1 原材料管理优化\n通过精确的需求预测和库存管理，可以显著减少原材料浪费...'
                    }
                ]
            }
        }
    }
    return render_template('resource/research_report.html', report=reports.get(report_id))

@app.route('/resource-center/case-studies/<case_id>')
def case_study(case_id):
    cases = {
        'smart-energy': {
            'title': '智能能源管理实施案例',
            'publish_date': '2024-03-01',
            'company': '上海绿色烘焙示范工厂',
            'content': {
                'introduction': '本案例展示了如何通过智能化手段实现能源消耗的显著降低...',
                'sections': [
                    {
                        'title': '一、项目背景',
                        'content': '工厂原有能源管理系统存在效率低下等问题...'
                    },
                    {
                        'title': '二、解决方案',
                        'content': '引入智能监控系统，实现能源使用的实时监测和优化...'
                    },
                    {
                        'title': '三、实施效果',
                        'content': '项目实施后，工厂能源消耗降低40%，年节省成本超过100万元...'
                    }
                ]
            }
        },
        'zero-waste': {
            'title': '零废弃计划成果',
            'publish_date': '2024-02-15',
            'company': '北京绿色食品有限公司',
            'content': {
                'introduction': '通过系统性的废弃物管理方案，实现了生产过程的零废弃...',
                'sections': [
                    {
                        'title': '一、项目目标',
                        'content': '建立完整的废弃物管理体系，实现资源的循环利用...'
                    },
                    {
                        'title': '二、实施过程',
                        'content': '分阶段推进废弃物管理改革，包括分类收集、回收利用等...'
                    },
                    {
                        'title': '三、成果展示',
                        'content': '实现95%以上的废弃物回收利用，年度环保效益显著...'
                    }
                ]
            }
        }
    }
    return render_template('resource/case_study.html', case=cases.get(case_id))

@app.template_filter('nl2br')
def nl2br(value):
    return value.replace('\n', '<br>')


@app.route('/manager/procurement')
@manager_required
def manager_procurement():
    db = next(get_db())
    store_id = session.get('store_id')
    store = db.get(Store, store_id)

    # 获取产品列表
    products = db.query(Product).filter(Product.store_id == store_id).all()

    # 获取原材料列表
    materials = db.query(Material).filter(Material.store_id == store_id).all()

    # 获取供应商列表
    suppliers = db.query(Supplier).all()

    # 获取历史销售数据
    sales_data = db.query(
        SalesRecord.product_id,
        func.date_format(SalesRecord.sale_date, '%Y-%m').label('month'),
        func.sum(SalesRecord.quantity).label('total')
    ).filter(
        SalesRecord.store_id == store_id
    ).group_by(
        SalesRecord.product_id,
        func.date_format(SalesRecord.sale_date, '%Y-%m')
    ).all()

    # 将销售数据转换为字典格式，方便前端使用
    sales_history = {}
    for product_id, month, total in sales_data:
        if product_id not in sales_history:
            sales_history[product_id] = {}
        sales_history[product_id][month] = total

    return render_template('manager/procurement.html',
                           store=store,
                           products=products,
                           materials=materials,
                           suppliers=suppliers,
                           sales_history=sales_history)


@app.route('/api/manager/predict-procurement', methods=['POST'])
@manager_required
def predict_procurement():
    db = next(get_db())
    store_id = session.get('store_id')

    try:
        # 解析请求数据
        data = request.json
        predicted_sales = data.get('predicted_sales', {})
        use_ml_prediction = data.get('use_ml_prediction', False)
        days_to_predict = data.get('days_to_predict', 90)  # 默认预测90天

        # 将字符串键转换为整数
        sales_data = {int(product_id): int(quantity) for product_id, quantity in predicted_sales.items()}

        # 如果启用机器学习预测，使用线性回归模型
        if use_ml_prediction:
            sales_data = ProcurementService.predict_sales(db, store_id, days_to_predict)

        # 计算每种产品需要的原料
        material_needs = {}
        for product_id, quantity in sales_data.items():
            if quantity <= 0:
                continue

            product = db.get(Product, product_id)
            if not product:
                continue

            # 获取产品的配方
            recipes = db.query(Recipe).filter(Recipe.product_id == product_id).all()
            if not recipes:
                continue

            # 计算所需原料数量
            for recipe in recipes:
                material_id = recipe.material_id
                material = db.get(Material, material_id)
                if not material:
                    continue

                required_amount = recipe.amount * float(quantity)

                if material_id not in material_needs:
                    material_needs[material_id] = {
                        'name': material.name,
                        'amount': 0,
                        'unit': material.unit,
                        'current_stock': material.current_stock
                    }

                material_needs[material_id]['amount'] += required_amount

        # 为每种需要采购的原料找到最佳供应商
        result = {
            'materials': [],
            'total_cost': 0,
            'total_amount': 0,
            'total_carbon_emission': 0
        }

        for material_id, material_data in material_needs.items():
            material = db.get(Material, material_id)
            if not material:
                continue

            # 获取材料的所有供应商价格
            prices = db.query(MaterialPrice).filter(
                MaterialPrice.material_id == material_id
            ).order_by(
                MaterialPrice.effective_date.desc()
            ).all()

            # 选择综合评分最高的供应商
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
                    # 计算需要采购的数量（减去库存）
                    purchase_amount = max(0, material_data['amount'] - material_data['current_stock'])

                    # 计算碳排放等级
                    carbon_level = 'low'
                    if best_supplier.carbon_emission > 30:
                        carbon_level = 'high'
                    elif best_supplier.carbon_emission > 10:
                        carbon_level = 'medium'

                    # 添加到结果中
                    material_info = {
                        'name': material.name,
                        'amount': round(purchase_amount, 2),
                        'unit': material.unit,
                        'price': round(best_supplier.price, 2),
                        'carbon_emission': round(best_supplier.carbon_emission, 2),
                        'carbon_level': carbon_level,
                        'supplier': supplier.name
                    }

                    result['materials'].append(material_info)
                    result['total_cost'] += best_supplier.price * purchase_amount
                    result['total_amount'] += purchase_amount
                    result['total_carbon_emission'] += best_supplier.carbon_emission * purchase_amount

        # 计算总体碳排放等级
        if result['total_carbon_emission'] > 0:
            avg_carbon_emission = result['total_carbon_emission'] / len(result['materials']) if result[
                'materials'] else 0
            if avg_carbon_emission <= 10:
                result['total_carbon_level'] = 'low'
            elif avg_carbon_emission <= 30:
                result['total_carbon_level'] = 'medium'
            else:
                result['total_carbon_level'] = 'high'
        else:
            result['total_carbon_level'] = 'low'

        # 四舍五入总数值
        result['total_cost'] = round(result['total_cost'], 2)
        result['total_amount'] = round(result['total_amount'], 2)
        result['total_carbon_emission'] = round(result['total_carbon_emission'], 2)

        # 添加销售预测数据
        result['predictions'] = {}
        for product_id, quantity in sales_data.items():
            product = db.get(Product, product_id)
            if product:
                result['predictions'][product_id] = {
                    'name': product.name,
                    'quantity': quantity
                }

        # 添加历史销售记录数据
        result['sales_history'] = {}

        # 获取过去12个月的销售数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        sales_history = db.query(
            Product.id.label('product_id'),
            Product.name.label('product_name'),
            func.extract('month', SalesRecord.sale_date).label('month'),
            func.sum(SalesRecord.quantity).label('quantity')
        ).join(
            SalesRecord, Product.id == SalesRecord.product_id
        ).filter(
            Product.store_id == store_id,
            SalesRecord.sale_date.between(start_date, end_date)
        ).group_by(
            Product.id,
            Product.name,
            func.extract('month', SalesRecord.sale_date)
        ).all()

        # 整理数据为表格格式
        for record in sales_history:
            product_id = record.product_id
            if product_id not in result['sales_history']:
                result['sales_history'][product_id] = {
                    'name': record.product_name,
                    'monthly_sales': [0] * 12  # 12个月的数据
                }

            # 月份从1开始，数组索引从0开始
            month_index = int(record.month) - 1
            if 0 <= month_index < 12:
                result['sales_history'][product_id]['monthly_sales'][month_index] = record.quantity

        return jsonify(result)

    except Exception as e:
        print(f"Error in predict_procurement: {str(e)}")
        return jsonify({
            'error': f"计算采购方案时出错: {str(e)}"
        }), 500


@app.route('/manager/procurement/simulate', methods=['GET', 'POST'])
@manager_required
def simulate_procurement():
    db = next(get_db())
    store_id = session.get('store_id')
    store = db.get(Store, store_id)

    # 为演示生成模拟数据
    if request.method == 'POST':
        # 这里可以接收用户选择的参数进行真实预测
        return redirect(url_for('manager_procurement_result'))

    # 获取产品和原料数据
    products = db.query(Product).filter(Product.store_id == store_id).all()
    materials = db.query(Material).filter(Material.store_id == store_id).all()

    return render_template('manager/procurement_simulate.html',
                           store=store,
                           products=products,
                           materials=materials)


@app.route('/manager/procurement/result')
@manager_required
def manager_procurement_result():
    db = next(get_db())
    store_id = session.get('store_id')
    store = db.get(Store, store_id)

    # 模拟数据 - 在实际实现中这些数据将由预测算法生成
    # 预计销售数据
    products = db.query(Product).filter(Product.store_id == store_id).all()
    product_sales = {product.id: random.randint(20, 100) for product in products}

    # 调用预测API
    prediction_result = {}
    materials_needed = {}
    suppliers_plan = {}
    total_cost = 0

    # 模拟调用预测API的结果
    try:
        # 在生产环境中，这里应该调用真实的预测API
        response = predict_procurement()
        if isinstance(response, tuple):
            prediction_data = response[0].json
        else:
            prediction_data = response.json

        # 从API响应中提取数据
        prediction_result = prediction_data.get('predictions', {})
        materials_needed = prediction_data.get('materials', {})
        suppliers_plan = prediction_data.get('purchase_plan', {})
        total_cost = prediction_data.get('total_cost', 0)
    except Exception as e:
        flash(f'预测失败：{str(e)}')
        prediction_result = {}

    return render_template('manager/procurement_result.html',
                           store=store,
                           products=products,
                           product_sales=product_sales,
                           prediction_result=prediction_result,
                           materials_needed=materials_needed,
                           suppliers_plan=suppliers_plan,
                           total_cost=total_cost)


@app.route('/manager/sales/add', methods=['POST'])
@manager_required
def manager_add_sales():
    db = next(get_db())
    store_id = session.get('store_id')

    if request.method == 'POST':
        try:
            product_id = request.form.get('product')
            quantity = request.form.get('quantity')
            sale_date = request.form.get('sale_date')

            if not product_id or not quantity or not sale_date:
                flash('请填写所有必填字段')
                return redirect(url_for('manager_inventory'))

            # 创建销售记录
            new_sale = SalesRecord(
                product_id=product_id,
                store_id=store_id,
                quantity=int(quantity),
                sale_date=datetime.strptime(sale_date, '%Y-%m-%d'),
                created_at=datetime.now()
            )

            db.add(new_sale)
            db.commit()

            flash('销售数据添加成功')
        except Exception as e:
            db.rollback()
            print(f"Error adding sales record: {str(e)}")
            flash('添加销售数据失败，请稍后重试')

    return redirect(url_for('manager_inventory'))


@app.route('/manager/sales/delete/<int:record_id>', methods=['POST'])
@manager_required
def manager_delete_sales(record_id):
    db = next(get_db())
    store_id = session.get('store_id')

    try:
        # 查找销售记录
        sales_record = db.query(SalesRecord).filter(
            SalesRecord.id == record_id,
            SalesRecord.store_id == store_id
        ).first()

        if not sales_record:
            return jsonify({'success': False, 'message': '未找到销售记录'}), 404

        # 删除记录
        db.delete(sales_record)
        db.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        print(f"Error deleting sales record: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/manager/sales/<int:record_id>', methods=['GET'])
@manager_required
def manager_get_sales(record_id):
    db = next(get_db())
    store_id = session.get('store_id')

    try:
        # 查找销售记录
        record = db.query(
            SalesRecord.id,
            SalesRecord.product_id,
            Product.name.label('product_name'),
            SalesRecord.quantity,
            SalesRecord.sale_date
        ).join(
            Product, SalesRecord.product_id == Product.id
        ).filter(
            SalesRecord.id == record_id,
            SalesRecord.store_id == store_id
        ).first()

        if not record:
            return jsonify({'success': False, 'message': '未找到销售记录'}), 404

        # 返回记录详情
        return jsonify({
            'success': True,
            'record': {
                'id': record.id,
                'product_id': record.product_id,
                'product_name': record.product_name,
                'quantity': record.quantity,
                'sale_date': record.sale_date.strftime('%Y-%m-%d')
            }
        })
    except Exception as e:
        print(f"Error getting sales record: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/manager/sales/edit/<int:record_id>', methods=['POST'])
@manager_required
def manager_edit_sales(record_id):
    db = next(get_db())
    store_id = session.get('store_id')

    try:
        # 查找销售记录
        sales_record = db.query(SalesRecord).filter(
            SalesRecord.id == record_id,
            SalesRecord.store_id == store_id
        ).first()

        if not sales_record:
            return jsonify({'success': False, 'message': '未找到销售记录'}), 404

        # 更新记录
        product_id = request.form.get('edit_product')
        quantity = request.form.get('edit_quantity')
        sale_date = request.form.get('edit_sale_date')

        if not product_id or not quantity or not sale_date:
            return jsonify({'success': False, 'message': '请填写所有必填字段'}), 400

        sales_record.product_id = product_id
        sales_record.quantity = int(quantity)
        sales_record.sale_date = datetime.strptime(sale_date, '%Y-%m-%d')

        db.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        print(f"Error updating sales record: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/manager/inventory-prediction')
@manager_required
def get_inventory_prediction():
    """生成未来3天的原材料需求预测"""
    db = next(get_db())
    store_id = session.get('store_id')

    try:
        # 获取该商店的所有原材料
        materials = db.query(Material).filter(Material.store_id == store_id).all()

        # 如果没有原材料数据，返回空列表
        if not materials:
            print("No materials found for store_id:", store_id)
            return jsonify([])

        # 获取最近30天的销售记录数据，用于预测
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # 查询销售数据
        sales_data = db.query(
            SalesRecord.product_id,
            func.sum(SalesRecord.quantity).label('total_quantity')
        ).filter(
            SalesRecord.store_id == store_id,
            SalesRecord.sale_date.between(start_date, end_date)
        ).group_by(
            SalesRecord.product_id
        ).all()

        # 如果没有销售数据，返回默认预测
        if not sales_data:
            print("No sales data found for prediction")
            result = []
            for material in materials:
                # 默认预测值（每种原料每天5个单位）
                predictions = [5, 5, 5]  # 简单的默认值
                result.append({
                    'material': material.name,
                    'unit': material.unit,
                    'predictions': predictions
                })
            return jsonify(result)

        # 获取产品配方
        product_recipes = {}
        for product_id, total_quantity in sales_data:
            recipes = db.query(Recipe).filter(Recipe.product_id == product_id).all()
            if recipes:
                product_recipes[product_id] = {
                    'sales': total_quantity,
                    'recipes': recipes
                }

        # 如果没有配方数据，返回默认预测
        if not product_recipes:
            print("No recipe data found for products")
            result = []
            for material in materials:
                # 默认预测值
                predictions = [5, 5, 5]  # 简单的默认值
                result.append({
                    'material': material.name,
                    'unit': material.unit,
                    'predictions': predictions
                })
            return jsonify(result)

        # 计算每天的平均销售量
        days = (end_date - start_date).days or 1  # 避免除以零

        # 计算材料的每日平均需求
        material_daily_usage = {}
        for product_id, data in product_recipes.items():
            daily_sales = data['sales'] / days

            for recipe in data['recipes']:
                material_id = recipe.material_id
                # 确保recipe.amount是有效的数字
                try:
                    amount = float(recipe.amount)
                except (ValueError, TypeError):
                    print(f"Invalid amount in recipe: {recipe.id}, using default value 1.0")
                    amount = 1.0

                # 确保daily_sales是float类型
                daily_sales = float(daily_sales)

                daily_material_usage = daily_sales * amount

                if material_id not in material_daily_usage:
                    material_daily_usage[material_id] = 0

                material_daily_usage[material_id] += daily_material_usage

        # 生成未来3天的预测
        result = []
        for material in materials:
            daily_usage = material_daily_usage.get(material.id, 0)

            # 预测未来3天的需求（包含一些随机波动）
            predictions = []
            for i in range(3):
                # 添加一些随机波动 (±20%)
                variation = random.uniform(-0.2, 0.2)
                predicted_usage = daily_usage * (1 + variation)
                predictions.append(round(predicted_usage, 2))

            result.append({
                'material': material.name,
                'unit': material.unit,
                'predictions': predictions
            })

        return jsonify(result)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in inventory prediction: {str(e)}")
        print(f"Detailed error: {error_details}")

        # 发生错误时返回默认数据
        try:
            result = []
            # 尝试返回所有原料的默认预测
            if 'materials' in locals() and materials:
                for material in materials:
                    result.append({
                        'material': material.name,
                        'unit': material.unit,
                        'predictions': [5, 5, 5]  # 默认预测值
                    })
            return jsonify(result)
        except:
            # 如果无法创建默认数据，则返回空列表
            return jsonify([])


@app.route('/manager/chart_test')
@manager_required
def chart_test():
    """测试图表页面"""
    return render_template('manager/chart_test.html')


# 添加供应商和价格API
@app.route('/api/manager/suppliers')
@manager_required
def get_suppliers():
    """获取供应商和原料价格数据"""
    db = next(get_db())
    store_id = session.get('store_id')

    try:
        # 获取该商店的所有原材料
        materials = db.query(Material).filter(Material.store_id == store_id).all()

        # 获取所有供应商
        suppliers = db.query(Supplier).all()

        # 获取原料价格
        result = {}

        for material in materials:
            # 获取该原料的所有价格记录
            prices = db.query(MaterialPrice).filter(
                MaterialPrice.material_id == material.id
            ).all()

            # 按供应商组织价格数据
            material_suppliers = []
            for price in prices:
                supplier = db.query(Supplier).filter(Supplier.id == price.supplier_id).first()
                if supplier:
                    material_suppliers.append({
                        'supplier_id': supplier.id,
                        'name': supplier.name,
                        'price': price.price,
                        'emission': price.carbon_emission,
                        'rating': supplier.carbon_footprint_rating
                    })

            # 如果没有找到供应商，添加默认供应商
            if not material_suppliers:
                for supplier in suppliers[:3]:  # 使用前3个供应商作为默认
                    material_suppliers.append({
                        'supplier_id': supplier.id,
                        'name': supplier.name,
                        'price': 10.0,  # 默认价格
                        'emission': 1.0,  # 默认碳排放
                        'rating': supplier.carbon_footprint_rating
                    })

            # 添加到结果
            result[material.name] = {
                'material_id': material.id,
                'name': material.name,
                'unit': material.unit,
                'suppliers': material_suppliers
            }

        return jsonify(result)

    except Exception as e:
        print(f"Error in getting suppliers: {str(e)}")
        return jsonify({}), 500


@app.route('/api/procurement-plan')
@manager_required
def get_procurement_plan():
    """获取采购方案"""
    db = next(get_db())
    store_id = session.get('store_id')

    try:
        # 获取预测数据
        prediction_response = get_inventory_prediction()
        prediction_data = prediction_response.json

        if not prediction_data:
            return jsonify([])

        # 获取供应商数据
        suppliers = db.query(Supplier).all()
        suppliers_dict = {}

        # 整理供应商数据
        for supplier in suppliers:
            prices = db.query(MaterialPrice).filter(
                MaterialPrice.supplier_id == supplier.id
            ).all()

            for price in prices:
                material = db.get(Material, price.material_id)
                if not material:
                    continue

                if material.name not in suppliers_dict:
                    suppliers_dict[material.name] = []

                suppliers_dict[material.name].append({
                    'name': supplier.name,
                    'price': round(price.price, 2),
                    'emission': round(price.carbon_emission, 2)
                })

        # 处理每种材料的采购建议
        result = []
        for item in prediction_data:
            material_name = item['material']
            # 确保predictions中的值是数字并求和
            total_demand = sum(float(p) for p in item['predictions'])  # 3天总需求
            total_demand = round(total_demand, 2)  # 四舍五入保留两位小数

            # 获取该材料的供应商信息
            material_suppliers = suppliers_dict.get(material_name, [])

            # 选择最佳供应商（考虑价格和碳排放）
            best_supplier = None
            best_score = float('inf')

            for supplier in material_suppliers:
                # 综合评分（价格权重0.6，碳排放权重0.4）
                score = (supplier['price'] * 0.6) + (supplier['emission'] * 0.4)
                if score < best_score:
                    best_score = score
                    best_supplier = supplier

            # 如果没有找到供应商，使用默认值
            if not best_supplier:
                best_supplier = {
                    'name': f'{material_name}供应商A',
                    'price': 100.00,
                    'emission': 10.00
                }

            # 计算成本和碳排放（保留两位小数）
            cost = round(best_supplier['price'] * total_demand, 2)
            emission = round(best_supplier['emission'] * total_demand, 2)

            result.append({
                'material': material_name,
                'quantity': total_demand,
                'unit': item['unit'],
                'cost': cost,
                'emission': emission,
                'supplier': best_supplier['name']
            })

        return jsonify(result)

    except Exception as e:
        print(f"Error in get_procurement_plan: {str(e)}")
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)