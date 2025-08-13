/**
 * 简化版演示脚本 - 不依赖WebSocket
 */

class SimpleDemoApp {
    constructor() {
        this.isRunning = false;
        this.updateInterval = null;
        this.charts = {};
        
        this.init();
    }

    init() {
        console.log('智能教育助手机器人演示平台初始化...');
        
        // 初始化图表
        this.initCharts();
        
        // 设置事件监听器
        this.setupEventListeners();
        
        // 开始数据更新
        this.startDataUpdates();
        
        // 显示欢迎信息
        this.showWelcomeMessage();
        
        console.log('演示平台初始化完成');
    }

    initCharts() {
        // 初始化响应时间图表
        const responseCtx = document.getElementById('responseTimeChart');
        if (responseCtx) {
            this.charts.responseTime = new Chart(responseCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '响应时间 (ms)',
                        data: [],
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 3000,
                            ticks: {
                                callback: function(value) {
                                    return value + 'ms';
                                }
                            }
                        },
                        x: {
                            display: false
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
    }

    setupEventListeners() {
        // 演示控制按钮
        document.getElementById('startDemo')?.addEventListener('click', () => this.startDemo());
        document.getElementById('pauseDemo')?.addEventListener('click', () => this.pauseDemo());
        document.getElementById('stopDemo')?.addEventListener('click', () => this.stopDemo());

        // 手势控制按钮
        document.querySelectorAll('[data-gesture]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const gesture = e.target.getAttribute('data-gesture');
                this.triggerGesture(gesture);
            });
        });

        // 语音测试
        document.getElementById('testSpeechBtn')?.addEventListener('click', () => {
            const text = document.getElementById('testSpeechInput')?.value;
            if (text) {
                this.testSpeech(text);
            }
        });

        // 清空日志
        document.getElementById('clearLogs')?.addEventListener('click', () => {
            this.clearLogs();
        });

