document.addEventListener('DOMContentLoaded', function() {
    // 初始化 AOS 动画
    AOS.init({
        duration: 1000,
        once: true,
        offset: 100
    });

    // 图表动画
    const chartBars = document.querySelectorAll('.chart-bar');
    chartBars.forEach(bar => {
        const height = bar.style.height;
        bar.style.height = '0';
        setTimeout(() => {
            bar.style.height = height;
        }, 300);
    });

    // 数字计数动画
    const numbers = document.querySelectorAll('.metric-number');
    numbers.forEach(number => {
        const target = parseFloat(number.textContent);
        let start = 0;
        const duration = 2000;
        const step = target / duration * 10;
        
        const updateNumber = () => {
            start += step;
            if (start < Math.abs(target)) {
                number.textContent = target < 0 ? 
                    `-${Math.floor(start)}%` : 
                    `${Math.floor(start)}%`;
                requestAnimationFrame(updateNumber);
            } else {
                number.textContent = `${target}%`;
            }
        };
        
        updateNumber();
    });

    // 初始化统计数字动画
    const counters = document.querySelectorAll('.counter');
    counters.forEach(counter => {
        const target = parseInt(counter.innerText);
        const duration = 2000;
        const step = target / duration * 10;
        let current = 0;

        const updateCounter = () => {
            current += step;
            if (current < target) {
                counter.innerText = Math.floor(current);
                setTimeout(updateCounter, 10);
            } else {
                counter.innerText = target;
            }
        };

        updateCounter();
    });

    // 响应式导航菜单
    const menuToggle = document.querySelector('.menu-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });
    }
}); 