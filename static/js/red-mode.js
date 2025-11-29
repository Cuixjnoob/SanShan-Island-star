document.addEventListener('DOMContentLoaded', () => {
    // 动态创建按钮
    let toggleBtn = document.getElementById('redModeToggle');
    
    if (!toggleBtn) {
        toggleBtn = document.createElement('button');
        toggleBtn.id = 'redModeToggle';
        toggleBtn.className = 'mode-toggle';
        toggleBtn.title = '切换红光模式以保护暗适应';
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i> <span>红光模式</span>';
        document.body.insertBefore(toggleBtn, document.body.firstChild);
    }

    const body = document.body;
    const icon = toggleBtn.querySelector('i');
    const text = toggleBtn.querySelector('span');
    
    // 检查本地存储
    if (localStorage.getItem('redMode') === 'true') {
        body.classList.add('red-mode');
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
        text.textContent = '退出红光';
    }
    
    toggleBtn.addEventListener('click', () => {
        body.classList.toggle('red-mode');
        const isRed = body.classList.contains('red-mode');
        localStorage.setItem('redMode', isRed);
        
        if (isRed) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
            text.textContent = '退出红光';
        } else {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
            text.textContent = '红光模式';
        }
    });
});