        // 场景切换
        document.getElementById('scenarioSelect')?.addEventListener('change', (e) => {
            this.switchScenario(e.target.value);
        });
    }

    startDataUpdates() {
        this.isRunning = true;
        this.updateData();
        
        this.updateInterval = setInterval(() => {
            this.updateData();
        }, 2000);
    }

    async updateData() {
        try {
            // 获取系统状态
            const response = await fetch('/api/status');
            const data = await response.json();
            
            // 更新状态显示
            this.updateSystemStatus(data);
            
            // 更新多模态数据
            this.updateMultimodalData();
            
            // 更新机械臂状态
            this.updateArmStatus();
            
        } catch (error) {
            console.error('数据更新失败:', error);
            this.showConnectionError();
        }
    }

    updateSystemStatus(data) {
        // 更新状态栏
        document.getElementById('cpuUsage').textContent = `${data.cpu}%`;
        document.getElementById('memoryUsage').textContent = `${data.memory}%`;
        document.getElementById('responseTime').textContent = `${data.response_time}ms`;
        document.getElementById('connectionCount').textContent = data.connections;
        document.getElementById('lastUpdate').textContent = `最后更新: ${new Date().toLocaleTimeString()}`;

        // 更新准确率
        document.getElementById('speechAccuracy').textContent = `${data.speech_accuracy}%`;
        document.getElementById('visionAccuracy').textContent = `${data.vision_accuracy}%`;

        // 更新响应时间图表
        this.updateResponseTimeChart(data.response_time);

        // 更新系统状态指示器
        const statusElement = document.getElementById('systemStatus');
        if (statusElement) {
            statusElement.innerHTML = '<i class="fas fa-circle pulse"></i> 系统运行中';
            statusElement.className = 'badge bg-success';
        }
    }

    updateResponseTimeChart(responseTime) {
        if (!this.charts.responseTime) return;

        const chart = this.charts.responseTime;
        const now = new Date().toLocaleTimeString();
        
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(responseTime);
        
        // 保持最多20个数据点
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.update('none');
    }

    updateMultimodalData() {
        // 模拟多模态数据
        const mockData = this.generateMockMultimodalData();
        
        // 更新语音识别
        document.getElementById('speechText').textContent = mockData.speech.text;
        document.getElementById('speechConfidence').textContent = mockData.speech.confidence;

        // 更新视觉识别
        const visionResults = document.getElementById('visionResults');
        if (visionResults) {
            visionResults.innerHTML = `
                <div class="small">检测对象: ${mockData.vision.objects.join(', ')}</div>
                <div class="small">OCR文字: ${mockData.vision.text}</div>
                <div class="small">表情分析: ${mockData.vision.emotion}</div>
            `;
        }

        // 更新AI回复
        document.getElementById('aiResponse').textContent = mockData.ai.response;
        document.getElementById('responseTime').textContent = mockData.ai.time;

        // 更新融合结果
        const fusionResult = document.getElementById('fusionResult');
        if (fusionResult) {
            fusionResult.innerHTML = `
                <div class="small">意图: ${mockData.fusion.intent}</div>
                <div class="small">置信度: ${mockData.fusion.confidence}</div>
                <div class="small">动作: ${mockData.fusion.action}</div>
            `;
        }
    }

    generateMockMultimodalData() {
        const speechTexts = [
            "小助手，你好！",
            "什么是加法？", 
            "这道题怎么做？",
            "我不太明白",
            "谢谢老师！"
        ];

        const objects = [
            ['数学书', '铅笔'],
            ['语文书', '练习本'],
            ['英语书', '橡皮'],
            ['计算器', '尺子']
        ];

        const aiResponses = [
            "很好的问题！让我来解释一下...",
            "加法是把两个数合起来的运算...",
            "让我用手势演示给你看...",
            "你说得很对！继续加油！"
        ];

        const random = Math.random();
        
        return {
            speech: {
                text: this.isRunning ? speechTexts[Math.floor(random * speechTexts.length)] : "等待语音输入...",
                confidence: this.isRunning ? `${(85 + Math.random() * 10).toFixed(1)}%` : "--"
            },
            vision: {
                objects: this.isRunning ? objects[Math.floor(random * objects.length)] : [],
                text: this.isRunning ? "3 + 5 = ?" : "",
                emotion: this.isRunning ? ["专注", "高兴", "思考"][Math.floor(random * 3)] : "无"
            },
            ai: {
                response: this.isRunning ? aiResponses[Math.floor(random * aiResponses.length)] : "等待交互...",
                time: this.isRunning ? `${(1.0 + Math.random() * 1.5).toFixed(1)}s` : "--"
            },
            fusion: {
                intent: this.isRunning ? ["学习请求", "问题咨询", "确认反馈"][Math.floor(random * 3)] : "无",
                confidence: this.isRunning ? `${(75 + Math.random() * 20).toFixed(1)}%` : "--",
                action: this.isRunning ? ["解释手势", "指向手势", "鼓励手势"][Math.floor(random * 3)] : "无"
            }
        };
    }

    updateArmStatus() {
        // 模拟机械臂状态
        const armStatus = this.isRunning ? ["执行中", "待机", "运动中"][Math.floor(Math.random() * 3)] : "待机中";
        const position = Array.from({length: 6}, () => (Math.random() * 60 - 30).toFixed(1));
        const gesture = this.isRunning ? ["问候", "指向", "思考", "解释"][Math.floor(Math.random() * 4)] : "无";

        document.getElementById('armStatus').textContent = armStatus;
        document.getElementById('armPosition').textContent = `位置: [${position.join(',')}]`;
        document.getElementById('currentGesture').textContent = gesture;

        // 更新机械臂可视化
        this.updateArmVisualization({
            status: armStatus,
            position: position.map(p => parseFloat(p)),
            current_gesture: gesture
        });
    }

    updateArmVisualization(data) {
        const canvas = document.getElementById('armVisualization');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        // 清空画布
        ctx.clearRect(0, 0, width, height);
        
        // 绘制机械臂简化示意图
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        
        const centerX = width / 2;
        const centerY = height - 20;
        const positions = data.position || [0, 0, 0, 0, 0, 0];
        
        // 绘制基座
        ctx.beginPath();
        ctx.arc(centerX, centerY, 8, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        
        // 绘制关节链
        let currentX = centerX;
        let currentY = centerY;
        const segmentLength = 25;
        
        for (let i = 0; i < 3; i++) {
            const angle = (positions[i] || 0) * Math.PI / 180;
            const nextX = currentX + Math.cos(angle - Math.PI/2) * segmentLength;
            const nextY = currentY + Math.sin(angle - Math.PI/2) * segmentLength;
            
            ctx.beginPath();
            ctx.moveTo(currentX, currentY);
            ctx.lineTo(nextX, nextY);
            ctx.stroke();
            
            // 绘制关节
            ctx.beginPath();
            ctx.arc(nextX, nextY, 4, 0, 2 * Math.PI);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            
            currentX = nextX;
            currentY = nextY;
        }
    }

    startDemo() {
        this.isRunning = true;
        this.addLog('开始演示模式', 'info');
        
        // 更新按钮状态
        document.getElementById('startDemo').disabled = true;
        document.getElementById('pauseDemo').disabled = false;
        document.getElementById('stopDemo').disabled = false;
        
        this.showAlert('演示模式已启动', 'success');
    }

    pauseDemo() {
        this.isRunning = false;
        this.addLog('演示已暂停', 'info');
        
        document.getElementById('startDemo').disabled = false;
        document.getElementById('pauseDemo').disabled = true;
        
        this.showAlert('演示已暂停', 'warning');
    }

    stopDemo() {
        this.isRunning = false;
        this.addLog('演示已停止', 'info');
        
        // 重置按钮状态
        document.getElementById('startDemo').disabled = false;
        document.getElementById('pauseDemo').disabled = true;
        document.getElementById('stopDemo').disabled = true;
        
        this.showAlert('演示已停止', 'secondary');
    }

    switchScenario(scenario) {
        if (scenario) {
            const scenarioNames = {
                'math': '数学学习',
                'chinese': '语文学习', 
                'english': '英语学习',
                'science': '科学学习',
                'free': '自由对话'
            };
            
            this.addLog(`切换到${scenarioNames[scenario]}场景`, 'info');
            this.showAlert(`已切换到${scenarioNames[scenario]}场景`, 'info');
        }
    }

    triggerGesture(gesture) {
        const gestureNames = {
            'greeting': '问候',
            'pointing': '指向',
            'encouragement': '鼓励',
            'thinking': '思考',
            'explanation': '解释'
        };
        
        this.addLog(`执行${gestureNames[gesture]}手势`, 'info');
        
        // 添加视觉反馈
        const btn = document.querySelector(`[data-gesture="${gesture}"]`);
        if (btn) {
            btn.classList.add('active');
            setTimeout(() => btn.classList.remove('active'), 2000);
        }
        
        this.showAlert(`正在执行${gestureNames[gesture]}手势`, 'info');
    }

    testSpeech(text) {
        this.addLog(`测试语音: ${text}`, 'info');
        document.getElementById('testSpeechInput').value = '';
        this.showAlert(`语音测试: ${text}`, 'info');
    }

    addLog(message, level = 'info') {
        const logContainer = document.getElementById('systemLogs');
        if (!logContainer) return;
        
        const time = new Date().toLocaleString();
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry slide-in';
        
        logEntry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-level log-${level}">${level.toUpperCase()}</span>
            <span class="log-message">${message}</span>
        `;
        
        logContainer.insertBefore(logEntry, logContainer.firstChild);
        
        // 限制日志条目数量
        const maxLogs = 20;
        while (logContainer.children.length > maxLogs) {
            logContainer.removeChild(logContainer.lastChild);
        }
    }

    clearLogs() {
        const logContainer = document.getElementById('systemLogs');
        if (logContainer) {
            logContainer.innerHTML = '';
            this.addLog('日志已清空', 'info');
        }
    }

    showAlert(message, type = 'info') {
        // 创建临时警告元素
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = `
            top: 80px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // 自动删除
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 3000);
    }

    showConnectionError() {
        const statusElement = document.getElementById('systemStatus');
        if (statusElement) {
            statusElement.innerHTML = '<i class="fas fa-circle"></i> 连接错误';
            statusElement.className = 'badge bg-danger';
        }
    }

    showWelcomeMessage() {
        this.addLog('智能教育助手机器人展示平台启动成功', 'success');
        this.addLog('欢迎使用蓝桥杯参赛作品演示系统', 'info');
        this.addLog('点击"开始演示"按钮开始功能展示', 'info');
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否有Chart.js
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js未加载，图表功能将不可用');
    }
    
    window.simpleDemoApp = new SimpleDemoApp();
    console.log('简化版演示应用已初始化');
});