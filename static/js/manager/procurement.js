document.addEventListener('DOMContentLoaded', function() {
    const autoPredictBtn = document.getElementById('auto-predict');
    const predictBtn = document.getElementById('predict-procurement');
    const predictionForm = document.getElementById('prediction-form');
    const predictionResults = document.getElementById('prediction-results');
    const salesHistoryTable = document.getElementById('sales-history-table');
    
    // 自动预测功能 - 使用机器学习模型
    autoPredictBtn.addEventListener('click', function() {
        // 显示加载提示
        const loadingMsg = document.createElement('div');
        loadingMsg.id = 'loading-message';
        loadingMsg.className = 'loading-message';
        loadingMsg.textContent = 'Analyzing historical data using linear regression model...';
        document.querySelector('.prediction-form-container').appendChild(loadingMsg);
        
        // 发送API请求，使用机器学习模型预测
        fetch('/api/manager/predict-procurement', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                predicted_sales: {},  // 空对象，表示使用模型预测
                use_ml_prediction: true,  // 启用机器学习预测
                days_to_predict: 90  // 预测未来90天（约3个月）
            })
        })
        .then(response => response.json())
        .then(data => {
            // 移除加载提示
            const loadingMsg = document.getElementById('loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }
            
            // 如果有错误
            if (data.error) {
                alert('Prediction failed: ' + data.error);
                return;
            }
            
            // 更新表单输入值
            const inputs = predictionForm.querySelectorAll('input');
            inputs.forEach(input => {
                const productId = input.id.split('-')[1];
                if (data.predictions[productId]) {
                    input.value = data.predictions[productId].quantity;
                } else {
                    input.value = 0;
                }
            });
            
            // 展示预测结果
            displayResults(data);
            
            // 更新历史销售数据表格
            if (salesHistoryTable && data.sales_history) {
                updateSalesHistoryTable(data.sales_history);
            }
        })
        .catch(error => {
            // 移除加载提示
            const loadingMsg = document.getElementById('loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }
            
            console.error('Error:', error);
            alert('An error occurred during prediction, please try again later');
        });
    });
    
    // 计算采购方案
    predictBtn.addEventListener('click', function() {
        // 收集表单数据
        const formData = {};
        const inputs = predictionForm.querySelectorAll('input');
        inputs.forEach(input => {
            const productId = input.id.split('-')[1];
            formData[productId] = input.value;
        });
        
        // 显示加载提示
        const loadingMsg = document.createElement('div');
        loadingMsg.id = 'loading-message';
        loadingMsg.className = 'loading-message';
        loadingMsg.textContent = 'Calculating optimal procurement plan...';
        document.querySelector('.prediction-form-container').appendChild(loadingMsg);
        
        // 发送API请求
        fetch('/api/manager/predict-procurement', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                predicted_sales: formData,
                use_ml_prediction: false  // 使用用户输入的预测
            })
        })
        .then(response => response.json())
        .then(data => {
            // 移除加载提示
            const loadingMsg = document.getElementById('loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }
            
            // 如果有错误
            if (data.error) {
                alert('Calculation failed: ' + data.error);
                return;
            }
            
            // 展示预测结果
            displayResults(data);
            
            // 更新历史销售数据表格
            if (salesHistoryTable && data.sales_history) {
                updateSalesHistoryTable(data.sales_history);
            }
        })
        .catch(error => {
            // 移除加载提示
            const loadingMsg = document.getElementById('loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }
            
            console.error('Error:', error);
            alert('An error occurred during calculation, please try again later');
        });
    });
    
    // 更新历史销售数据表格
    function updateSalesHistoryTable(salesHistory) {
        // 创建表头
        const thead = salesHistoryTable.querySelector('thead');
        thead.innerHTML = '';
        const headerRow = document.createElement('tr');
        
        // 添加月份列
        const monthTh = document.createElement('th');
        monthTh.textContent = 'Month';
        headerRow.appendChild(monthTh);
        
        // 添加产品列
        for (const productId in salesHistory) {
            const productTh = document.createElement('th');
            productTh.textContent = salesHistory[productId].name;
            headerRow.appendChild(productTh);
        }
        
        thead.appendChild(headerRow);
        
        // 创建表格内容
        const tbody = salesHistoryTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        // 月份名称
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        // 每个月一行
        for (let i = 0; i < 12; i++) {
            const row = document.createElement('tr');
            
            // 月份
            const monthTd = document.createElement('td');
            monthTd.textContent = monthNames[i];
            row.appendChild(monthTd);
            
            // 每个产品的销售量
            for (const productId in salesHistory) {
                const salesTd = document.createElement('td');
                salesTd.textContent = salesHistory[productId].monthly_sales[i];
                row.appendChild(salesTd);
            }
            
            tbody.appendChild(row);
        }
    }
    
    // 显示预测结果
    function displayResults(data) {
        // 显示结果区域
        predictionResults.style.display = 'block';
        
        // 1. 更新推荐采购方案
        const recommendationGrid = document.querySelector('.recommendation-grid');
        recommendationGrid.innerHTML = ''; // 清空现有内容
        
        // 添加每个材料的推荐卡片
        for (const material of data.materials) {
            const materialCard = document.createElement('div');
            materialCard.className = 'recommendation-item';
            materialCard.innerHTML = `
                <div class="material-info">
                    <div class="material-name">${material.name}</div>
                    <div class="material-details">
                        Required Amount: ${material.amount} ${material.unit}
                    </div>
                </div>
                <div class="supplier-info">
                    <div class="price">¥${material.price}/${material.unit}</div>
                    <div class="carbon-rating">
                        <span class="carbon-indicator carbon-${material.carbon_level}"></span>
                        Carbon Emission: ${material.carbon_emission}kg
                    </div>
                </div>
            `;
            recommendationGrid.appendChild(materialCard);
        }
        
        // 添加总结栏
        const totalSummary = document.createElement('div');
        totalSummary.className = 'total-summary';
        totalSummary.innerHTML = `
            <div class="label">Total Procurement Cost</div>
            <div class="value">¥${data.total_cost}</div>
            <div class="eco-rating">
                <span class="carbon-indicator carbon-${data.total_carbon_level}"></span>
                Carbon Emission Rating
            </div>
        `;
        recommendationGrid.appendChild(totalSummary);
        
        // 2. 更新材料明细表
        const materialsTable = document.getElementById('materials-table');
        const tbody = materialsTable.querySelector('tbody');
        tbody.innerHTML = ''; // 清空现有内容
        
        // 添加每个材料行
        for (const material of data.materials) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${material.name}</td>
                <td>${material.amount}</td>
                <td>${material.price}</td>
                <td>${material.carbon_emission}</td>
                <td>${material.supplier}</td>
            `;
            tbody.appendChild(tr);
        }
        
        // 添加总计行
        const totalRow = document.createElement('tr');
        totalRow.className = 'total-row';
        totalRow.innerHTML = `
            <td>Total</td>
            <td>${data.total_amount}</td>
            <td>${data.total_cost}</td>
            <td>${data.total_carbon_emission}</td>
            <td>-</td>
        `;
        tbody.appendChild(totalRow);
        
        // 3. 更新表单输入值（如果有预测数据）
        if (data.predictions) {
            const inputs = predictionForm.querySelectorAll('input');
            inputs.forEach(input => {
                const productId = input.id.split('-')[1];
                if (data.predictions[productId]) {
                    input.value = data.predictions[productId].quantity;
                } else {
                    input.value = 0;
                }
            });
        }
        
        // 4. 更新历史销售数据表格
        if (salesHistoryTable && data.sales_history) {
            updateSalesHistoryTable(data.sales_history);
        }
    }
    
    // 根据碳排放量确定等级
    function getCarbonLevel(emission) {
        if (emission <= 10) return 'low';
        if (emission <= 30) return 'medium';
        return 'high';
    }
}); 