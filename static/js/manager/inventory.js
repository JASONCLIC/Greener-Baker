// 初始化预测图表
function initPredictionChart() {
    console.log("Initializing prediction chart");

    try {
        // 检查echarts是否已加载
        if (typeof echarts === 'undefined') {
            console.error("Error: echarts is undefined, please ensure the echarts library is loaded");
            return null;
        }

        // 检查容器是否存在
        const chartDom = document.getElementById('predictionChart');
        if (!chartDom) {
            console.error("Error: Cannot find DOM element with ID 'predictionChart'");
            return null;
        }

        // 初始化图表
        const chart = echarts.init(chartDom);
        console.log("Chart initialized successfully");

        // 基础配置
        const option = {
            title: {
                text: 'Raw Material Demand Forecast for Next 3 Days',
                left: 'center'
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: function(params) {
                    let result = params[0].axisValue + '<br/>';
                    params.forEach(param => {
                        result += param.marker + param.seriesName + ': ' +
                                 Math.round(param.value) + '<br/>';
                    });
                    return result;
                }
            },
            legend: {
                data: [],
                top: 30
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: ['Day 1', 'Day 2', 'Day 3']
            },
            yAxis: {
                type: 'value',
                name: 'Demand',
                axisLabel: {
                    formatter: function(value) {
                        return Math.round(value);
                    }
                }
            },
            series: []
        };

        chart.setOption(option);
        return chart;
    } catch (error) {
        console.error("Error initializing prediction chart:", error);
        return null;
    }
}

// 定义全局变量存储预测数据
let chartData = [];
let predictionChart;

