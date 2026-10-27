// 移除原有的 handleLogin 函数，使用表单的默认提交行为
document.addEventListener('DOMContentLoaded', function() {
    // 初始化粒子效果
    if (typeof particlesJS !== 'undefined') {
        particlesJS('particles-js', {
            // 直接将配置写在这里，而不是加载外部文件
            "particles": {
                "number": {
                    "value": 80,
                    "density": {
                        "enable": true,
                        "value_area": 800
                    }
                },
                // ... 其他配置
            }
        });
    }

    // 表单验证
    const forms = document.querySelectorAll('.auth-form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const password = form.querySelector('input[type="password"]');
            const confirmPassword = form.querySelector('input[name="confirm_password"]');
            
            if (confirmPassword && password.value !== confirmPassword.value) {
                e.preventDefault();
                alert('Passwords do not match');
            }
        });
    });

    // 输入框动画效果
    const inputs = document.querySelectorAll('.auth-form input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
}); 