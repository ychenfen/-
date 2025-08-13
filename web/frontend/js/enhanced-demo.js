/**
 * 增强版智能教育助手机器人演示系统
 * 包含更丰富的交互功能和完善的模块展示
 */

class EnhancedEducationalRobotDemo {
    constructor() {
        this.isRunning = false;
        this.currentScenario = 'welcome';
        this.demoStep = 0;
        this.charts = {};
        this.updateInterval = null;
        this.armAnimation = null;
        
        // 演示场景配置
        this.scenarios = {
            welcome: {
                name: '欢迎展示',
                steps: [
                    { action: 'greeting', message: '欢迎来到智能教育助手机器人演示！', duration: 3000 },
                    { action: 'introduction', message: '我是您的AI教学助手，让我展示我的能力', duration: 4000 },
                    { action: 'ready', message: '准备开始精彩的教学旅程吧！', duration: 3000 }
                ]
            },
            math: {
                name: '数学学习',
                steps: [
                    { action: 'detect_book', message: '我看到了一本数学书！', duration: 3000 },
                    { action: 'read_problem', message: '让我读一下这道题：3 + 5 = ?', duration: 4000 },
                    { action: 'explain_concept', message: '加法就是把两个数合并起来...', duration: 5000 },
                    { action: 'demonstrate', message: '让我用手指演示给你看', duration: 4000 },
                    { action: 'encourage', message: '很好！你学会了加法的概念', duration: 3000 }
                ]
            },
            chinese: {
                name: '语文学习',
                steps: [
                    { action: 'poetry_reading', message: '让我为你朗读一首古诗', duration: 3000 },
                    { action: 'recite_poem', message: '床前明月光，疑是地上霜...', duration: 5000 },
                    { action: 'explain_meaning', message: '这首诗表达了诗人的思乡之情', duration: 4000 },
                    { action: 'emotion_gesture', message: '用手势感受诗歌的意境', duration: 4000 },
                    { action: 'interactive_qa', message: '你能感受到诗人的心情吗？', duration: 3000 }
                ]
            },
            english: {
                name: '英语学习',
                steps: [
                    { action: 'pronunciation', message: 'Let me help you with pronunciation', duration: 3000 },
                    { action: 'word_teaching', message: 'The word is "beautiful" - /ˈbjuːtɪfʊl/', duration: 4000 },
                    { action: 'mouth_shape', message: '注意嘴唇的形状和舌头的位置', duration: 4000 },
                    { action: 'practice', message: 'Now try to say it with me!', duration: 3000 },
                    { action: 'feedback', message: 'Great job! Your pronunciation is improving', duration: 3000 }
                ]
            },
            science: {
                name: '科学学习',
                steps: [
                    { action: 'experiment_intro', message: '今天我们来做一个有趣的实验', duration: 3000 },
                    { action: 'hypothesis', message: '你知道为什么天空是蓝色的吗？', duration: 4000 },
                    { action: 'explanation', message: '这是因为光的散射现象...', duration: 5000 },
                    { action: 'demonstration', message: '让我用手势模拟光的传播', duration: 4000 },
                    { action: 'conclusion', message: '科学就在我们身边！', duration: 3000 }
                ]
            }
        };
        
        // 手势动作库
        this.gestures = {
            greeting: { name: '问候', positions: [0, -30, -45, 0, 45, 0], description: '友好挥手' },
            pointing: { name: '指向', positions: [45, -60, -30, 0, 0, 0], description: '指向黑板或重点' },
            encouragement: { name: '鼓励', positions: [0, -45, -60, 0, 90, 0], description: '竖大拇指' },
            thinking: { name: '思考', positions: [-30, -45, -75, 0, 45, -30], description: '托下巴思考' },
            explanation: { name: '解释', positions: [45, -30, -45, 0, 0, 45], description: '张开双臂解释' },
            counting: { name: '数数', positions: [0, -30, -60, 45, 0, 0], description: '手指计数' },
            writing: { name: '书写', positions: [30, -45, -45, 45, 30, 0], description: '模拟书写' },
            reading: { name: '朗读', positions: [-15, -30, -30, 0, 15, 0], description: '朗读手势' }
        };
        
        this.init();
    }