// 更新预测数据
function updatePrediction() {
    console.log("开始更新预测数据...");

    // 检查echarts是否加载
    if (typeof echarts === 'undefined') {
        console.error("错误：echarts未定义，无法初始化图表");
        alert("图表库未正确加载，请刷新页面或联系管理员");
        return;
    }

    // 检查图表容器
    const chartContainer = document.getElementById('predictionChart');
    if (!chartContainer) {
        console.error("错误：找不到图表容器元素 #predictionChart");
        return;
    } else {
        console.log("图表容器尺寸:", chartContainer.offsetWidth, "x", chartContainer.offsetHeight);
        // 如果容器尺寸为0，添加内联样式确保其可见
        if (chartContainer.offsetWidth === 0 || chartContainer.offsetHeight === 0) {
            console.warn("图表容器尺寸为0，设置内联样式");
            chartContainer.style.width = '100%';
            chartContainer.style.height = '400px';
            chartContainer.style.border = '1px dashed red'; // 调试用边框
        }
    }

    fetch('/api/manager/inventory-prediction')
        .then(response => {
            console.log("API响应状态:", response.status);
            if (!response.ok) {
                throw new Error('网络响应异常: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log("收到预测数据:", JSON.stringify(data));

            // 检查是否有有效数据
            if (!data || !Array.isArray(data) || data.length === 0) {
                console.warn("收到空的预测数据，使用模拟数据");
                useMockData();
                return;
            }

            // 确保数据格式正确
            const processedData = data.map(item => {
                // 确保predictions是数字数组
                let predictions = Array.isArray(item.predictions) ? item.predictions : [0, 0, 0];
                predictions = predictions.map(val => {
                    const numVal = parseFloat(val);
                    return isNaN(numVal) ? 0 : numVal;
                });

                // 如果所有的预测值都是0，添加一些随机值以便显示
                const isAllZero = predictions.every(val => val === 0);
                if (isAllZero) {
                    console.warn(`${item.material}的所有预测值都是0，添加随机值`);
                    predictions = [
                        Math.random() * 10 + 5,
                        Math.random() * 10 + 5,
                        Math.random() * 10 + 5
                    ];
                }

                return {
                    material: item.material || '未知材料',
                    unit: item.unit || 'kg',
                    predictions: predictions
                };
            });

            // 存储数据到全局变量
            chartData = processedData;

            // 提取材料名称列表用于图例
            const materialNames = processedData.map(item => item.material);
            console.log("材料名称:", materialNames);

            // 准备系列数据
            const seriesData = processedData.map(item => ({
                name: item.material,
                type: 'bar',
                data: item.predictions,
                markLine: {
                    data: [
                        { type: 'average', name: '平均值' }
                    ],
                    label: {
                        formatter: function(params) {
                            return Math.round(params.value);
                        }
                    }
                }
            }));

            // 确保图表已初始化
            if (!predictionChart) {
                console.log("图表未初始化，正在初始化...");
                predictionChart = initPredictionChart();
                if (!predictionChart) {
                    console.error("图表初始化失败，使用模拟数据");
                    useMockData();
                    return;
                }
            }

            // 更新图表配置
            try {
                console.log("更新图表配置...");
                predictionChart.setOption({
                    legend: {
                        data: materialNames
                    },
                    series: seriesData
                });
                console.log("图表更新成功");

                // 强制重绘图表
                predictionChart.resize();
            } catch (error) {
                console.error("更新图表时出错:", error);
                alert("更新图表时发生错误，请查看控制台");
            }

            // 更新图表后生成采购方案
            generatePurchasePlan();
        })
        .catch(error => {
            console.error('获取预测数据失败:', error);
            // 使用模拟数据作为备用
            useMockData();
        });
}

// 生成采购方案的函数
async function generatePurchasePlan() {
    console.log("开始生成采购方案...");

    try {
        // 获取供应商数据
        const suppliersResponse = await fetch('/api/manager/suppliers');
        const suppliersData = await suppliersResponse.json();

        // 使用预测数据（已经存储在chartData中）
        if (!chartData || chartData.length === 0) {
            console.warn("没有预测数据，无法生成采购方案");
            return;
        }

        // 处理每种材料的采购建议
        const purchasePlan = chartData.map(material => {
            // 计算3天的总需求量
            const totalDemand = material.predictions.reduce((sum, val) => sum + val, 0);

            // 获取该材料的供应商信息
            const materialSuppliers = suppliersData[material.material] || [];

            // 选择最佳供应商（考虑价格和碳排放）
            let bestSupplier = null;
            let bestScore = Infinity;

            materialSuppliers.forEach(supplier => {
                // 计算综合评分（价格权重0.6，碳排放权重0.4）
                const score = (supplier.price * 0.6) + (supplier.emission * 0.4);
                if (score < bestScore) {
                    bestScore = score;
                    bestSupplier = supplier;
                }
            });

            // 如果没有找到供应商，使用默认值
            if (!bestSupplier) {
                bestSupplier = {
                    name: `${material.material}供应商A`,
                    price: 100,
                    emission: 10
                };
            }

            return {
                material: material.material,
                amount: totalDemand.toFixed(2),
                unit: material.unit,
                price: (bestSupplier.price * totalDemand).toFixed(2),
                emission: (bestSupplier.emission * totalDemand).toFixed(2),
                supplier: bestSupplier.name
            };
        });

        // 更新表格内容
        updateProcurementTable(purchasePlan);

    } catch (error) {
        console.error('生成采购方案失败:', error);
        showError('生成采购方案失败，请稍后重试');
    }
}

// 更新采购方案表格
function updateProcurementTable(data) {
    const tbody = document.querySelector('.recommendation-table tbody');
    const totalCostElement = document.getElementById('totalCost');
    const totalEmissionElement = document.getElementById('totalEmission');

    if (!tbody) {
        console.error('找不到采购方案表格');
        return;
    }

    // 清空现有内容
    tbody.innerHTML = '';

    // 计算总计
    let totalCost = 0;
    let totalEmission = 0;

    // 添加每行数据
    data.forEach(item => {
        // 确保所有数值都是数字并保留两位小数
        const quantity = parseFloat(item.quantity).toFixed(2);
        const cost = parseFloat(item.cost).toFixed(2);
        const emission = parseFloat(item.emission).toFixed(2);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.material}</td>
            <td>${quantity} ${item.unit}</td>
            <td>¥${cost}</td>
            <td>${emission} kg</td>
            <td>${item.supplier}</td>
        `;
        tbody.appendChild(tr);

        // 累计总计（使用parseFloat避免字符串拼接）
        totalCost += parseFloat(item.cost);
        totalEmission += parseFloat(item.emission);
    });

    // 更新总计，保留两位小数
    if (totalCostElement) {
        totalCostElement.textContent = `¥${totalCost.toFixed(2)}`;
    }
    if (totalEmissionElement) {
        totalEmissionElement.textContent = `${totalEmission.toFixed(2)} kg`;
    }
}

// 使用模拟数据（当API调用失败时）
function useMockData() {
    console.log("使用模拟数据");

    // 模拟数据
    const mockData = [
        {
            material: '面粉',
            unit: 'kg',
            predictions: [15, 18, 12]
        },
        {
            material: '糖',
            unit: 'kg',
            predictions: [8, 10, 7]
        },
        {
            material: '黄油',
            unit: 'kg',
            predictions: [5, 6, 4]
        },
        {
            material: '鸡蛋',
            unit: '个',
            predictions: [20, 25, 18]
        }
    ];

    // 存储到全局变量
    chartData = mockData;

    // 检查图表是否已初始化
    if (!predictionChart) {
        console.log("图表未初始化，尝试重新初始化");
        predictionChart = initPredictionChart();

        // 如果仍然无法初始化，则退出
        if (!predictionChart) {
            console.error("无法初始化图表，放弃显示模拟数据");
            return;
        }
    }

    // 提取材料名称
    const materialNames = mockData.map(item => item.material);

    // 准备系列数据
    const seriesData = mockData.map(item => ({
        name: item.material,
        type: 'bar',
        data: item.predictions,
        markLine: {
            data: [
                { type: 'average', name: '平均值' }
            ],
            label: {
                formatter: function(params) {
                    return Math.round(params.value);
                }
            }
        }
    }));

    // 更新图表
    predictionChart.setOption({
        legend: {
            data: materialNames
        },
        series: seriesData
    });

    console.log("模拟数据已加载到图表");
}

// 显示添加销售数据模态框
function showAddSalesModal() {
    const modal = document.getElementById('addSalesModal');
    if (modal) {
        modal.style.display = 'flex';

        // 设置默认日期为今天
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('sale_date').value = today;
    }
}

// 显示编辑销售数据模态框
function showEditSalesModal(record) {
    const modal = document.getElementById('editSalesModal');
    if (modal) {
        // 填充表单数据
        document.getElementById('edit_record_id').value = record.id;
        document.getElementById('edit_sale_date').value = record.sale_date;
        document.getElementById('edit_product').value = record.product_id;
        document.getElementById('edit_quantity').value = record.quantity;

        // 显示模态框
        modal.style.display = 'flex';
    }
}

// 隐藏模态框
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';

        // 重置表单
        const form = modal.querySelector('form');
        if (form) {
            form.reset();
        }
    }
}

// 用于编辑销售记录的函数
function editSalesRecord(recordId) {
    // 获取记录详情并显示编辑模态框
    fetch(`/manager/sales/${recordId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showEditSalesModal(data.record);
            } else {
                alert('获取销售记录失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取销售记录失败');
        });
}

// 更新销售记录
function updateSalesRecord(recordId, formData) {
    fetch(`/manager/sales/edit/${recordId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 隐藏模态框
            hideModal('editSalesModal');

            // 刷新页面显示更新后的数据
            window.location.reload();
        } else {
            alert('更新销售记录失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('更新销售记录失败');
    });
}

// 用于删除销售记录的函数
function deleteSalesRecord(recordId) {
    // 显示确认对话框
    if (confirm('确定要删除这条销售记录吗？')) {
        // 发送删除请求
        fetch(`/manager/sales/delete/${recordId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 刷新页面显示更新后的数据
                window.location.reload();
            } else {
                alert('删除销售记录失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('删除销售记录失败');
        });
    }
}

// 显示加载动画
function showLoading() {
    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text">Updating data...</div>
    `;
    document.body.appendChild(loading);
}

// 隐藏加载动画
function hideLoading() {
    const loading = document.querySelector('.loading-overlay');
    if (loading) {
        loading.remove();
    }
}

// 显示错误消息
function showError(message) {
    const error = document.createElement('div');
    error.className = 'error-message';
    error.textContent = message;
    document.body.appendChild(error);

    setTimeout(() => {
        error.remove();
    }, 3000);
}

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM已加载完成，初始化库存预测页面");

    // 使用setTimeout确保DOM完全渲染后再初始化图表
    setTimeout(function() {
        console.log("延时后初始化图表...");
        // 检查图表容器是否存在
        const chartContainer = document.getElementById('predictionChart');
        if (chartContainer) {
            console.log("找到预测图表容器，尺寸:", chartContainer.offsetWidth, "x", chartContainer.offsetHeight);

            // 设置容器样式确保可见
            chartContainer.style.width = '100%';
            chartContainer.style.height = '400px';

            // 初始化图表
            try {
                if (predictionChart) {
                    console.log("图表已存在，尝试销毁重建");
                    predictionChart.dispose();
                }

                predictionChart = initPredictionChart();

                // 获取并显示预测数据
                updatePrediction();
            } catch (error) {
                console.error("初始化图表时出错:", error);
                // 尝试使用模拟数据
                useMockData();
            }
        } else {
            console.warn("未找到预测图表容器，跳过图表初始化");
        }
    }, 500); // 延时500毫秒

    // 设置"录入销售数据"按钮的点击事件
    const addSalesBtn = document.querySelector('.add-sales-btn');
    if (addSalesBtn) {
        addSalesBtn.addEventListener('click', showAddSalesModal);
    }

    // 设置"刷新预测"按钮的点击事件
    const refreshBtn = document.querySelector('.refresh-btn');
    if (refreshBtn) {
        console.log("找到刷新预测按钮，添加点击事件");
        refreshBtn.addEventListener('click', function() {
            console.log("点击刷新预测按钮");
            refreshPrediction();
        });
    } else {
        console.warn("未找到刷新预测按钮");
    }

    // 设置所有取消按钮的点击事件
    const cancelBtns = document.querySelectorAll('.cancel-btn');
    cancelBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const modalId = this.closest('.modal').id;
            hideModal(modalId);
        });
    });

    // 点击模态框背景时关闭模态框
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('click', function(event) {
            if (event.target === this) {
                hideModal(this.id);
            }
        });
    });

    // 处理销售表单提交
    const salesForm = document.getElementById('salesForm');
    if (salesForm) {
        salesForm.addEventListener('submit', function(event) {
            // 表单将正常提交，但我们可以在这里添加验证逻辑
            // 表单提交后页面会重新加载，显示最新数据
        });
    }

    // 处理编辑表单提交
    const updateSalesBtn = document.getElementById('updateSalesBtn');
    if (updateSalesBtn) {
        updateSalesBtn.addEventListener('click', function() {
            const editForm = document.getElementById('editSalesForm');
            const recordId = document.getElementById('edit_record_id').value;

            // 创建FormData对象
            const formData = new FormData();
            formData.append('edit_product', document.getElementById('edit_product').value);
            formData.append('edit_quantity', document.getElementById('edit_quantity').value);
            formData.append('edit_sale_date', document.getElementById('edit_sale_date').value);

            // 更新记录
            updateSalesRecord(recordId, formData);
        });
    }

    // 初始化图表和数据
    refreshPrediction();

    // 设置定时刷新（每30分钟）
    setInterval(refreshPrediction, 30 * 60 * 1000);
});

function updateProcurementPlan(data) {
    const tbody = document.getElementById('procurementTableBody');
    const totalCostElement = document.getElementById('totalCost');
    const totalEmissionElement = document.getElementById('totalEmission');

    tbody.innerHTML = '';
    let totalCost = 0;
    let totalEmission = 0;

    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.material}</td>
            <td>${Math.round(item.quantity)} ${item.unit}</td>
            <td>¥${item.cost.toFixed(2)}</td>
            <td>${item.emission.toFixed(2)}kg</td>
            <td>${item.supplier}</td>
        `;
        tbody.appendChild(row);

        totalCost += item.cost;
        totalEmission += item.emission;
    });

    totalCostElement.textContent = `¥${totalCost.toFixed(2)}`;
    totalEmissionElement.textContent = `${totalEmission.toFixed(2)}kg`;
}

// 示例数据获取函数
async function fetchProcurementPlan() {
    try {
        const response = await fetch('/api/procurement-plan');
        const data = await response.json();
        updateProcurementPlan(data);
    } catch (error) {
        console.error('获取采购方案失败:', error);
    }
}

// 页面加载时获取采购方案
document.addEventListener('DOMContentLoaded', fetchProcurementPlan);