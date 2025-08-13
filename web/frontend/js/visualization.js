/**
 * 数据可视化模块
 */

class VisualizationManager {
    constructor() {
        this.charts = {};
        this.animationFrameId = null;
        this.isInitialized = false;
        
        this.init();
    }

    /**
     * 初始化可视化组件
     */
    init() {
        this.initializeCharts();
        this.setupEventListeners();
        this.startAnimationLoop();
        this.isInitialized = true;
        
        console.log('可视化管理器初始化完成');
    }

    /**
     * 初始化图表
     */
    initializeCharts() {
        this.initResponseTimeChart();
        this.initAccuracyChart();
        this.initResourceUsageChart();
        this.initArmVisualization();
    }

    /**
     * 初始化响应时间图表
     */
    initResponseTimeChart() {
        const canvas = document.getElementById('responseTimeChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.responseTime = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '响应时间',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 3000,
                        ticks: {
                            callback: function(value) {
                                return value + 'ms';
                            },
                            font: {
                                size: 10
                            }
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.05)'
                        }
                    },
                    x: {
                        display: false
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        cornerRadius: 4,
                        displayColors: false
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
    }

    /**
     * 初始化准确率图表
     */
    initAccuracyChart() {
        const canvas = document.getElementById('accuracyChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.accuracy = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['语音识别', '视觉识别', '意图理解'],
                datasets: [{
                    data: [87, 92, 85],
                    backgroundColor: [
                        '#28a745',
                        '#17a2b8',
                        '#ffc107'
                    ],
                    borderWidth: 0,
                    cutout: '60%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            fontSize: 10,
                            padding: 10
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.parsed + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * 初始化资源使用图表
     */
    initResourceUsageChart() {
        const canvas = document.getElementById('resourceChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.resource = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['CPU', '内存', '存储', '网络'],
                datasets: [{
                    label: '使用率',
                    data: [45, 65, 30, 20],
                    backgroundColor: [
                        'rgba(0, 123, 255, 0.8)',
                        'rgba(40, 167, 69, 0.8)',
                        'rgba(255, 193, 7, 0.8)',
                        'rgba(220, 53, 69, 0.8)'
                    ],
                    borderRadius: 4,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            },
                            font: {
                                size: 10
                            }
                        }
                    },
                    x: {
                        ticks: {
                            font: {
                                size: 10
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    /**
     * 初始化机械臂可视化
     */
    initArmVisualization() {
        const canvas = document.getElementById('armVisualization');
        if (!canvas) return;

        this.armCanvas = canvas;
        this.armCtx = canvas.getContext('2d');
        this.armData = {
            position: [0, 0, 0, 0, 0, 0],
            status: 'idle',
            currentGesture: null
        };

        // 设置画布大小
        this.resizeArmCanvas();
    }

    /**
     * 调整机械臂画布大小
     */
    resizeArmCanvas() {
        if (!this.armCanvas) return;

        const container = this.armCanvas.parentElement;
        const rect = container.getBoundingClientRect();
        
        this.armCanvas.width = rect.width - 30; // 留一些边距
        this.armCanvas.height = 200;
        
        this.armCanvas.style.width = (rect.width - 30) + 'px';
        this.armCanvas.style.height = '200px';
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 监听WebSocket数据更新
        if (window.wsManager) {
            window.wsManager.addEventListener('system_status', (data) => {
                this.updateSystemCharts(data);
            });

            window.wsManager.addEventListener('multimodal_data', (data) => {
                this.updateMultimodalVisualization(data);
            });

            window.wsManager.addEventListener('arm_status', (data) => {
                this.updateArmVisualization(data);
            });
        }

        // 监听窗口大小变化
        window.addEventListener('resize', () => {
            this.resizeArmCanvas();
            this.redrawArmVisualization();
        });

        // 图表悬停效果
        this.setupChartInteractions();
    }

    /**
     * 设置图表交互
     */
    setupChartInteractions() {
        // 为响应时间图表添加实时更新效果
        if (this.charts.responseTime) {
            const chart = this.charts.responseTime;
            const originalDestroy = chart.destroy;
            chart.destroy = function() {
                this.clearAnimations();
                originalDestroy.call(this);
            };
        }
    }

    /**
     * 更新系统图表
     */
    updateSystemCharts(data) {
        // 更新响应时间图表
        this.updateResponseTimeChart(data.response_time);
        
        // 更新资源使用图表
        this.updateResourceChart(data);
        
        // 更新准确率图表
        if (data.speech_accuracy && data.vision_accuracy) {
            this.updateAccuracyChart({
                speech: data.speech_accuracy,
                vision: data.vision_accuracy,
                intent: 85 // 假设的意图理解准确率
            });
        }
    }

    /**
     * 更新响应时间图表
     */
    updateResponseTimeChart(responseTime) {
        if (!this.charts.responseTime || !responseTime) return;

        const chart = this.charts.responseTime;
        const now = new Date().toLocaleTimeString();
        
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(responseTime);
        
        // 保持最多30个数据点
        if (chart.data.labels.length > 30) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        // 动态调整Y轴最大值
        const maxValue = Math.max(...chart.data.datasets[0].data);
        chart.options.scales.y.max = Math.max(3000, maxValue * 1.2);
        
        chart.update('none');
    }

    /**
     * 更新资源使用图表
     */
    updateResourceChart(data) {
        if (!this.charts.resource) return;

        const chart = this.charts.resource;
        const newData = [
            data.cpu || 0,
            data.memory || 0,
            Math.random() * 40 + 10, // 模拟存储使用率
            Math.random() * 30 + 10  // 模拟网络使用率
        ];

        chart.data.datasets[0].data = newData;
        chart.update('none');
    }

    /**
     * 更新准确率图表
     */
    updateAccuracyChart(accuracyData) {
        if (!this.charts.accuracy) return;

        const chart = this.charts.accuracy;
        chart.data.datasets[0].data = [
            accuracyData.speech,
            accuracyData.vision,
            accuracyData.intent
        ];
        chart.update('none');
    }

    /**
     * 更新多模态可视化
     */
    updateMultimodalVisualization(data) {
        // 更新视觉检测覆盖层
        this.updateDetectionOverlay(data.vision);
        
        // 更新音频可视化
        this.updateAudioVisualization(data.speech);
        
        // 更新融合结果可视化
        this.updateFusionVisualization(data.fusion);
    }

    /**
     * 更新检测覆盖层
     */
    updateDetectionOverlay(visionData) {
        const overlay = document.getElementById('detectionOverlay');
        if (!overlay || !visionData) return;

        const ctx = overlay.getContext('2d');
        ctx.clearRect(0, 0, overlay.width, overlay.height);

        // 绘制检测框（示例）
        if (visionData.objects && visionData.objects.length > 0) {
            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            ctx.font = '12px Arial';
            ctx.fillStyle = '#00ff00';

            // 模拟检测框位置
            visionData.objects.forEach((obj, index) => {
                const x = 50 + index * 80;
                const y = 50 + index * 30;
                const w = 60;
                const h = 40;

                ctx.strokeRect(x, y, w, h);
                ctx.fillText(obj, x, y - 5);
            });
        }
    }

    /**
     * 更新音频可视化
     */
    updateAudioVisualization(speechData) {
        const audioVisualizer = document.getElementById('audioVisualizer');
        if (!audioVisualizer || !speechData) return;

        // 创建简单的音频波形可视化
        const confidence = speechData.confidence || 0;
        const bars = audioVisualizer.querySelectorAll('.audio-bar');
        
        bars.forEach((bar, index) => {
            const height = Math.random() * confidence * 100;
            bar.style.height = height + '%';
            bar.style.opacity = confidence;
        });
    }

    /**
     * 更新融合结果可视化
     */
    updateFusionVisualization(fusionData) {
        if (!fusionData) return;

        // 更新意图置信度可视化
        const intentBar = document.getElementById('intentConfidenceBar');
        if (intentBar && fusionData.confidence) {
            const percentage = fusionData.confidence * 100;
            intentBar.style.width = percentage + '%';
            intentBar.textContent = percentage.toFixed(1) + '%';
            
            // 根据置信度设置颜色
            if (percentage > 80) {
                intentBar.className = 'progress-bar bg-success';
            } else if (percentage > 60) {
                intentBar.className = 'progress-bar bg-warning';
            } else {
                intentBar.className = 'progress-bar bg-danger';
            }
        }
    }

    /**
     * 更新机械臂可视化
     */
    updateArmVisualization(armData) {
        if (!armData) return;

        this.armData = { ...this.armData, ...armData };
        this.redrawArmVisualization();
    }

    /**
     * 重绘机械臂可视化
     */
    redrawArmVisualization() {
        if (!this.armCtx) return;

        const ctx = this.armCtx;
        const canvas = this.armCanvas;
        const width = canvas.width;
        const height = canvas.height;

        // 清空画布
        ctx.clearRect(0, 0, width, height);

        // 设置绘制样式
        ctx.strokeStyle = '#ffffff';
        ctx.fillStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // 绘制背景网格
        this.drawGrid(ctx, width, height);

        // 绘制机械臂
        this.drawRobotArm(ctx, width, height);

        // 绘制状态信息
        this.drawArmStatus(ctx, width, height);
    }

    /**
     * 绘制背景网格
     */
    drawGrid(ctx, width, height) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;

        const gridSize = 20;
        
        // 绘制垂直线
        for (let x = 0; x <= width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }

        // 绘制水平线
        for (let y = 0; y <= height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
    }

    /**
     * 绘制机械臂
     */
    drawRobotArm(ctx, width, height) {
        const centerX = width / 2;
        const centerY = height - 30;
        const positions = this.armData.position || [0, 0, 0, 0, 0, 0];

        // 恢复绘制样式
        ctx.strokeStyle = '#ffffff';
        ctx.fillStyle = '#ffffff';
        ctx.lineWidth = 3;

        // 绘制基座
        ctx.beginPath();
        ctx.arc(centerX, centerY, 10, 0, 2 * Math.PI);
        ctx.fill();

        // 绘制关节和连杆
        let currentX = centerX;
        let currentY = centerY;
        const segmentLengths = [40, 35, 30, 25]; // 各段长度
        const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']; // 各段颜色

        for (let i = 0; i < Math.min(4, positions.length); i++) {
            const angle = (positions[i] || 0) * Math.PI / 180;
            const length = segmentLengths[i];
            
            // 计算下一个点的位置
            const nextX = currentX + Math.cos(angle - Math.PI/2) * length;
            const nextY = currentY + Math.sin(angle - Math.PI/2) * length;

            // 绘制连杆
            ctx.strokeStyle = colors[i];
            ctx.lineWidth = 6 - i;
            ctx.beginPath();
            ctx.moveTo(currentX, currentY);
            ctx.lineTo(nextX, nextY);
            ctx.stroke();

            // 绘制关节
            ctx.fillStyle = colors[i];
            ctx.beginPath();
            ctx.arc(nextX, nextY, 4, 0, 2 * Math.PI);
            ctx.fill();

            currentX = nextX;
            currentY = nextY;
        }

        // 绘制末端执行器
        ctx.fillStyle = '#ffd93d';
        ctx.beginPath();
        ctx.arc(currentX, currentY, 6, 0, 2 * Math.PI);
        ctx.fill();

        // 添加动作轨迹
        if (this.armData.status === 'active') {
            this.drawMotionTrail(ctx, currentX, currentY);
        }
    }

    /**
     * 绘制运动轨迹
     */
    drawMotionTrail(ctx, x, y) {
        const time = Date.now() * 0.005;
        const trailLength = 20;
        
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        
        for (let i = 0; i < trailLength; i++) {
            const alpha = (i / trailLength) * 0.3;
            const offset = i * 2;
            const trailX = x + Math.sin(time - offset * 0.1) * 5;
            const trailY = y + Math.cos(time - offset * 0.1) * 3;
            
            ctx.globalAlpha = alpha;
            ctx.beginPath();
            ctx.arc(trailX, trailY, 1, 0, 2 * Math.PI);
            ctx.stroke();
        }
        
        ctx.globalAlpha = 1;
    }

    /**
     * 绘制机械臂状态信息
     */
    drawArmStatus(ctx, width, height) {
        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';

        const status = this.armData.status || 'idle';
        const gesture = this.armData.currentGesture || '无';

        ctx.fillText(`状态: ${status}`, 10, 20);
        ctx.fillText(`手势: ${gesture}`, 10, 35);

        // 绘制关节角度信息
        const positions = this.armData.position || [0, 0, 0, 0, 0, 0];
        positions.forEach((pos, index) => {
            ctx.fillText(`J${index + 1}: ${pos.toFixed(1)}°`, 10, 55 + index * 15);
        });
    }

    /**
     * 开始动画循环
     */
    startAnimationLoop() {
        const animate = () => {
            // 更新需要动画的可视化元素
            if (this.armData.status === 'active') {
                this.redrawArmVisualization();
            }

            this.animationFrameId = requestAnimationFrame(animate);
        };

        animate();
    }

    /**
     * 停止动画循环
     */
    stopAnimationLoop() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    /**
     * 导出图表为图片
     */
    exportChart(chartName, filename) {
        const chart = this.charts[chartName];
        if (!chart) return;

        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = filename || `${chartName}_chart.png`;
        link.href = url;
        link.click();
    }

    /**
     * 重置所有图表
     */
    resetCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart.data && chart.data.datasets) {
                chart.data.datasets.forEach(dataset => {
                    dataset.data = [];
                });
                if (chart.data.labels) {
                    chart.data.labels = [];
                }
                chart.update();
            }
        });
    }

    /**
     * 销毁可视化管理器
     */
    destroy() {
        this.stopAnimationLoop();
        
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        this.charts = {};
        this.isInitialized = false;
    }
}

// 全局可视化管理器实例
let visualizationManager = null;

// 初始化可视化管理器
document.addEventListener('DOMContentLoaded', () => {
    // 等待Chart.js加载完成
    if (typeof Chart !== 'undefined') {
        visualizationManager = new VisualizationManager();
        window.visualizationManager = visualizationManager;
        console.log('可视化管理器已初始化');
    } else {
        console.error('Chart.js未加载，无法启动可视化管理器');
    }
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (visualizationManager) {
        visualizationManager.destroy();
    }
});