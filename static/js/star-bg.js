// 星空背景动画
function initStarBackground() {
    // 如果页面上没有canvas元素，创建一个
    let canvas = document.getElementById('star-bg');
    if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'star-bg';
        document.body.prepend(canvas);
    }

    const ctx = canvas.getContext('2d');
    let width, height, stars;
    
    // 鼠标位置配置
    let mouse = {
        x: null,
        y: null,
        max: 20000 // 鼠标连线距离的平方
    };

    // 监听鼠标移动
    window.onmousemove = function(e) {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    };

    // 鼠标移出清除位置
    window.onmouseout = function() {
        mouse.x = null;
        mouse.y = null;
    };

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
        initStars();
    }

    function initStars() {
        stars = [];
        const starCount = Math.floor((width * height) / 8000); // 调整星星密度
        for (let i = 0; i < starCount; i++) {
            stars.push({
                x: Math.random() * width,
                y: Math.random() * height,
                radius: Math.random() * 1.5 + 0.5,
                vx: (Math.random() - 0.5) * 0.8, // 速度
                vy: (Math.random() - 0.5) * 0.8,
                max: 6000 // 星星之间连线的距离平方
            });
        }
    }

    function draw() {
        ctx.clearRect(0, 0, width, height);
        
        stars.forEach((star, index) => {
            // 更新位置
            star.x += star.vx;
            star.y += star.vy;

            // 边界反弹
            if (star.x < 0 || star.x > width) star.vx *= -1;
            if (star.y < 0 || star.y > height) star.vy *= -1;

            // 绘制星星
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.beginPath();
            ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
            ctx.fill();

            // 1. 与鼠标互动（连线 + 吸引）
            if (mouse.x !== null) {
                let dx = star.x - mouse.x;
                let dy = star.y - mouse.y;
                let dist = dx * dx + dy * dy;
                
                if (dist < mouse.max) {
                    // 靠近鼠标时被吸引
                    if (dist > mouse.max / 5) {
                        star.x -= dx * 0.03;
                        star.y -= dy * 0.03;
                    }
                    
                    // 绘制连线
                    ctx.beginPath();
                    ctx.lineWidth = 1;
                    ctx.strokeStyle = 'rgba(255, 255, 255,' + (1 - dist / mouse.max) * 0.6 + ')';
                    ctx.moveTo(star.x, star.y);
                    ctx.lineTo(mouse.x, mouse.y);
                    ctx.stroke();
                }
            }

            // 2. 星星之间连线
            for (let i = index + 1; i < stars.length; i++) {
                let star2 = stars[i];
                let dx = star.x - star2.x;
                let dy = star.y - star2.y;
                let dist = dx * dx + dy * dy;

                if (dist < star.max) {
                    ctx.beginPath();
                    ctx.lineWidth = 0.5;
                    ctx.strokeStyle = 'rgba(255, 255, 255,' + (1 - dist / star.max) * 0.2 + ')';
                    ctx.moveTo(star.x, star.y);
                    ctx.lineTo(star2.x, star2.y);
                    ctx.stroke();
                }
            }
        });
        
        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', resize);
    resize();
    draw();
}

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    initStarBackground();
});
