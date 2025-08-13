/**
 * 智能教育助手机器人 - 详细互动演示引擎
 * 第十六届蓝桥杯大赛数字科技创新赛参赛作品
 * 基于RISC-V K1芯片的多模态AI教育系统
 */

class InteractiveDemoEngine {
    constructor() {
        this.isRunning = false;
        this.currentScenario = 'welcome';
        this.currentStep = 0;
        this.demoInterval = null;
        this.charts = {};
        this.canvasContexts = {};
        
        // 系统状态数据
        this.systemData = {
            cpu: 45,
            memory: 68,
            npu: 32,
            responseTime: 1200,
            speechAccuracy: 92.3,
            visionAccuracy: 88.7,
            connections: 1,
            temperature: 45.6
        };
        
        // 教学场景数据
        this.scenarios = {
            welcome: {
                name: '欢迎展示',
                color: '#6c5ce7',
                steps: [
                    { action: 'speech', content: '欢迎使用智能教育助手机器人！', duration: 3000 },
                    { action: 'gesture', content: 'greeting', duration: 2000 },
                    { action: 'display', content: '系统正在初始化多模态AI引擎...', duration: 2500 },
                    { action: 'vision', content: '检测到用户，开始人脸识别...', duration: 2000 }
                ]
            },
            math: {
                name: '数学学习',
                color: '#0984e3',
                steps: [
                    { action: 'vision', content: '检测到数学教材和练习册', duration: 2000 },
                    { action: 'ocr', content: 'OCR识别: "3 + 5 = ?"', duration: 2000 },
                    { action: 'speech', content: '这是一道基础加法题，让我来为你解答', duration: 3000 },
                    { action: 'gesture', content: 'counting', duration: 3000 },
                    { action: 'display', content: '答案是8，让我用手势演示计数过程', duration: 3000 },
                    { action: 'gesture', content: 'explanation', duration: 2500 }
                ]
            },
            chinese: {
                name: '语文学习',
                color: '#00b894',
                steps: [
                    { action: 'vision', content: '识别到语文课本：《静夜思》', duration: 2000 },
                    { action: 'ocr', content: 'OCR识别古诗词文本', duration: 2000 },
                    { action: 'speech', content: '床前明月光，疑是地上霜...', duration: 4000 },
                    { action: 'gesture', content: 'reading', duration: 3000 },
                    { action: 'emotion', content: '情感分析：思乡之情 (置信度: 94%)', duration: 2500 },
                    { action: 'display', content: '这首诗表达了诗人深深的思乡之情', duration: 3000 }
                ]
            },
            english: {
                name: '英语学习',
                color: '#fdcb6e',
                steps: [
                    { action: 'vision', content: '检测到英语单词卡片', duration: 2000 },
                    { action: 'ocr', content: 'OCR识别: "Hello, World!"', duration: 2000 },
                    { action: 'speech', content: 'Hello! Let me teach you pronunciation', duration: 3000 },
                    { action: 'gesture', content: 'greeting', duration: 2000 },
                    { action: 'pronunciation', content: '发音分析: /həˈloʊ wɜːrld/', duration: 3000 },
                    { action: 'gesture', content: 'encouragement', duration: 2500 }
                ]
            },
            science: {
                name: '科学学习',
                color: '#e17055',
                steps: [
                    { action: 'vision', content: '检测到科学实验器材', duration: 2000 },
                    { action: 'safety', content: '安全检查：护目镜、手套已佩戴', duration: 2500 },
                    { action: 'speech', content: '今天我们来做一个简单的化学实验', duration: 3000 },
                    { action: 'gesture', content: 'demonstration', duration: 3000 },
                    { action: 'monitoring', content: '实时监控实验过程和安全状态', duration: 2500 },
                    { action: 'explanation', content: '实验原理：酸碱中和反应', duration: 3000 }
                ]
            }
        };
        
        // 手势定义
        this.gestures = {
            greeting: { name: '问候手势', description: '友好的挥手问候', duration: 2000 },
            pointing: { name: '指向手势', description: '指向重要内容', duration: 1500 },
            encouragement: { name: '鼓励手势', description: '竖拇指表示赞扬', duration: 2000 },
            thinking: { name: '思考手势', description: '托下巴思考状态', duration: 2500 },
            explanation: { name: '解释手势', description: '张开双臂解释概念', duration: 3000 },
            counting: { name: '数数手势', description: '手指计数演示', duration: 3000 },
            writing: { name: '书写手势', description: '模拟书写过程', duration: 2500 },
            reading: { name: '朗读手势', description: '朗读表达手势', duration: 2000 },
            demonstration: { name: '演示手势', description: '实验演示动作', duration: 3000 }
        };
        
        this.init();
    }
    
