/**
 * 智能教育助手机器人 - Web展示平台主应用
 */

class RobotDashboard {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.charts = {};
        this.systemStatus = {
            cpu: 0,
            memory: 0,
            responseTime: 0,
            connections: 0
        };
        
        this.init();
    }

    /**
     * 初始化应用
     */
    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.connectWebSocket();
        this.startStatusUpdates();
        
        console.log('智能教育助手机器人展示平台初始化完成');
        this.addLog('系统初始化完成', 'info');
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 演示控制按钮
        document.getElementById('startDemo')?.addEventListener('click', () => this.startDemo());
        document.getElementById('pauseDemo')?.addEventListener('click', () => this.pauseDemo());
        document.getElementById('stopDemo')?.addEventListener('click', () => this.stopDemo());

        // 场景切换
        document.getElementById('scenarioSelect')?.addEventListener('change', (e) => {
            this.switchScenario(e.target.value);
        });

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

        // 导航切换
        document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchTab(e.target.getAttribute('href'));
            });
        });

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey) {
                switch(e.key) {
                    case '1': this.startDemo(); break;
                    case '2': this.pauseDemo(); break;
                    case '3': this.stopDemo(); break;
                    case 'l': this.clearLogs(); break;
                }
            }
        });
    }

    /**
     * 初始化图表
     */
    initializeCharts() {
        // 响应时间图表
        const ctx = document.getElementById('responseTimeChart')?.getContext('2d');
        if (ctx) {
            this.charts.responseTime = new Chart(ctx, {
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
                            max: 5000,
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
                    },
                    elements: {
                        point: {
                            radius: 0
                        }
                    }
                }
            });
        }
    }

    /**
     * 连接WebSocket
     */
    connectWebSocket() {
        try {
            this.socket = io('http://localhost:5000');
            
            this.socket.on('connect', () => {
                this.isConnected = true;
                this.updateConnectionStatus('connected');
                this.addLog('WebSocket连接成功', 'success');
            });

            this.socket.on('disconnect', () => {
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.addLog('WebSocket连接断开', 'warning');
            });

            this.socket.on('system_status', (data) => {
                this.updateSystemStatus(data);
            });

            this.socket.on('multimodal_data', (data) => {
                this.updateMultimodalDisplay(data);
            });

            this.socket.on('arm_status', (data) => {
                this.updateArmStatus(data);
            });

            this.socket.on('log_message', (data) => {
                this.addLog(data.message, data.level, data.timestamp);
            });
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateConnectionStatus('disconnected');
        }
    }

    /**
     * 更新连接状态
     */
    updateConnectionStatus(status) {
        const indicator = document.getElementById('connectionIndicator');
        const statusElement = document.getElementById('systemStatus');
        
        if (indicator) {
            indicator.className = `connection-indicator ${status}`;
            
            switch(status) {
                case 'connected':
                    indicator.innerHTML = '<i class="fas fa-wifi"></i><span>已连接</span>';
                    statusElement.innerHTML = '<i class="fas fa-circle pulse"></i> 系统运行中';
                    statusElement.className = 'badge bg-success';
                    break;
                case 'connecting':
                    indicator.innerHTML = '<i class="fas fa-wifi"></i><span>连接中...</span>';
                    statusElement.innerHTML = '<i class="fas fa-circle"></i> 连接中';
                    statusElement.className = 'badge bg-warning';
                    break;
                case 'disconnected':
                    indicator.innerHTML = '<i class="fas fa-wifi"></i><span>连接断开</span>';
                    statusElement.innerHTML = '<i class="fas fa-circle"></i> 系统离线';
                    statusElement.className = 'badge bg-danger';
                    break;
            }
        }
    }

    /**
     * 更新系统状态
     */
    updateSystemStatus(data) {
        this.systemStatus = { ...this.systemStatus, ...data };
        
        // 更新状态栏显示
        document.getElementById('cpuUsage').textContent = `${data.cpu}%`;
        document.getElementById('memoryUsage').textContent = `${data.memory}%`;
        document.getElementById('responseTime').textContent = `${data.response_time}ms`;
        document.getElementById('connectionCount').textContent = data.connections || 1;
        document.getElementById('lastUpdate').textContent = `最后更新: ${new Date().toLocaleTimeString()}`;

        // 更新响应时间图表
        this.updateResponseTimeChart(data.response_time);
        
        // 更新准确率显示
        if (data.speech_accuracy) {
            document.getElementById('speechAccuracy').textContent = `${data.speech_accuracy}%`;
        }
        if (data.vision_accuracy) {
            document.getElementById('visionAccuracy').textContent = `${data.vision_accuracy}%`;
        }
    }

    /**
     * 更新响应时间图表
     */
    updateResponseTimeChart(responseTime) {
        if (this.charts.responseTime) {
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
    }

    /**
     * 更新多模态显示
     */
    updateMultimodalDisplay(data) {
        // 语音识别结果
        if (data.speech) {
            document.getElementById('speechText').textContent = data.speech.text || '等待语音输入...';
            document.getElementById('speechConfidence').textContent = 
                data.speech.confidence ? `${(data.speech.confidence * 100).toFixed(1)}%` : '--';
        }

        // 视觉识别结果
        if (data.vision) {
            const visionResults = document.getElementById('visionResults');
            visionResults.innerHTML = `
                <div class="small">检测对象: ${data.vision.objects?.join(', ') || '无'}</div>
                <div class="small">OCR文字: ${data.vision.text || '无'}</div>
                <div class="small">表情分析: ${data.vision.emotion || '无'}</div>
            `;
        }

        // AI回复
        if (data.ai_response) {
            document.getElementById('aiResponse').textContent = data.ai_response.text || '等待交互...';
            document.getElementById('responseTime').textContent = 
                data.ai_response.generation_time ? `${data.ai_response.generation_time.toFixed(2)}s` : '--';
        }

        // 融合结果
        if (data.fusion) {
            const fusionResult = document.getElementById('fusionResult');
            fusionResult.innerHTML = `
                <div class="small">意图: ${data.fusion.intent || '无'}</div>
                <div class="small">置信度: ${data.fusion.confidence ? `${(data.fusion.confidence * 100).toFixed(1)}%` : '--'}</div>
                <div class="small">动作: ${data.fusion.action || '无'}</div>
            `;
        }
    }

    /**
     * 更新机械臂状态
     */
    updateArmStatus(data) {
        document.getElementById('armStatus').textContent = data.status || '待机中';
        document.getElementById('armPosition').textContent = 
            `位置: [${data.position?.map(p => p.toFixed(1)).join(',') || '0,0,0,0,0,0'}]`;
        document.getElementById('currentGesture').textContent = data.current_gesture || '无';
        
        // 更新机械臂可视化
        this.updateArmVisualization(data);
    }

    /**
     * 更新机械臂可视化
     */
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
        
        // 绘制关节链（简化）
        let currentX = centerX;
        let currentY = centerY;
        const segmentLength = 30;
        
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

    /**
     * 开始演示
     */
    startDemo() {
        if (this.socket && this.isConnected) {
            this.socket.emit('start_demo');
            this.addLog('开始演示模式', 'info');
            
            // 更新按钮状态
            document.getElementById('startDemo').disabled = true;
            document.getElementById('pauseDemo').disabled = false;
            document.getElementById('stopDemo').disabled = false;
        } else {
            this.showAlert('请先连接到机器人系统', 'warning');
        }
    }

    /**
     * 暂停演示
     */
    pauseDemo() {
        if (this.socket && this.isConnected) {
            this.socket.emit('pause_demo');
            this.addLog('演示已暂停', 'info');
            
            document.getElementById('startDemo').disabled = false;
            document.getElementById('pauseDemo').disabled = true;
        }
    }

    /**
     * 停止演示
     */
    stopDemo() {
        if (this.socket && this.isConnected) {
            this.socket.emit('stop_demo');
            this.addLog('演示已停止', 'info');
            
            // 重置按钮状态
            document.getElementById('startDemo').disabled = false;
            document.getElementById('pauseDemo').disabled = true;
            document.getElementById('stopDemo').disabled = true;
        }
    }

    /**
     * 切换教学场景
     */
    switchScenario(scenario) {
        if (this.socket && this.isConnected && scenario) {
            this.socket.emit('switch_scenario', { scenario });
            this.addLog(`切换到${scenario}学习场景`, 'info');
        }
    }

    /**
     * 触发手势
     */
    triggerGesture(gesture) {
        if (this.socket && this.isConnected) {
            this.socket.emit('trigger_gesture', { gesture });
            this.addLog(`执行${gesture}手势`, 'info');
            
            // 添加视觉反馈
            const btn = document.querySelector(`[data-gesture="${gesture}"]`);
            if (btn) {
                btn.classList.add('active');
                setTimeout(() => btn.classList.remove('active'), 2000);
            }
        } else {
            this.showAlert('请先连接到机器人系统', 'warning');
        }
    }

    /**
     * 测试语音
     */
    testSpeech(text) {
        if (this.socket && this.isConnected) {
            this.socket.emit('test_speech', { text });
            this.addLog(`测试语音: ${text}`, 'info');
            document.getElementById('testSpeechInput').value = '';
        } else {
            this.showAlert('请先连接到机器人系统', 'warning');
        }
    }

    /**
     * 添加日志条目
     */
    addLog(message, level = 'info', timestamp = null) {
        const logContainer = document.getElementById('systemLogs');
        if (!logContainer) return;
        
        const time = timestamp || new Date().toLocaleString();
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry slide-in';
        
        logEntry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-level log-${level}">${level.toUpperCase()}</span>
            <span class="log-message">${message}</span>
        `;
        
        logContainer.insertBefore(logEntry, logContainer.firstChild);
        
        // 限制日志条目数量
        const maxLogs = 50;
        while (logContainer.children.length > maxLogs) {
            logContainer.removeChild(logContainer.lastChild);
        }
    }

    /**
     * 清空日志
     */
    clearLogs() {
        const logContainer = document.getElementById('systemLogs');
        if (logContainer) {
            logContainer.innerHTML = '';
            this.addLog('日志已清空', 'info');
        }
    }

    /**
     * 显示警告消息
     */
    showAlert(message, type = 'info') {
        // 创建临时警告元素
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // 插入到页面顶部
        document.body.insertBefore(alertDiv, document.body.firstChild);
        
        // 自动删除
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }

    /**
     * 开始状态更新
     */
    startStatusUpdates() {
        // 模拟状态更新（在实际应用中会从WebSocket接收）
        setInterval(() => {
            if (!this.isConnected) {
                // 模拟一些状态数据用于演示
                const mockData = {
                    cpu: Math.floor(Math.random() * 20) + 40,
                    memory: Math.floor(Math.random() * 20) + 60,
                    response_time: Math.floor(Math.random() * 1000) + 1000,
                    connections: 1,
                    speech_accuracy: 85 + Math.floor(Math.random() * 10),
                    vision_accuracy: 90 + Math.floor(Math.random() * 8)
                };
                this.updateSystemStatus(mockData);
            }
        }, 2000);
    }

    /**
     * 切换标签页
     */
    switchTab(tabId) {
        // 移除所有active类
        document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // 添加active类到当前链接
        document.querySelector(`[href="${tabId}"]`)?.classList.add('active');
        
        // 这里可以添加标签页切换逻辑
        this.addLog(`切换到${tabId}页面`, 'info');
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.robotDashboard = new RobotDashboard();
});

// 全局错误处理
window.addEventListener('error', (e) => {
    console.error('应用错误:', e.error);
    if (window.robotDashboard) {
        window.robotDashboard.addLog(`应用错误: ${e.message}`, 'error');
    }
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (window.robotDashboard && window.robotDashboard.socket) {
        window.robotDashboard.socket.disconnect();
    }
});