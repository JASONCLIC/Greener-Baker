// 初始化首页数据
document.addEventListener('DOMContentLoaded', function() {
    // 能源消耗数据
    const energyData = {
        percentage: -15,
        currentUsage: 85
    };
    
    // 更新能源消耗显示
    const energyNumber = document.querySelector('.energy-consumption .metric-number');
    const energyBar = document.querySelector('.energy-consumption .chart-bar');
    
    if (energyNumber && energyBar) {
        energyNumber.textContent = `${energyData.percentage}%`;
        energyBar.style.height = `${energyData.currentUsage}%`;
    }
    
    // 添加数据更新动画
    const cards = document.querySelectorAll('.metric-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            const bar = this.querySelector('.chart-bar');
            if (bar) {
                bar.style.transform = 'scaleY(1.02)';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            const bar = this.querySelector('.chart-bar');
            if (bar) {
                bar.style.transform = 'scaleY(1)';
            }
        });
    });
}); 