    init() {
        console.log('初始化增强版教育机器人演示系统...');
        
        this.initializeCharts();
        this.setupEventListeners();
        this.loadScenarios();
        this.startDataUpdates();
        this.showWelcomeMessage();
        
        // 自动开始欢迎演示
        setTimeout(() => {
            this.startScenarioDemo('welcome');
        }, 2000);
        
        console.log('增强版演示系统初始化完成');
    }

    initializeCharts() {
        // 响应时间图表
        const responseCtx = document.getElementById('responseTimeChart');
        if (responseCtx) {
            this.charts.responseTime = new Chart(responseCtx, {
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
                        pointRadius: 3,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 750,
                        easing: 'easeInOutQuart'
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 3000,
                            ticks: {
                                callback: value => value + 'ms'
                            }
                        },
                        x: { display: false }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white'
                        }
                    }
                }
            });
        }

        // 准确率环形图
        const accuracyCtx = document.getElementById('accuracyChart');
        if (accuracyCtx) {
            this.charts.accuracy = new Chart(accuracyCtx, {
                type: 'doughnut',
                data: {
                    labels: ['语音识别', '视觉识别', '意图理解'],
                    datasets: [{
                        data: [87, 92, 85],
                        backgroundColor: ['#28a745', '#17a2b8', '#ffc107'],
                        borderWidth: 0,
                        cutout: '70%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { padding: 15, font: { size: 12 } }
                        },
                        tooltip: {
                            callbacks: {
                                label: context => `${context.label}: ${context.parsed}%`
                            }
                        }
                    }
                }
            });
        }

        // 资源使用条形图
        const resourceCtx = document.getElementById('resourceChart');
        if (resourceCtx) {
            this.charts.resource = new Chart(resourceCtx, {
                type: 'bar',
                data: {
                    labels: ['CPU', '内存', 'NPU', '网络'],
                    datasets: [{
                        label: '使用率',
                        data: [45, 65, 30, 20],
                        backgroundColor: [
                            'rgba(0, 123, 255, 0.8)',
                            'rgba(40, 167, 69, 0.8)',
                            'rgba(255, 193, 7, 0.8)',
                            'rgba(220, 53, 69, 0.8)'
                        ],
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: { callback: value => value + '%' }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }
    }

    setupEventListeners() {
        // 演示控制
        document.getElementById('startDemo')?.addEventListener('click', () => this.startInteractiveDemo());
        document.getElementById('pauseDemo')?.addEventListener('click', () => this.pauseDemo());
        document.getElementById('stopDemo')?.addEventListener('click', () => this.stopDemo());

        // 场景选择
        document.getElementById('scenarioSelect')?.addEventListener('change', (e) => {
            if (e.target.value) {
                this.startScenarioDemo(e.target.value);
            }
        });

        // 手势控制 - 增强版
        document.querySelectorAll('[data-gesture]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const gesture = e.target.getAttribute('data-gesture');
                this.executeGesture(gesture);
            });
        });

        // 语音测试 - 增强版
        document.getElementById('testSpeechBtn')?.addEventListener('click', () => {
            const text = document.getElementById('testSpeechInput')?.value;
            if (text) {
                this.performSpeechTest(text);
            }
        });

        // 智能问答测试
        document.getElementById('askQuestionBtn')?.addEventListener('click', () => {
            this.showQuestionModal();
        });

        // 教学模式切换
        document.querySelectorAll('.teaching-mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.target.getAttribute('data-mode');
                this.switchTeachingMode(mode);
            });
        });

        // 系统设置
        document.getElementById('settingsBtn')?.addEventListener('click', () => {
            this.showSettingsModal();
        });

        // 日志管理
        document.getElementById('clearLogs')?.addEventListener('click', () => this.clearLogs());
        document.getElementById('exportLogs')?.addEventListener('click', () => this.exportLogs());

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case '1': e.preventDefault(); this.startInteractiveDemo(); break;
                    case '2': e.preventDefault(); this.pauseDemo(); break;
                    case '3': e.preventDefault(); this.stopDemo(); break;
                    case 'l': e.preventDefault(); this.clearLogs(); break;
                    case 's': e.preventDefault(); this.showSettingsModal(); break;
                }
            }
        });
    }

    loadScenarios() {
        const select = document.getElementById('scenarioSelect');
        if (select) {
            // 清空现有选项
            select.innerHTML = '<option value="">选择教学场景...</option>';
            
            // 添加场景选项
            Object.entries(this.scenarios).forEach(([key, scenario]) => {
                const option = document.createElement('option');
                option.value = key;
                option.textContent = scenario.name;
                select.appendChild(option);
            });
        }
    }

    startDataUpdates() {
        this.updateInterval = setInterval(() => {
            this.updateSystemMetrics();
            this.updateMultimodalData();
            if (this.isRunning) {
                this.updateArmStatus();
            }
        }, 1500);
    }

    updateSystemMetrics() {
        // 生成动态系统指标
        const now = Date.now();
        const cpu = 40 + Math.sin(now / 10000) * 15 + Math.random() * 10;
        const memory = 60 + Math.cos(now / 8000) * 10 + Math.random() * 8;
        const responseTime = 1000 + Math.sin(now / 5000) * 300 + Math.random() * 200;
        
        // 更新显示
        document.getElementById('cpuUsage').textContent = `${Math.round(cpu)}%`;
        document.getElementById('memoryUsage').textContent = `${Math.round(memory)}%`;
        document.getElementById('responseTime').textContent = `${Math.round(responseTime)}ms`;
        document.getElementById('lastUpdate').textContent = `最后更新: ${new Date().toLocaleTimeString()}`;

        // 更新图表
        this.updateResponseTimeChart(responseTime);
        
        // 更新资源图表
        if (this.charts.resource) {
            this.charts.resource.data.datasets[0].data = [
                Math.round(cpu),
                Math.round(memory),
                30 + Math.random() * 20,  // NPU使用率
                15 + Math.random() * 15   // 网络使用率
            ];
            this.charts.resource.update('none');
        }

        // 更新准确率（模拟学习改进）
        if (this.charts.accuracy) {
            const speechAcc = 85 + Math.sin(now / 20000) * 5 + Math.random() * 3;
            const visionAcc = 90 + Math.cos(now / 15000) * 4 + Math.random() * 2;
            const intentAcc = 82 + Math.sin(now / 18000) * 6 + Math.random() * 4;
            
            this.charts.accuracy.data.datasets[0].data = [
                Math.round(speechAcc),
                Math.round(visionAcc), 
                Math.round(intentAcc)
            ];
            this.charts.accuracy.update('none');
            
            // 更新准确率显示
            document.getElementById('speechAccuracy').textContent = `${Math.round(speechAcc)}%`;
            document.getElementById('visionAccuracy').textContent = `${Math.round(visionAcc)}%`;
        }
    }

    updateResponseTimeChart(responseTime) {
        if (!this.charts.responseTime) return;

        const chart = this.charts.responseTime;
        const now = new Date().toLocaleTimeString();
        
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(Math.round(responseTime));
        
        // 保持30个数据点
        if (chart.data.labels.length > 30) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.update('none');
    }

    updateMultimodalData() {
        const currentScenario = this.scenarios[this.currentScenario];
        const isActive = this.isRunning;
        
        // 语音识别数据
        const speechTexts = isActive ? this.getScenarioSpeechTexts() : ["等待语音输入..."];
        const speechText = speechTexts[Math.floor(Math.random() * speechTexts.length)];
        const speechConf = isActive ? `${(85 + Math.random() * 12).toFixed(1)}%` : "--";
        
        document.getElementById('speechText').textContent = speechText;
        document.getElementById('speechConfidence').textContent = speechConf;

        // 视觉识别数据
        const visionObjects = isActive ? this.getScenarioObjects() : [];
        const ocrText = isActive ? this.getScenarioOCRText() : "";
        const emotion = isActive ? this.getScenarioEmotion() : "平静";
        
        const visionResults = document.getElementById('visionResults');
        if (visionResults) {
            visionResults.innerHTML = `
                <div class="small"><strong>检测对象:</strong> ${visionObjects.join(', ') || '无'}</div>
                <div class="small"><strong>OCR文字:</strong> ${ocrText || '无'}</div>
                <div class="small"><strong>表情分析:</strong> ${emotion}</div>
            `;
        }

        // AI回复数据
        const aiResponses = isActive ? this.getScenarioAIResponses() : ["等待交互..."];
        const aiResponse = aiResponses[Math.floor(Math.random() * aiResponses.length)];
        const genTime = isActive ? `${(1.0 + Math.random() * 1.8).toFixed(1)}s` : "--";
        
        document.getElementById('aiResponse').textContent = aiResponse;
        document.getElementById('responseTime').textContent = genTime;

        // 融合结果数据
        const intents = isActive ? ['学习请求', '问题咨询', '确认反馈', '注意力引导'] : ['无'];
        const intent = intents[Math.floor(Math.random() * intents.length)];
        const confidence = isActive ? `${(75 + Math.random() * 20).toFixed(1)}%` : "--";
        const actions = isActive ? ['解释手势', '指向手势', '鼓励手势', '思考手势'] : ['无'];
        const action = actions[Math.floor(Math.random() * actions.length)];
        
        const fusionResult = document.getElementById('fusionResult');
        if (fusionResult) {
            fusionResult.innerHTML = `
                <div class="small"><strong>意图:</strong> ${intent}</div>
                <div class="small"><strong>置信度:</strong> ${confidence}</div>
                <div class="small"><strong>动作:</strong> ${action}</div>
            `;
        }
    }

    getScenarioSpeechTexts() {
        const texts = {
            welcome: ["你好！", "欢迎使用智能教育助手", "我准备好了"],
            math: ["这道题不会做", "什么是加法？", "能演示一下吗？", "我明白了"],
            chinese: ["这首诗什么意思？", "帮我朗读一下", "我想学古诗", "太美了"],
            english: ["How do you say this?", "发音不准确", "再说一遍", "Thank you"],
            science: ["为什么会这样？", "好神奇啊", "能解释一下吗？", "我懂了"]
        };
        return texts[this.currentScenario] || texts.welcome;
    }

    getScenarioObjects() {
        const objects = {
            welcome: ['机器人'],
            math: ['数学书', '计算器', '铅笔', '练习本'],
            chinese: ['语文书', '字典', '毛笔', '宣纸'],
            english: ['英语书', '单词卡', '录音笔'],
            science: ['实验器材', '显微镜', '试管', '量杯']
        };
        const scenarioObjects = objects[this.currentScenario] || objects.welcome;
        return scenarioObjects.slice(0, Math.floor(Math.random() * scenarioObjects.length) + 1);
    }

    getScenarioOCRText() {
        const texts = {
            welcome: '',
            math: ['3 + 5 = ?', '计算下列各题', '数学练习册', '第一章 加法'][Math.floor(Math.random() * 4)],
            chinese: ['床前明月光', '静夜思', '古诗三百首', '诗词鉴赏'][Math.floor(Math.random() * 4)],
            english: ['Hello World', 'Beautiful', 'Pronunciation', 'English Grammar'][Math.floor(Math.random() * 4)],
            science: ['实验步骤', '科学探究', '假设验证', '结论分析'][Math.floor(Math.random() * 4)]
        };
        return texts[this.currentScenario] || '';
    }

    getScenarioEmotion() {
        const emotions = {
            welcome: ['友好', '热情', '专注'],
            math: ['思考', '专注', '恍然大悟', '困惑'],
            chinese: ['陶醉', '专注', '感动', '思考'],
            english: ['专注', '练习', '困惑', '开心'],
            science: ['好奇', '惊讶', '思考', '兴奋']
        };
        const scenarioEmotions = emotions[this.currentScenario] || emotions.welcome;
        return scenarioEmotions[Math.floor(Math.random() * scenarioEmotions.length)];
    }

    getScenarioAIResponses() {
        const responses = {
            welcome: [
                "欢迎来到智能教育世界！",
                "我是你的AI学习伙伴",
                "准备好开始学习了吗？",
                "让我们一起探索知识的海洋"
            ],
            math: [
                "这是一道基础加法题...",
                "让我用手指演示给你看",
                "数学其实很有趣呢！",
                "你已经掌握了这个概念",
                "我们来练习更多题目吧"
            ],
            chinese: [
                "这首诗表达了诗人的思乡之情",
                "古诗词是中华文化的瑰宝",
                "让我为你朗读这首诗",
                "你能感受到诗歌的意境吗？",
                "中华文字真是博大精深"
            ],
            english: [
                "Let me help you with pronunciation",
                "Practice makes perfect!",
                "Your English is improving!",
                "Try to speak more confidently",
                "Great job on that sentence!"
            ],
            science: [
                "科学就在我们身边",
                "这个现象很有趣，让我解释",
                "通过实验我们能发现真理",
                "你观察得很仔细！",
                "科学探索永无止境"
            ]
        };
        return responses[this.currentScenario] || responses.welcome;
    }

    updateArmStatus() {
        // 根据当前场景更新机械臂状态
        const currentStep = this.scenarios[this.currentScenario]?.steps[this.demoStep];
        const gesture = this.getCurrentGesture(currentStep?.action);
        
        const status = this.isRunning ? ['执行中', '运动中', '定位中'][Math.floor(Math.random() * 3)] : '待机中';
        const position = gesture ? gesture.positions : [0, 0, 0, 0, 0, 0];
        const currentGesture = gesture ? gesture.name : '待机';

        document.getElementById('armStatus').textContent = status;
        document.getElementById('armPosition').textContent = `位置: [${position.map(p => p.toFixed(1)).join(',')}]`;
        document.getElementById('currentGesture').textContent = currentGesture;

        // 更新3D可视化
        this.updateArmVisualization({
            status: status,
            position: position,
            current_gesture: currentGesture
        });
    }

    getCurrentGesture(action) {
        const actionGestureMap = {
            greeting: this.gestures.greeting,
            introduction: this.gestures.explanation,
            detect_book: this.gestures.pointing,
            read_problem: this.gestures.reading,
            explain_concept: this.gestures.explanation,
            demonstrate: this.gestures.counting,
            encourage: this.gestures.encouragement,
            poetry_reading: this.gestures.reading,
            recite_poem: this.gestures.reading,
            explain_meaning: this.gestures.explanation,
            emotion_gesture: this.gestures.explanation,
            pronunciation: this.gestures.explanation,
            word_teaching: this.gestures.pointing,
            mouth_shape: this.gestures.pointing,
            practice: this.gestures.encouragement,
            experiment_intro: this.gestures.explanation,
            hypothesis: this.gestures.thinking,
            explanation: this.gestures.explanation,
            demonstration: this.gestures.pointing
        };
        
        return actionGestureMap[action] || this.gestures.greeting;
    }

    updateArmVisualization(data) {
        const canvas = document.getElementById('armVisualization');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        // 清空画布
        ctx.clearRect(0, 0, width, height);
        
        // 设置绘制样式
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.shadowColor = 'rgba(255, 255, 255, 0.3)';
        ctx.shadowBlur = 5;
        
        const centerX = width / 2;
        const centerY = height - 30;
        const positions = data.position || [0, 0, 0, 0, 0, 0];
        
        // 绘制基座
        ctx.beginPath();
        ctx.arc(centerX, centerY, 12, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        
        // 绘制关节链
        let currentX = centerX;
        let currentY = centerY;
        const segmentLengths = [35, 30, 25, 20];
        const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4'];
        
        for (let i = 0; i < Math.min(4, positions.length); i++) {
            const angle = (positions[i] || 0) * Math.PI / 180;
            const length = segmentLengths[i];
            
            const nextX = currentX + Math.cos(angle - Math.PI/2) * length;
            const nextY = currentY + Math.sin(angle - Math.PI/2) * length;
            
            // 绘制连杆
            ctx.strokeStyle = colors[i];
            ctx.lineWidth = 8 - i * 1.5;
            ctx.beginPath();
            ctx.moveTo(currentX, currentY);
            ctx.lineTo(nextX, nextY);
            ctx.stroke();
            
            // 绘制关节
            ctx.fillStyle = colors[i];
            ctx.beginPath();
            ctx.arc(nextX, nextY, 6 - i, 0, 2 * Math.PI);
            ctx.fill();
            
            currentX = nextX;
            currentY = nextY;
        }
        
        // 绘制末端执行器
        ctx.fillStyle = '#ffd93d';
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(currentX, currentY, 8, 0, 2 * Math.PI);
        ctx.fill();
        
        // 如果在运动，添加轨迹效果
        if (data.status === '执行中' || data.status === '运动中') {
            this.drawMotionTrail(ctx, currentX, currentY);
        }
        
        ctx.shadowBlur = 0;
    }

    drawMotionTrail(ctx, x, y) {
        const time = Date.now() * 0.005;
        const trailLength = 15;
        
        for (let i = 0; i < trailLength; i++) {
            const alpha = (1 - i / trailLength) * 0.6;
            const offset = i * 3;
            const trailX = x + Math.sin(time - offset * 0.1) * 8;
            const trailY = y + Math.cos(time - offset * 0.1) * 5;
            
            ctx.globalAlpha = alpha;
            ctx.fillStyle = '#ffff00';
            ctx.beginPath();
            ctx.arc(trailX, trailY, 2, 0, 2 * Math.PI);
            ctx.fill();
        }
        
        ctx.globalAlpha = 1;
    }

    // 演示控制方法
    startInteractiveDemo() {
        this.isRunning = true;
        this.addLog('开始交互式演示模式', 'success');
        
        // 更新按钮状态
        this.updateDemoButtons(true);
        
        // 开始欢迎场景
        this.startScenarioDemo('welcome');
        
        this.showAlert('🚀 交互式演示已启动！点击不同场景体验各种功能', 'success');
    }

    startScenarioDemo(scenarioKey) {
        if (!this.scenarios[scenarioKey]) return;
        
        this.currentScenario = scenarioKey;
        this.demoStep = 0;
        const scenario = this.scenarios[scenarioKey];
        
        this.addLog(`开始${scenario.name}演示`, 'info');
        
        // 更新场景选择器
        const select = document.getElementById('scenarioSelect');
        if (select) {
            select.value = scenarioKey;
        }
        
        // 执行场景步骤
        this.executeScenarioSteps(scenario);
    }

    executeScenarioSteps(scenario) {
        if (this.demoStep >= scenario.steps.length) {
            this.demoStep = 0;
            this.addLog(`${scenario.name}演示完成`, 'success');
            return;
        }
        
        const step = scenario.steps[this.demoStep];
        this.addLog(`执行: ${step.message}`, 'info');
        
        // 更新AI回复显示
        document.getElementById('aiResponse').textContent = step.message;
        
        // 执行对应的手势
        if (step.action) {
            const gesture = this.getCurrentGesture(step.action);
            if (gesture) {
                this.executeGesture(step.action, false);
            }
        }
        
        // 计划下一步
        setTimeout(() => {
            this.demoStep++;
            if (this.isRunning && this.currentScenario === scenario.name) {
                this.executeScenarioSteps(scenario);
            }
        }, step.duration);
    }

    executeGesture(gestureKey, showFeedback = true) {
        const gesture = this.gestures[gestureKey];
        if (!gesture) return;
        
        if (showFeedback) {
            this.addLog(`执行${gesture.name}手势: ${gesture.description}`, 'info');
        }
        
        // 添加按钮视觉反馈
        const btn = document.querySelector(`[data-gesture="${gestureKey}"]`);
        if (btn) {
            btn.classList.add('active');
            setTimeout(() => btn.classList.remove('active'), 2000);
        }
        
        // 更新机械臂状态
        document.getElementById('armStatus').textContent = '执行中';
        document.getElementById('currentGesture').textContent = gesture.name;
        
        if (showFeedback) {
            this.showAlert(`🤖 正在执行${gesture.name}手势`, 'info');
        }
    }

    performSpeechTest(text) {
        this.addLog(`语音合成测试: "${text}"`, 'info');
        
        // 模拟语音合成过程
        document.getElementById('aiResponse').textContent = `正在合成语音: ${text}`;
        
        setTimeout(() => {
            document.getElementById('aiResponse').textContent = `语音合成完成: ${text}`;
            this.showAlert('🔊 语音合成测试完成', 'success');
        }, 1500);
        
        // 清空输入框
        document.getElementById('testSpeechInput').value = '';
    }

    pauseDemo() {
        this.isRunning = false;
        this.addLog('演示已暂停', 'warning');
        this.updateDemoButtons(false);
        this.showAlert('⏸️ 演示已暂停', 'warning');
    }

    stopDemo() {
        this.isRunning = false;
        this.currentScenario = 'welcome';
        this.demoStep = 0;
        
        this.addLog('演示已停止', 'info');
        this.updateDemoButtons(false, true);
        
        // 重置显示
        document.getElementById('aiResponse').textContent = '等待交互...';
        document.getElementById('armStatus').textContent = '待机中';
        document.getElementById('currentGesture').textContent = '无';
        
        this.showAlert('⏹️ 演示已停止', 'secondary');
    }

    updateDemoButtons(isRunning, isStopped = false) {
        document.getElementById('startDemo').disabled = isRunning;
        document.getElementById('pauseDemo').disabled = !isRunning;
        document.getElementById('stopDemo').disabled = isStopped;
    }

    // 工具方法
    addLog(message, level = 'info', showTime = true) {
        const logContainer = document.getElementById('systemLogs');
        if (!logContainer) return;
        
        const time = showTime ? new Date().toLocaleString() : '';
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry slide-in';
        
        logEntry.innerHTML = `
            ${showTime ? `<span class="log-time">${time}</span>` : ''}
            <span class="log-level log-${level}">${level.toUpperCase()}</span>
            <span class="log-message">${message}</span>
        `;
        
        logContainer.insertBefore(logEntry, logContainer.firstChild);
        
        // 限制日志数量
        const maxLogs = 50;
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

    exportLogs() {
        const logContainer = document.getElementById('systemLogs');
        if (!logContainer) return;
        
        const logs = Array.from(logContainer.children).map(entry => {
            return entry.textContent;
        }).reverse().join('\n');
        
        const blob = new Blob([logs], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `robot_logs_${new Date().toISOString().slice(0, 10)}.txt`;
        link.click();
        URL.revokeObjectURL(url);
        
        this.showAlert('📄 日志已导出', 'success');
    }

    showAlert(message, type = 'info', duration = 4000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = `
            top: 90px;
            right: 20px;
            z-index: 9999;
            min-width: 350px;
            max-width: 500px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            border: none;
            border-left: 4px solid var(--bs-${type});
        `;
        
        alertDiv.innerHTML = `
            <div class="d-flex align-items-center">
                ${this.getAlertIcon(type)}
                <div class="ms-2">${message}</div>
            </div>
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // 自动删除
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }

    getAlertIcon(type) {
        const icons = {
            success: '<i class="fas fa-check-circle text-success"></i>',
            info: '<i class="fas fa-info-circle text-info"></i>',
            warning: '<i class="fas fa-exclamation-triangle text-warning"></i>',
            danger: '<i class="fas fa-exclamation-circle text-danger"></i>',
            secondary: '<i class="fas fa-pause-circle text-secondary"></i>'
        };
        return icons[type] || icons.info;
    }

    showWelcomeMessage() {
        setTimeout(() => {
            this.addLog('🤖 智能教育助手机器人展示系统启动成功', 'success');
            this.addLog('🎓 第十六届蓝桥杯大赛参赛作品', 'info');
            this.addLog('🚀 基于RISC-V K1芯片的多模态AI教育系统', 'info');
            this.addLog('💡 点击"开始演示"体验完整功能', 'info');
        }, 500);
    }
}

// 初始化增强版演示系统
document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js未加载，图表功能将受限');
    }
    
    window.enhancedDemo = new EnhancedEducationalRobotDemo();
    console.log('🎉 增强版智能教育助手机器人演示系统已启动');
});