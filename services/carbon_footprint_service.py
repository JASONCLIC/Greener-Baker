import os
import qrcode
from datetime import datetime
from sqlalchemy.orm import Session
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from models import Product, Recipe, MaterialPrice, DeviceData, BatchCarbonFootprint, Material, Supplier, Device

class CarbonFootprintService:
    @staticmethod
    def calculate_product_carbon_footprint(db: Session, product_id: int, quantity: int, store_id: int):
        """
        计算产品的碳足迹
        
        Args:
            db: 数据库会话
            product_id: 产品ID
            quantity: 生产数量
            store_id: 店铺ID
            
        Returns:
            BatchCarbonFootprint对象
        """
        # 获取产品信息
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")
        
        # 获取产品配方
        recipes = db.query(Recipe).filter(Recipe.product_id == product_id).all()
        if not recipes:
            raise ValueError(f"No recipe found for product {product.name}")
        
        # 计算原材料碳排放
        materials_emission = 0.0
        for recipe in recipes:
            # 获取每种原料的最新价格和碳排放数据
            material_price = db.query(MaterialPrice).filter(
                MaterialPrice.material_id == recipe.material_id
            ).order_by(MaterialPrice.effective_date.desc()).first()
            
            if material_price:
                # 计算该原料的总碳排放
                material_emission = material_price.carbon_emission * recipe.amount * quantity
                materials_emission += material_emission
        
        # 计算生产过程碳排放 (基于设备耗电)
        # 获取店铺中的烤箱设备
        devices = db.query(Device).filter(
            Device.store_id == store_id,
            Device.device_type == 'oven'  # 假设烤箱是主要的产品生产设备
        ).all()
        
        # 估算生产能耗 (kWh) - 这里使用一个简单的模型
        # 实际应用中应该根据设备规格和生产时间计算
        production_emission = 0.0
        avg_power_kwh = 0
        
        if devices:
            # 获取设备的平均能耗数据
            for device in devices:
                device_data = db.query(DeviceData).filter(
                    DeviceData.device_id == device.id
                ).order_by(DeviceData.timestamp.desc()).limit(10).all()
                
                if device_data:
                    # 计算平均功率 (W) 并转换为kWh
                    avg_power = sum(data.power_consumption for data in device_data) / len(device_data)
                    # 假设每个产品需要烘焙30分钟，转换为小时
                    avg_power_kwh = (avg_power / 1000) * (30/60)
            
            # 使用碳排放因子 (每kWh电力产生0.4kg CO2)
            # 这个因子应该基于当地电网的碳强度
            carbon_factor = 0.4  # kg CO2/kWh
            
            # 计算生产能耗的碳排放
            production_emission = avg_power_kwh * quantity * carbon_factor
        
        # 计算总碳排放和单位产品碳排放
        total_emission = materials_emission + production_emission
        per_unit_emission = total_emission / quantity if quantity > 0 else 0
        
        # 创建并保存碳足迹记录
        batch_footprint = BatchCarbonFootprint(
            product_id=product_id,
            store_id=store_id,
            batch_date=datetime.now(),
            quantity=quantity,
            materials_emission=round(materials_emission, 2),
            production_emission=round(production_emission, 2),
            total_emission=round(total_emission, 2),
            per_unit_emission=round(per_unit_emission, 2)
        )
        
        db.add(batch_footprint)
        db.commit()
        db.refresh(batch_footprint)
        
        # 生成QR码和报告
        CarbonFootprintService.generate_qr_code(db, batch_footprint)
        CarbonFootprintService.generate_carbon_report(db, batch_footprint)
        
        return batch_footprint
    
    @staticmethod
    def generate_qr_code(db: Session, batch_footprint: BatchCarbonFootprint):
        """
        为碳足迹报告生成QR码
        
        Args:
            db: 数据库会话
            batch_footprint: 批次碳足迹对象
        """
        # 确保存储路径存在
        qr_directory = os.path.join('static', 'carbon_reports', 'qr_codes')
        os.makedirs(qr_directory, exist_ok=True)
        
        # QR码内容 - 这会是一个URL，指向碳足迹报告页面
        report_url = f"http://example.com/carbon-report/{batch_footprint.id}"
        
        # 生成QR码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(report_url)
        qr.make(fit=True)
        
        # 创建QR码图像
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # 保存QR码图像
        qr_filename = f"carbon_qr_{batch_footprint.id}.png"
        qr_path = os.path.join(qr_directory, qr_filename)
        qr_img.save(qr_path)
        
        # 更新数据库中的QR码路径
        relative_path = os.path.join('carbon_reports', 'qr_codes', qr_filename)
        batch_footprint.qr_code_path = relative_path
        db.commit()
    
    @staticmethod
    def generate_carbon_report(db: Session, batch_footprint: BatchCarbonFootprint):
        """
        生成PDF格式的碳足迹报告
        
        Args:
            db: 数据库会话
            batch_footprint: 批次碳足迹对象
        """
        # 获取相关数据
        product = db.query(Product).filter(Product.id == batch_footprint.product_id).first()
        if not product:
            raise ValueError(f"Product with ID {batch_footprint.product_id} not found")
        
        # 确保报告目录存在
        report_directory = os.path.join('static', 'carbon_reports', 'pdf')
        os.makedirs(report_directory, exist_ok=True)
        
        # 报告文件名
        report_filename = f"carbon_report_{batch_footprint.id}.pdf"
        report_path = os.path.join(report_directory, report_filename)
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            report_path,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        # 准备样式
        styles = getSampleStyleSheet()
        
        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#388E3C'),
            spaceAfter=20,
            alignment=1,  # 居中
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#757575'),
            spaceAfter=30,
            alignment=1,  # 居中
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#388E3C'),
            spaceBefore=20,
            spaceAfter=10,
            borderPadding=(0, 0, 5, 0),  # 底边padding
            borderWidth=0,
            borderColor=colors.HexColor('#4CAF50'),
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#4CAF50'),
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=8,
            textColor=colors.HexColor('#212121'),
            fontName='Helvetica'
        )
        
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=normal_style,
            fontSize=11,
            textColor=colors.HexColor('#424242'),
            spaceBefore=2,
            spaceAfter=2,
            fontName='Helvetica'
        )
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=normal_style,
            fontSize=9,
            textColor=colors.HexColor('#9E9E9E'),
            alignment=1,  # 居中
            fontName='Helvetica'
        )
        
        # 准备文档内容
        content = []
        
        # 添加logo (如果有)
        logo_path = os.path.join('static', 'images', 'eco-logo.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=80, height=80)
            logo.hAlign = 'CENTER'
            content.append(logo)
            content.append(Spacer(1, 15))
        
        # 添加标题和说明
        content.append(Paragraph("绿色烘焙碳足迹报告", title_style))
        content.append(Paragraph("我们致力于透明地展示我们的环境影响，并不断努力减少碳足迹", subtitle_style))
        
        # 绘制分隔线 (使用Table代替HorizontalLine)
        content.append(Spacer(1, 10))
        separator_table = Table([['']],
                              colWidths=[doc.width],
                              rowHeights=[1])
        separator_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#C8E6C9')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        content.append(separator_table)
        content.append(Spacer(1, 15))
        
        # 产品和批次信息区块
        info_table_data = [
            [Paragraph("<b>产品名称:</b>", info_style), Paragraph(product.name, info_style)],
            [Paragraph("<b>生产日期:</b>", info_style), Paragraph(batch_footprint.batch_date.strftime('%Y-%m-%d'), info_style)],
            [Paragraph("<b>生产数量:</b>", info_style), Paragraph(f"{batch_footprint.quantity} {product.unit}", info_style)],
            [Paragraph("<b>报告生成日期:</b>", info_style), Paragraph(batch_footprint.created_at.strftime('%Y-%m-%d'), info_style)]
        ]
        
        info_table = Table(info_table_data, colWidths=[120, 350])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        content.append(info_table)
        
        # 添加碳足迹摘要标题
        content.append(Spacer(1, 25))
        content.append(Paragraph("碳足迹摘要", heading_style))
        content.append(Spacer(1, 10))
        
        # 碳足迹数据表格
        data = [
            ["类别", "碳排放量 (kg CO₂)"],
            ["原材料", f"{batch_footprint.materials_emission}"],
            ["生产过程", f"{batch_footprint.production_emission}"],
            ["总排放量", f"{batch_footprint.total_emission}"],
            ["单位产品排放量", f"{batch_footprint.per_unit_emission}"]
        ]
        
        # 创建表格
        table = Table(data, colWidths=[220, 180])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#F1F8E9')),
            ('BACKGROUND', (1, 1), (1, -2), colors.HexColor('#F9FBF7')),
            ('BACKGROUND', (1, -1), (1, -1), colors.HexColor('#E8F5E9')),
            ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, -1), (1, -1), 12),
            ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#388E3C')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
        ]))
        
        content.append(table)
        
        # 添加饼图
        content.append(Spacer(1, 30))
        content.append(Paragraph("碳排放来源分布", subheading_style))
        
        # 创建饼图
        plt.figure(figsize=(6, 5))
        plt.clf()
        
        # 设置颜色主题
        colors_palette = ['#4CAF50', '#00BCD4']
        
        # 数据和标签
        sizes = [batch_footprint.materials_emission, batch_footprint.production_emission]
        labels = ['原材料碳排放', '生产过程碳排放']
        
        # 计算百分比
        total = sum(sizes)
        percentages = [round((size/total)*100, 1) for size in sizes]
        
        # 添加百分比到标签
        labels = [f'{label}\n({percentage}%)' for label, percentage in zip(labels, percentages)]
        
        # 创建饼图
        wedges, texts = plt.pie(sizes, labels=None, colors=colors_palette,
                  autopct='%1.1f%%', shadow=False, startangle=90,
                  wedgeprops={'edgecolor': 'white', 'linewidth': 1})
        
        # 确保圆形图
        plt.axis('equal')
        
        # 添加图例
        plt.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5))
        
        # 饼图保存路径
        chart_directory = os.path.join('static', 'carbon_reports', 'charts')
        os.makedirs(chart_directory, exist_ok=True)
        chart_filename = f"carbon_chart_{batch_footprint.id}.png"
        chart_path = os.path.join(chart_directory, chart_filename)
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # 添加图表到PDF
        chart_image = Image(chart_path, width=350, height=250)
        chart_image.hAlign = 'CENTER'
        content.append(chart_image)
        
        # 材料明细标题
        content.append(Spacer(1, 30))
        content.append(Paragraph("原材料碳排放明细", heading_style))
        content.append(Spacer(1, 5))
        content.append(Paragraph("我们产品生产过程中使用的各种原材料及其对应的碳排放信息", normal_style))
        
        # 获取产品配方和原料碳排放数据
        recipes = db.query(Recipe).filter(Recipe.product_id == product.id).all()
        material_data = [["原料名称", "使用量", "碳排放系数", "碳排放量 (kg CO₂)"]]
        
        for recipe in recipes:
            material = db.query(Material).filter(Material.id == recipe.material_id).first()
            if not material:
                continue
                
            material_price = db.query(MaterialPrice).filter(
                MaterialPrice.material_id == recipe.material_id
            ).order_by(MaterialPrice.effective_date.desc()).first()
            
            if material_price:
                material_emission = material_price.carbon_emission * recipe.amount * batch_footprint.quantity
                material_data.append([
                    material.name,
                    f"{recipe.amount * batch_footprint.quantity} {material.unit}",
                    f"{material_price.carbon_emission} kg CO₂/{material.unit}",
                    f"{round(material_emission, 2)}"
                ])
        
        # 创建原料表格
        if len(material_data) > 1:
            material_table = Table(material_data, colWidths=[100, 110, 150, 100])
            material_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FBF7')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F9FBF7'), colors.HexColor('#F1F8E9')]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 1), (3, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
            ]))
            content.append(material_table)
        
        # 添加二维码
        if batch_footprint.qr_code_path:
            content.append(Spacer(1, 40))
            qr_info = Paragraph("扫描以下二维码分享这份碳足迹报告", info_style)
            qr_info.alignment = 1  # 居中
            content.append(qr_info)
            
            qr_path = os.path.join('static', batch_footprint.qr_code_path)
            if os.path.exists(qr_path):
                qr_img = Image(qr_path, width=120, height=120)
                qr_img.hAlign = 'CENTER'
                content.append(qr_img)
        
        # 添加页脚
        content.append(Spacer(1, 40))
        footer_text = Paragraph(f"绿色烘焙 · 碳足迹报告 #{batch_footprint.id} · 生成于 {batch_footprint.created_at.strftime('%Y-%m-%d')}", footer_style)
        content.append(footer_text)
        
        # 生成PDF
        doc.build(content)
        
        # 更新数据库中的报告路径
        relative_path = os.path.join('carbon_reports', 'pdf', report_filename)
        batch_footprint.report_path = relative_path
        db.commit()
    
    @staticmethod
    def get_all_carbon_footprints(db: Session, store_id: int = None):
        """
        获取所有碳足迹报告
        
        Args:
            db: 数据库会话
            store_id: 可选的店铺ID过滤
            
        Returns:
            碳足迹报告列表
        """
        query = db.query(BatchCarbonFootprint).join(
            Product, BatchCarbonFootprint.product_id == Product.id
        )
        
        if store_id:
            query = query.filter(BatchCarbonFootprint.store_id == store_id)
            
        return query.order_by(BatchCarbonFootprint.batch_date.desc()).all()
    
    @staticmethod
    def get_carbon_footprint_by_id(db: Session, report_id: int):
        """
        通过ID获取碳足迹报告
        
        Args:
            db: 数据库会话
            report_id: 报告ID
            
        Returns:
            碳足迹报告对象
        """
        return db.query(BatchCarbonFootprint).join(
            Product, BatchCarbonFootprint.product_id == Product.id
        ).filter(BatchCarbonFootprint.id == report_id).first()
    
    @staticmethod
    def generate_report_files(db: Session, report_id: int):
        """
        生成碳足迹报告的二维码和PDF文件
        
        Args:
            db: 数据库会话
            report_id: 报告ID
            
        Returns:
            (qr_code_path, report_path): 二维码路径和报告路径的元组
        """
        # 获取碳足迹报告
        report = CarbonFootprintService.get_carbon_footprint_by_id(db, report_id)
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")
        
        # 创建二维码
        qr_directory = os.path.join('static', 'carbon_reports', 'qr')
        os.makedirs(qr_directory, exist_ok=True)
        
        # 二维码内容 - 访问报告的URL
        report_url = f"http://localhost:5000/carbon-report/{report_id}"
        
        # 创建二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(report_url)
        qr.make(fit=True)
        
        # 创建图像
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # 保存二维码
        qr_filename = f"carbon_qr_{report_id}.png"
        qr_path = os.path.join(qr_directory, qr_filename)
        qr_img.save(qr_path)
        
        # 保存二维码相对路径
        relative_qr_path = os.path.join('carbon_reports', 'qr', qr_filename)
        report.qr_code_path = relative_qr_path
        db.commit()
        
        # 生成PDF报告
        try:
            CarbonFootprintService.generate_carbon_report(db, report)
            
            # 返回路径元组
            return relative_qr_path, report.report_path
        except Exception as e:
            print(f"Error generating carbon report: {str(e)}")
            # 即使报告生成失败，也返回二维码路径和None
            return relative_qr_path, None 