// 声明全局变量
let charts = {};
let totalEnergyChart;
let currentTimeRanges = {};

// 初始化图表
function initDeviceCharts() {
    const deviceCharts = document.querySelectorAll('.device-chart');
    const now = new Date();
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);

    deviceCharts.forEach(chartElement => {
        const deviceId = chartElement.id.split('-')[1];
        const chart = echarts.init(chartElement);
        const option = {
            animation: true,
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#eee',
                borderWidth: 1,
                textStyle: {
                    color: '#333'
                },
                formatter: function(params) {
                    const date = new Date(params[0].value[0]);
                    const hours = date.getHours().toString().padStart(2, '0');
                    const minutes = date.getMinutes().toString().padStart(2, '0');
                    return `${hours}:${minutes}<br/>
                            Power: <strong>${params[0].value[1].toFixed(1)}W</strong>`;
                }
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '12%',
                top: '12%',
                containLabel: true
            },
            xAxis: {
                type: 'time',
                min: oneHourAgo.getTime(),
                max: now.getTime(),
                axisLine: {
                    lineStyle: {
                        color: '#ddd'
                    }
                },
                axisTick: {
                    show: false
                },
                axisLabel: {
                    formatter: function(value) {
                        const date = new Date(value);
                        return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
                    },
                    color: '#666',
                    fontSize: 11
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        color: '#f5f5f5',
                        type: 'dashed'
                    }
                }
            },
            yAxis: {
                type: 'value',
                name: 'Consumption(kWh)',
                //nameLocation: 'start', // 将标题放置在纵轴的顶部
                nameRotate: 0,  // 确保标题横向显示
                nameTextStyle: {
                    color: '#666',
                    fontSize: 12,  // 减小字体大小
                    padding: [0, 0, 0, 0]  // 更大的左侧内边距
                },
                axisLine: {
                    show: false
                },
                axisTick: {
                    show: false
                },
                axisLabel: {
                    color: '#666',
                    fontSize: 11,
                    margin: 12,
                    formatter: function(value) {
                        return value.toFixed(0);
                    }
                },
                splitLine: {
                    lineStyle: {
                        color: '#f5f5f5'
                    }
                }
            },
            series: [{
                type: 'line',
                smooth: true,
                showSymbol: false,
                symbolSize: 0,
                lineStyle: {
                    width: 2,
                    color: '#3b82f6'
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59, 130, 246, 0.2)' },
                        { offset: 1, color: 'rgba(59, 130, 246, 0.02)' }
                    ])
                },
                data: []
            }]
        };
        chart.setOption(option);
        charts[deviceId] = chart;
        currentTimeRanges[deviceId] = 'hour';
    });

    // 为每个设备图表添加时间范围选择器
    document.querySelectorAll('.device-card').forEach(card => {
        const timeSelector = document.createElement('div');
        timeSelector.className = 'time-range-selector';
        timeSelector.innerHTML = `
            <button class="time-btn active" data-range="hour">1 Hour</button>
            <button class="time-btn" data-range="day">24 Hours</button>
        `;
        
        const chartContainer = card.querySelector('.device-chart');
        chartContainer.parentNode.insertBefore(timeSelector, chartContainer);

        // 添加点击事件
        timeSelector.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const deviceId = card.querySelector('.device-chart').id.split('-')[1];
                const range = this.dataset.range;
                
                // 更新按钮状态
                timeSelector.querySelectorAll('.time-btn').forEach(b => 
                    b.classList.remove('active'));
                this.classList.add('active');
                
                // 更新存储的时间范围
                currentTimeRanges[deviceId] = range;
                
                // 更新图表数据
                updateDeviceData(deviceId, range);
            });
        });
    });
}