    init() {
        console.log('🤖 智能教育助手机器人演示引擎启动');
        this.initializeCanvases();
        this.initializeCharts();
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.initializeInterface();
    }
    
    initializeCanvases() {
        // 初始化检测画布
        const detectionCanvas = document.getElementById('detectionCanvas');
        if (detectionCanvas) {
            this.canvasContexts.detection = detectionCanvas.getContext('2d');
            detectionCanvas.width = 640;
            detectionCanvas.height = 480;
        }
        
        // 初始化机械臂可视化画布
        const armCanvas = document.getElementById('armCanvas');
        if (armCanvas) {
            this.canvasContexts.arm = armCanvas.getContext('2d');
            armCanvas.width = 400;
            armCanvas.height = 300;
            this.drawRobotArm();
        }
        
        // 初始化性能监控画布
        const performanceCanvas = document.getElementById('performanceCanvas');
        if (performanceCanvas) {
            this.canvasContexts.performance = performanceCanvas.getContext('2d');
        }
    }
    
    initializeCharts() {
        // CPU/内存使用率图表
        const resourceCtx = document.getElementById('resourceChart');
        if (resourceCtx) {
            this.charts.resource = new Chart(resourceCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'CPU使用率',
                            data: [],
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            tension: 0.4,
                            fill: true
                        },
                        {
                            label: '内存使用率',
                            data: [],
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            tension: 0.4,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 100 },
                        x: { display: false }
                    },
                    plugins: { legend: { display: true, position: 'top' } }
                }
            });
        }
        
        // 响应时间图表
        const responseCtx = document.getElementById('responseChart');
        if (responseCtx) {
            this.charts.response = new Chart(responseCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '响应时间 (ms)',
                        data: [],
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 3000 },
                        x: { display: false }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }
        
        // AI准确率图表
        const accuracyCtx = document.getElementById('accuracyChart');
        if (accuracyCtx) {
            this.charts.accuracy = new Chart(accuracyCtx, {
                type: 'doughnut',
                data: {
                    labels: ['语音识别', '视觉识别', '文本理解', '决策准确率'],
                    datasets: [{
                        data: [92.3, 88.7, 95.1, 91.2],
                        backgroundColor: [
                            '#3498db',
                            '#2ecc71', 
                            '#f39c12',
                            '#e74c3c'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { fontSize: 10 } }
                    }
                }
            });
        }
    }
    
    setupEventListeners() {
        // 主控制按钮
        const startBtn = document.getElementById('startDemo');
        const pauseBtn = document.getElementById('pauseDemo');
        const stopBtn = document.getElementById('stopDemo');
        
        if (startBtn) startBtn.addEventListener('click', () => this.startDemo());
        if (pauseBtn) pauseBtn.addEventListener('click', () => this.pauseDemo());
        if (stopBtn) stopBtn.addEventListener('click', () => this.stopDemo());
        
        // 场景切换按钮
        document.querySelectorAll('[data-scenario]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const scenario = e.target.getAttribute('data-scenario');
                this.switchScenario(scenario);
            });
        });
        
        // 手势控制按钮
        document.querySelectorAll('[data-gesture]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const gesture = e.target.getAttribute('data-gesture');
                this.executeGesture(gesture);
            });
        });
        
        // 语音合成测试
        const speechBtn = document.getElementById('testSpeech');
        if (speechBtn) {
            speechBtn.addEventListener('click', () => this.testSpeechSynthesis());
        }
        
        // 智能问答测试
        const qaBtn = document.getElementById('testQA');
        if (qaBtn) {
            qaBtn.addEventListener('click', () => this.testIntelligentQA());
        }
        
        // 系统设置
        const settingsBtn = document.getElementById('systemSettings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.openSettings());
        }
    }
    
    startRealTimeUpdates() {
        // 每1.5秒更新一次数据
        setInterval(() => {
            this.updateSystemMetrics();
            this.updateCharts();
            this.updateRobotArmVisualization();
            this.updateVisionData();
        }, 1500);
        
        // 每500ms更新一次界面动效
        setInterval(() => {
            this.updateInterfaceAnimations();
        }, 500);
    }
    
    initializeInterface() {
        this.updateLog('系统启动完成', 'success');
        this.updateLog('多模态AI引擎就绪', 'info');
        this.updateLog('机械臂控制系统已连接', 'info');
        this.updateLog('等待用户交互...', 'warning');
        
        // 设置初始状态
        this.updateSystemStatus('运行中', 'success');
        this.updateCurrentScenario('welcome');
    }
    
    // 核心演示控制方法
    startDemo() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.updateLog('开始完整功能演示', 'success');
        this.updateSystemStatus('演示中', 'info');
        
        // 更新按钮状态
        const startBtn = document.getElementById('startDemo');
        if (startBtn) {
            startBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>演示运行中';
            startBtn.disabled = true;
        }
        
        // 开始自动循环演示
        this.runAutomaticDemo();
    }
    
    pauseDemo() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        if (this.demoInterval) {
            clearInterval(this.demoInterval);
            this.demoInterval = null;
        }
        
        this.updateLog('演示已暂停', 'warning');
        this.updateSystemStatus('暂停中', 'warning');
        
        const startBtn = document.getElementById('startDemo');
        if (startBtn) {
            startBtn.innerHTML = '<i class="fas fa-play me-2"></i>继续演示';
            startBtn.disabled = false;
        }
    }
    
    stopDemo() {
        this.isRunning = false;
        if (this.demoInterval) {
            clearInterval(this.demoInterval);
            this.demoInterval = null;
        }
        
        this.currentStep = 0;
        this.updateLog('演示已停止', 'danger');
        this.updateSystemStatus('运行中', 'success');
        
        const startBtn = document.getElementById('startDemo');
        if (startBtn) {
            startBtn.innerHTML = '<i class="fas fa-play me-2"></i>开始演示';
            startBtn.disabled = false;
        }
    }
    
    runAutomaticDemo() {
        if (!this.isRunning) return;
        
        const scenarios = Object.keys(this.scenarios);
        let currentScenarioIndex = 0;
        
        const runNextScenario = () => {
            if (!this.isRunning) return;
            
            const scenarioKey = scenarios[currentScenarioIndex];
            this.switchScenario(scenarioKey);
            
            // 执行当前场景的所有步骤
            this.runScenarioSteps(scenarioKey, () => {
                currentScenarioIndex = (currentScenarioIndex + 1) % scenarios.length;
                
                // 间隔2秒后执行下一个场景
                setTimeout(runNextScenario, 2000);
            });
        };
        
        runNextScenario();
    }
    
    runScenarioSteps(scenarioKey, callback) {
        const scenario = this.scenarios[scenarioKey];
        let stepIndex = 0;
        
        const executeStep = () => {
            if (!this.isRunning || stepIndex >= scenario.steps.length) {
                if (callback) callback();
                return;
            }
            
            const step = scenario.steps[stepIndex];
            this.executeScenarioStep(step);
            
            stepIndex++;
            setTimeout(executeStep, step.duration);
        };
        
        executeStep();
    }
    
    executeScenarioStep(step) {
        switch (step.action) {
            case 'speech':
                this.simulateSpeechRecognition(step.content);
                this.simulateAIResponse(step.content);
                break;
                
            case 'gesture':
                this.executeGesture(step.content);
                break;
                
            case 'vision':
                this.simulateVisionDetection(step.content);
                break;
                
            case 'ocr':
                this.simulateOCRRecognition(step.content);
                break;
                
            case 'display':
                this.updateTeachingContent(step.content);
                break;
                
            case 'emotion':
                this.simulateEmotionAnalysis(step.content);
                break;
                
            case 'pronunciation':
                this.simulatePronunciationAnalysis(step.content);
                break;
                
            case 'safety':
                this.simulateSafetyCheck(step.content);
                break;
                
            case 'monitoring':
                this.simulateProcessMonitoring(step.content);
                break;
                
            case 'explanation':
                this.updateTeachingContent(step.content);
                break;
        }
        
        this.updateLog(`执行步骤: ${step.content}`, 'info');
    }
    
    // 场景和手势控制
    switchScenario(scenarioKey) {
        if (!this.scenarios[scenarioKey]) return;
        
        this.currentScenario = scenarioKey;
        const scenario = this.scenarios[scenarioKey];
        
        this.updateCurrentScenario(scenarioKey);
        this.updateLog(`切换到${scenario.name}场景`, 'info');
        
        // 更新场景按钮状态
        document.querySelectorAll('[data-scenario]').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-scenario') === scenarioKey) {
                btn.classList.add('active');
            }
        });
        
        // 更新进度条颜色
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.backgroundColor = scenario.color;
        }
    }
    
    executeGesture(gestureKey) {
        if (!this.gestures[gestureKey]) return;
        
        const gesture = this.gestures[gestureKey];
        this.updateCurrentGesture(gesture.name);
        this.updateLog(`执行${gesture.name}: ${gesture.description}`, 'success');
        
        // 更新机械臂状态
        this.updateArmStatus('执行中');
        
        // 动画效果
        setTimeout(() => {
            this.updateArmStatus('就绪');
            this.updateCurrentGesture('待机');
        }, gesture.duration);
        
        // 更新机械臂可视化
        this.animateRobotArm(gestureKey);
    }
    
    // 模拟多模态AI功能
    simulateSpeechRecognition(text) {
        const confidence = (85 + Math.random() * 10).toFixed(1);
        this.updateSpeechData(text, confidence);
    }
    
    simulateVisionDetection(content) {
        this.updateVisionData(content);
        this.drawDetectionResults();
    }
    
    simulateOCRRecognition(content) {
        const ocrResult = content.replace('OCR识别: ', '');
        this.updateOCRData(ocrResult);
    }
    
    simulateAIResponse(content) {
        setTimeout(() => {
            this.updateAIResponse(content);
        }, 500 + Math.random() * 1000);
    }
    
    simulateEmotionAnalysis(content) {
        this.updateEmotionData(content);
    }
    
    simulatePronunciationAnalysis(content) {
        this.updatePronunciationData(content);
    }
    
    simulateSafetyCheck(content) {
        this.updateSafetyStatus(content);
    }
    
    simulateProcessMonitoring(content) {
        this.updateProcessMonitoring(content);
    }
    
    // 界面更新方法
    updateSystemMetrics() {
        const time = Date.now();
        
        // 生成动态数据
        this.systemData.cpu = Math.max(20, Math.min(90, 
            45 + Math.sin(time / 10000) * 15 + (Math.random() - 0.5) * 10));
        this.systemData.memory = Math.max(30, Math.min(85, 
            68 + Math.cos(time / 8000) * 10 + (Math.random() - 0.5) * 8));
        this.systemData.npu = Math.max(15, Math.min(70, 
            32 + Math.sin(time / 12000) * 15 + (Math.random() - 0.5) * 10));
        this.systemData.responseTime = Math.max(800, Math.min(2500, 
            1200 + Math.sin(time / 5000) * 300 + (Math.random() - 0.5) * 200));
        
        // 更新界面显示
        this.updateElement('cpuUsage', `${this.systemData.cpu.toFixed(0)}%`);
        this.updateElement('memoryUsage', `${this.systemData.memory.toFixed(0)}%`);
        this.updateElement('npuUsage', `${this.systemData.npu.toFixed(0)}%`);
        this.updateElement('responseTime', `${this.systemData.responseTime.toFixed(0)}ms`);
        this.updateElement('temperature', `${this.systemData.temperature.toFixed(1)}°C`);
        this.updateElement('connections', this.systemData.connections);
    }
    
    updateCharts() {
        const timestamp = new Date().toLocaleTimeString();
        
        // 更新资源使用图表
        if (this.charts.resource) {
            const chart = this.charts.resource;
            chart.data.labels.push(timestamp);
            chart.data.datasets[0].data.push(this.systemData.cpu);
            chart.data.datasets[1].data.push(this.systemData.memory);
            
            if (chart.data.labels.length > 20) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
                chart.data.datasets[1].data.shift();
            }
            
            chart.update('none');
        }
        
        // 更新响应时间图表
        if (this.charts.response) {
            const chart = this.charts.response;
            chart.data.labels.push(timestamp);
            chart.data.datasets[0].data.push(this.systemData.responseTime);
            
            if (chart.data.labels.length > 15) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            
            chart.update('none');
        }
        
        // 更新准确率数据
        if (this.charts.accuracy) {
            const speechAcc = 85 + Math.sin(Date.now() / 20000) * 5 + Math.random() * 3;
            const visionAcc = 90 + Math.cos(Date.now() / 15000) * 4 + Math.random() * 2;
            
            this.charts.accuracy.data.datasets[0].data = [
                speechAcc, visionAcc, 95.1, 91.2
            ];
            this.charts.accuracy.update('none');
            
            this.updateElement('speechAccuracy', `${speechAcc.toFixed(1)}%`);
            this.updateElement('visionAccuracy', `${visionAcc.toFixed(1)}%`);
        }
    }
    
    drawRobotArm() {
        const canvas = document.getElementById('armCanvas');
        if (!canvas) return;
        
        const ctx = this.canvasContexts.arm;
        const width = canvas.width;
        const height = canvas.height;
        
        ctx.clearRect(0, 0, width, height);
        
        // 绘制背景
        const gradient = ctx.createLinearGradient(0, 0, width, height);
        gradient.addColorStop(0, '#667eea');
        gradient.addColorStop(1, '#764ba2');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
        
        // 绘制机械臂
        const time = Date.now() * 0.001;
        const centerX = width / 2;
        const centerY = height - 50;
        
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 6;
        ctx.lineCap = 'round';
        ctx.fillStyle = '#ffffff';
        
        // 基座
        ctx.beginPath();
        ctx.arc(centerX, centerY, 15, 0, 2 * Math.PI);
        ctx.fill();
        
        // 机械臂段
        let currentX = centerX;
        let currentY = centerY;
        
        const segments = [
            { length: 60, angle: Math.sin(time * 0.5) * 30 },
            { length: 50, angle: Math.cos(time * 0.7) * 25 },
            { length: 40, angle: Math.sin(time * 0.9) * 20 },
            { length: 30, angle: Math.cos(time * 1.1) * 15 }
        ];
        
        segments.forEach((segment, i) => {
            const angle = (segment.angle - 90) * Math.PI / 180;
            const nextX = currentX + Math.cos(angle) * segment.length;
            const nextY = currentY + Math.sin(angle) * segment.length;
            
            ctx.beginPath();
            ctx.moveTo(currentX, currentY);
            ctx.lineTo(nextX, nextY);
            ctx.stroke();
            
            ctx.beginPath();
            ctx.arc(nextX, nextY, 8, 0, 2 * Math.PI);
            ctx.fill();
            
            currentX = nextX;
            currentY = nextY;
        });
        
        // 末端执行器
        ctx.beginPath();
        ctx.arc(currentX, currentY, 12, 0, 2 * Math.PI);
        ctx.fillStyle = '#f39c12';
        ctx.fill();
    }
    
    animateRobotArm(gestureKey) {
        // 根据手势类型创建不同的动画效果
        const animationDuration = this.gestures[gestureKey]?.duration || 2000;
        const startTime = Date.now();
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            if (elapsed < animationDuration) {
                this.drawRobotArm();
                requestAnimationFrame(animate);
            }
        };
        
        animate();
    }
    
    updateRobotArmVisualization() {
        this.drawRobotArm();
    }
    
    drawDetectionResults() {
        const canvas = document.getElementById('detectionCanvas');
        if (!canvas) return;
        
        const ctx = this.canvasContexts.detection;
        const width = canvas.width;
        const height = canvas.height;
        
        ctx.clearRect(0, 0, width, height);
        
        // 模拟检测框
        const detections = [
            { x: 100, y: 80, width: 120, height: 80, label: '教科书', confidence: 0.92 },
            { x: 300, y: 150, width: 80, height: 60, label: '铅笔', confidence: 0.87 },
            { x: 450, y: 200, width: 100, height: 70, label: '练习本', confidence: 0.95 }
        ];
        
        detections.forEach(det => {
            // 绘制检测框
            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            ctx.strokeRect(det.x, det.y, det.width, det.height);
            
            // 绘制标签
            ctx.fillStyle = '#00ff00';
            ctx.font = '14px Arial';
            ctx.fillText(`${det.label} ${(det.confidence * 100).toFixed(0)}%`, 
                        det.x, det.y - 5);
        });
    }
    
    updateVisionData() {
        const visionTexts = [
            '检测对象: 数学书, 计算器, 铅笔<br>OCR文字: "2x + 3 = 7"<br>表情分析: 专注 (88%)',
            '检测对象: 语文书, 字典<br>OCR文字: "床前明月光"<br>表情分析: 陶醉 (92%)',
            '检测对象: 英语书, 单词卡<br>OCR文字: "Hello World"<br>表情分析: 练习 (86%)',
            '检测对象: 科学实验器材<br>OCR文字: "化学反应"<br>表情分析: 好奇 (90%)'
        ];
        
        const randomIndex = Math.floor(Math.random() * visionTexts.length);
        this.updateElement('visionResults', visionTexts[randomIndex]);
    }
    
    updateInterfaceAnimations() {
        // 更新脉冲动画
        const pulseElements = document.querySelectorAll('.pulse');
        pulseElements.forEach(el => {
            el.style.opacity = 0.5 + Math.sin(Date.now() / 1000) * 0.5;
        });
        
        // 更新进度条
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar && this.isRunning) {
            const progress = 30 + (Math.sin(Date.now() / 3000) * 30) + 20;
            progressBar.style.width = `${progress}%`;
        }
    }
    
    // 测试功能
    testSpeechSynthesis() {
        const input = document.getElementById('speechInput');
        const text = input ? input.value : '这是语音合成测试';
        
        this.updateLog(`语音合成测试: "${text}"`, 'info');
        this.simulateAIResponse(`正在合成语音: "${text}"`);
        
        // 模拟语音播放
        setTimeout(() => {
            this.updateLog('语音播放完成', 'success');
        }, 2000);
    }
    
    testIntelligentQA() {
        const questions = [
            '什么是加法？',
            '这首诗的作者是谁？',
            'How do you say hello in English?',
            '这个实验的原理是什么？'
        ];
        
        const answers = [
            '加法是将两个或多个数相加得到总和的数学运算',
            '这首《静夜思》的作者是唐代诗人李白',
            'You can say "Hello" or "Hi" to greet someone in English',
            '这是酸碱中和反应，产生盐和水'
        ];
        
        const randomIndex = Math.floor(Math.random() * questions.length);
        const question = questions[randomIndex];
        const answer = answers[randomIndex];
        
        this.updateLog(`智能问答测试: ${question}`, 'info');
        this.simulateSpeechRecognition(question);
        
        setTimeout(() => {
            this.simulateAIResponse(answer);
            this.updateLog('问答回复完成', 'success');
        }, 1500);
    }
    
    openSettings() {
        this.updateLog('打开系统设置面板', 'info');
        // 这里可以添加设置面板的逻辑
    }
    
    // 辅助方法
    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = content;
        }
    }
    
    updateLog(message, type = 'info') {
        const logContainer = document.getElementById('systemLogs');
        if (!logContainer) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        const typeClass = {
            'success': 'text-success',
            'info': 'text-info', 
            'warning': 'text-warning',
            'danger': 'text-danger'
        }[type] || 'text-muted';
        
        logEntry.innerHTML = `
            <span class="log-time">${timestamp}</span>
            <span class="log-level ${typeClass}">[${type.toUpperCase()}]</span>
            <span class="log-message">${message}</span>
        `;
        
        logContainer.insertBefore(logEntry, logContainer.firstChild);
        
        // 限制日志数量
        while (logContainer.children.length > 15) {
            logContainer.removeChild(logContainer.lastChild);
        }
    }
    
    updateSystemStatus(status, type) {
        this.updateElement('systemStatus', `<i class="fas fa-circle pulse"></i> ${status}`);
    }
    
    updateCurrentScenario(scenarioKey) {
        const scenario = this.scenarios[scenarioKey];
        if (scenario) {
            this.updateElement('currentScenario', scenario.name);
        }
    }
    
    updateCurrentGesture(gestureName) {
        this.updateElement('currentGesture', gestureName);
    }
    
    updateArmStatus(status) {
        this.updateElement('armStatus', status);
    }
    
    updateSpeechData(text, confidence) {
        this.updateElement('speechText', text);
        this.updateElement('speechConfidence', `${confidence}%`);
    }
    
    updateAIResponse(response) {
        this.updateElement('aiResponse', response);
        this.updateElement('responseTime', `${(Math.random() * 500 + 800).toFixed(0)}ms`);
    }
    
    updateTeachingContent(content) {
        this.updateElement('teachingContent', content);
    }
    
    updateOCRData(text) {
        // 更新OCR识别结果显示
        const visionResults = document.getElementById('visionResults');
        if (visionResults) {
            const currentContent = visionResults.innerHTML;
            visionResults.innerHTML = currentContent.replace(
                /OCR文字: [^<]*/,
                `OCR文字: "${text}"`
            );
        }
    }
    
    updateEmotionData(emotion) {
        this.updateLog(`情感分析: ${emotion}`, 'info');
    }
    
    updatePronunciationData(pronunciation) {
        this.updateLog(`发音分析: ${pronunciation}`, 'info');
    }
    
    updateSafetyStatus(status) {
        this.updateLog(`安全检查: ${status}`, 'success');
    }
    
    updateProcessMonitoring(status) {
        this.updateLog(`过程监控: ${status}`, 'info');
    }
}

// 页面加载完成后启动演示引擎
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 启动智能教育助手机器人演示系统');
    window.demoEngine = new InteractiveDemoEngine();
    
    // 添加键盘快捷键支持
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey) {
            switch(e.key) {
                case '1':
                    e.preventDefault();
                    window.demoEngine.startDemo();
                    break;
                case '2':
                    e.preventDefault();
                    window.demoEngine.pauseDemo();
                    break;
                case '3':
                    e.preventDefault();
                    window.demoEngine.stopDemo();
                    break;
            }
        }
    });
    
    console.log('✅ 演示系统启动完成，支持快捷键: Ctrl+1开始, Ctrl+2暂停, Ctrl+3停止');
});