function updateDeviceData(specificDeviceId = null, timeRange = null) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    fetch(`/api/manager/device-data`)
        .then(response => response.json())
        .then(data => {
            data.forEach(device => {
                if (charts[device.id] && (!specificDeviceId || device.id == specificDeviceId)) {
                    const chartElement = document.getElementById(`chart-${device.id}`);
                    const deviceCard = chartElement.closest('.device-card');

                    // 获取当前设备的状态并保存
                    const currentStatus = deviceCard.querySelector('.device-status').textContent;

                    // 获取当前选择的时间范围
                    const range = timeRange || currentTimeRanges[device.id] || 'hour';

                    let startTime;
                    if (range === 'hour') {
                        startTime = new Date(now.getTime() - 60 * 60 * 1000); // 1小时前
                    } else {
                        startTime = today; // 24小时
                    }

                    // 更新图表数据
                    const formattedData = device.power_data
                        .filter(item => new Date(item[0]) >= startTime)
                        .map(item => ({
                            name: new Date(item[0]).getTime(),
                            value: [new Date(item[0]).getTime(), item[1]]
                        }));

                    charts[device.id].setOption({
                        animation: true,
                        xAxis: {
                            min: startTime.getTime(),
                            max: now.getTime()
                        },
                        series: [{
                            data: formattedData
                        }]
                    });

                    // 更新设备信息，不改变状态
                    updateDeviceInfo(device, formattedData);

                    // 确保状态不会被错误修改
                    const statusElement = deviceCard.querySelector('.device-status');
                    if (statusElement && statusElement.textContent !== currentStatus) {
                        statusElement.textContent = currentStatus;
                    }
                }
            });
        });
}


// 初始化总耗电量图表
function initTotalEnergyChart() {
    const chart = echarts.init(document.getElementById('totalEnergyChart'));
    
    const option = {
        title: {
            text: 'Store Power Consumption Trend',
            left: 'center',
            textStyle: {
                fontSize: 16
            }
        },
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                const date = new Date(params[0].axisValue);
                const formattedDate = date.toLocaleString('en-US', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit'
                });
                return `${formattedDate}<br/>Hourly Consumption: ${params[0].value[1].toFixed(2)} kWh`;
            },
            axisPointer: {
                type: 'cross',
                label: {
                    backgroundColor: '#6a7985'
                }
            }
        },
        grid: {
            left: '7%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'time',
            boundaryGap: false,
            axisLabel: {
                formatter: function(value) {
                    const date = new Date(value);
                    return date.toLocaleString('en-US', {
                        hour: '2-digit'
                    }) + ':00';
                }
            }
        },
        yAxis: {
            type: 'value',
            name: 'Consumption (kWh)',
            nameTextStyle: {
                padding: [0, 100, 0, 0]
            },
            axisLabel: {
                formatter: function(value) {
                    return value.toFixed(2);
                }
            },
            min: 0
        },
        series: [{
            name: 'Hourly Consumption',
            type: 'line',
            smooth: true,
            showSymbol: false,
            sampling: 'average',
            areaStyle: {
                opacity: 0.4,
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(76, 175, 80, 0.8)' },
                    { offset: 1, color: 'rgba(76, 175, 80, 0.2)' }
                ])
            },
            itemStyle: {
                color: '#4CAF50'
            },
            lineStyle: {
                width: 3
            },
            data: []
        }]
    };
    
    chart.setOption(option);
    return chart;
}

// 更新总耗电量数据
function updateTotalEnergyData(period = 'day') {
    fetch(`/api/manager/total-energy?period=${period}&accumulated=false`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.energy_data) {
                // 格式化数据 - 不再使用累积值
                let formattedData = data.energy_data.map(item => ({
                    name: item[0],
                    value: [item[0], item[1]]
                }));
                
                // 根据选择的时间段调整X轴标签格式和数据聚合
                let xAxisFormatter;
                let yAxisName = 'Consumption(kWh)';
                
                if (period === 'day') {
                    // 对24小时数据按小时聚合
                    formattedData = aggregateDataByHour(formattedData);
                    xAxisFormatter = function(value) {
                        const date = new Date(value);
                        return date.toLocaleString('en-US', { hour: '2-digit' });
                    };
                    //yAxisName = 'Hourly Power   Consumption(kWh)';
                } else if (period === 'week') {
                    // 对于周数据，不需要聚合，已经是每小时一个点
                    xAxisFormatter = function(value) {
                        const date = new Date(value);
                        return date.toLocaleString('en-US', { month: '2-digit', day: '2-digit' });
                    };
                    //yAxisName = 'Hourly Power   Consumption(kWh)';
                } else { // month
                    // 对于月数据，按天聚合
                    formattedData = aggregateDataByDay(formattedData);
                    xAxisFormatter = function(value) {
                        const date = new Date(value);
                        return date.toLocaleString('en-US', { month: '2-digit', day: '2-digit' });
                    };
                    //yAxisName = 'Hourly Power           Consumption(kWh)';
                }
                
                // 计算Y轴最大值，稍微放大以便有留白
                const maxValue = formattedData.length > 0 ? 
                    Math.max(...formattedData.map(item => item.value[1])) * 1.2 : 1;
                
                // 更新图表配置
                totalEnergyChart.setOption({
                    tooltip: {
                        trigger: 'axis',
                        formatter: function(params) {
                            const date = new Date(params[0].axisValue);
                            let formattedDate;
                            
                            if (period === 'day') {
                                formattedDate = date.toLocaleString('en-US', {
                                    month: '2-digit',
                                    day: '2-digit',
                                    hour: '2-digit'
                                });
                                return `${formattedDate}<br/>Hourly power consumption: ${params[0].value[1].toFixed(2)} kWh`;
                            } else if (period === 'week') {
                                formattedDate = date.toLocaleString('en-US', {
                                    month: '2-digit',
                                    day: '2-digit',
                                    weekday: 'short'
                                });
                                return `${formattedDate}<br/>Hourly power consumption: ${params[0].value[1].toFixed(2)} kWh`;
                            } else {
                                formattedDate = date.toLocaleString('en-US', {
                                    year: 'numeric',
                                    month: '2-digit',
                                    day: '2-digit'
                                });
                                return `${formattedDate}<br/>Daily power consumption: ${params[0].value[1].toFixed(2)} kWh`;
                            }
                        }
                    },
                    xAxis: {
                        axisLabel: {
                            formatter: xAxisFormatter
                        }
                    },
                    yAxis: {
                        name: yAxisName,
                        max: maxValue,
                        min: 0,
                        axisLabel: {
                            formatter: function(value) {
                                return value.toFixed(2);
                            }
                        }
                    },
                    series: [{
                        name: '时段耗电量',
                        type: 'line',
                        smooth: true,
                        showSymbol: false,
                        sampling: 'average',
                        itemStyle: {
                            color: '#4CAF50'
                        },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(76, 175, 80, 0.6)' },
                                { offset: 1, color: 'rgba(76, 175, 80, 0.1)' }
                            ])
                        },
                        lineStyle: {
                            width: 3
                        },
                        data: formattedData
                    }]
                });
            }
        })
        .catch(error => {
            console.error('获取能耗数据失败:', error);
        });
}

// 按小时聚合数据
function aggregateDataByHour(data) {
    const hourlyData = {};
    
    data.forEach(item => {
        const date = new Date(item.name);
        // 将日期设置为当天的每个小时整点
        const hourKey = new Date(
            date.getFullYear(),
            date.getMonth(),
            date.getDate(),
            date.getHours()
        ).toISOString();
        
        if (!hourlyData[hourKey]) {
            hourlyData[hourKey] = {
                count: 0,
                total: 0
            };
        }
        
        hourlyData[hourKey].count++;
        hourlyData[hourKey].total += item.value[1];
    });
    
    // 转换为图表需要的格式
    return Object.keys(hourlyData).map(key => {
        const entry = hourlyData[key];
        // 计算每个小时的平均能耗，并固定保留两位小数
        const hourlyPower = entry.total * (60 / 5); // 假设数据间隔为5分钟，转换为每小时
        return {
            name: key,
            value: [key, parseFloat(hourlyPower.toFixed(2))]
        };
    }).sort((a, b) => new Date(a.name) - new Date(b.name));
}

// 按天聚合数据
function aggregateDataByDay(data) {
    const dailyData = {};
    
    data.forEach(item => {
        const date = new Date(item.name);
        // 将日期设置为当天的0点
        const dayKey = new Date(
            date.getFullYear(),
            date.getMonth(),
            date.getDate()
        ).toISOString();
        
        if (!dailyData[dayKey]) {
            dailyData[dayKey] = {
                count: 0,
                total: 0
            };
        }
        
        dailyData[dayKey].count++;
        dailyData[dayKey].total += item.value[1];
    });
    
    // 转换为图表需要的格式
    return Object.keys(dailyData).map(key => {
        const entry = dailyData[key];
        // 计算每天的总能耗，并固定保留两位小数
        const dailyPower = entry.total * (24 / (entry.count / 6)); // 假设数据间隔为4小时，转换为每天
        return {
            name: key,
            value: [key, parseFloat(dailyPower.toFixed(2))]
        };
    }).sort((a, b) => new Date(a.name) - new Date(b.name));
}

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    // 初始化设备图表
    initDeviceCharts();
    
    // 初始化总耗电量图表
    totalEnergyChart = initTotalEnergyChart();
    
    // 设置时间段选择按钮的点击事件
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // 移除其他按钮的active类
            document.querySelectorAll('.period-btn').forEach(b => 
                b.classList.remove('active'));
            // 添加当前按钮的active类
            this.classList.add('active');
            // 更新图表数据
            updateTotalEnergyData(this.dataset.period);
        });
    });
    
    // 初始加载24小时数据
    updateTotalEnergyData('day');
    
    // 设置定时更新
    setInterval(() => {
        updateDeviceData();
        updateTotalEnergyData(
            document.querySelector('.period-btn.active').dataset.period
        );
    }, 60000); // 每分钟更新一次

    // 监听窗口大小变化，调整图表大小
    window.addEventListener('resize', function() {
        totalEnergyChart.resize();
    });

    // 修改设备状态切换的事件处理
    document.querySelector('.devices-list').addEventListener('click', function(e) {
        if (e.target.classList.contains('toggle-btn')) {
            const deviceCard = e.target.closest('.device-card');
            const deviceId = deviceCard.querySelector('.device-chart').id.split('-')[1];
            
            fetch(`/manager/devices/${deviceId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 更新状态显示
                    const statusElement = deviceCard.querySelector('.device-status');
                    const isActive = data.status === 'active';
                    
                    if (statusElement) {
                        statusElement.textContent = isActive ? 'Running' : 'Stopped';
                        statusElement.className = `device-status ${data.status}`;
                    }
                    
                    // 更新按钮文本
                    e.target.textContent = isActive ? 'Stopped' : 'Running';
                    
                    // 更新当前功率显示
                    const powerElement = deviceCard.querySelector('.current-power .value');
                    if (powerElement) {
                        powerElement.textContent = `${data.current_power}W`;
                    }
                    
                    // 立即更新图表数据
                    updateDeviceData(deviceId);
                }
            })
            .catch(error => console.error('切换设备状态失败:', error));
        }
    });
});

// 添加图表加载动画
function showLoading() {
    document.querySelectorAll('.device-chart').forEach(el => {
        const chart = echarts.getInstanceByDom(el);
        if (chart) {
            chart.showLoading({
                text: 'Loading data...',
                color: '#3498db',
                textColor: '#2c3e50',
                maskColor: 'rgba(255, 255, 255, 0.8)',
                zlevel: 0
            });
        }
    });
}

function hideLoading() {
    document.querySelectorAll('.device-chart').forEach(el => {
        const chart = echarts.getInstanceByDom(el);
        if (chart) {
            chart.hideLoading();
        }
    });
}

// 在页面初始化时添加窗口大小变化监听
window.addEventListener('resize', function() {
    document.querySelectorAll('.device-chart').forEach(el => {
        const chart = echarts.getInstanceByDom(el);
        if (chart) {
            chart.resize();
        }
    });
});

// 设备信息更新函数优化
function updateDeviceInfo(device, formattedData) {
    const chartElement = document.getElementById(`chart-${device.id}`);
    if (!chartElement) return;
    
    const deviceCard = chartElement.closest('.device-card');
    const statusElement = deviceCard.querySelector('.device-status');
    const powerElement = deviceCard.querySelector('.current-power .value');
    const consumptionElement = deviceCard.querySelector('.today-consumption .value');
    
    // 获取最新功率值
    let currentPower = 0;
    if (formattedData && formattedData.length > 0) {
        // 取最后一个数据点
        currentPower = formattedData[formattedData.length - 1].value[1];
    }
    
    // 计算今日能耗（累计功率 * 时间）
    const today = new Date().setHours(0, 0, 0, 0);
    let todayConsumption = 0;
    
    // 使用原始的完整数据计算今日能耗，而不是使用图表显示的数据
    if (device.power_data && device.power_data.length > 0) {
        let lastTime = null;
        let lastPower = 0;
        
        device.power_data.forEach(item => {
            const time = new Date(item[0]);
            if (time >= today) {
                if (lastTime) {
                    // 计算两点之间的时间差（小时）
                    const hoursDiff = (time - lastTime) / (1000 * 60 * 60);
                    // 使用平均功率计算这段时间的能耗
                    const avgPower = (lastPower + item[1]) / 2;
                    // 累加能耗 (kWh)
                    todayConsumption += (avgPower * hoursDiff) / 1000;
                }
                lastTime = time;
                lastPower = item[1];
            }
        });
    }
    
    // 更新显示
    if (statusElement) {
        statusElement.textContent = device.status === 'active' ? 'Running' : 'Stopped';
        statusElement.className = `device-status ${device.status}`;
    }
    
    if (powerElement) {
        powerElement.textContent = `${currentPower.toFixed(1)}W`;
    }
    
    if (consumptionElement) {
        consumptionElement.textContent = `${todayConsumption.toFixed(2)}kWh`;
    }
} 