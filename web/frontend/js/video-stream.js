/**
 * 实时视频流处理模块
 */

class VideoStreamManager {
    constructor() {
        this.videoElement = null;
        this.canvas = null;
        this.context = null;
        this.stream = null;
        this.isStreaming = false;
        this.detectionOverlay = null;
        this.frameRate = 30;
        this.streamUrl = 'http://localhost:5000/video_stream';
        
        this.init();
    }

    /**
     * 初始化视频流管理器
     */
    init() {
        this.videoElement = document.getElementById('cameraFeed');
        this.detectionOverlay = document.getElementById('detectionOverlay');
        
        if (!this.videoElement) {
            console.warn('视频元素未找到');
            return;
        }

        this.setupVideoElement();
        this.setupDetectionOverlay();
        this.setupEventListeners();
        
        console.log('视频流管理器初始化完成');
    }

    /**
     * 设置视频元素
     */
    setupVideoElement() {
        this.videoElement.addEventListener('loadedmetadata', () => {
            console.log('视频元数据加载完成');
            this.updateCanvasSize();
        });

        this.videoElement.addEventListener('play', () => {
            console.log('视频开始播放');
            this.isStreaming = true;
            this.startDetectionLoop();
        });

        this.videoElement.addEventListener('pause', () => {
            console.log('视频暂停');
            this.isStreaming = false;
        });

        this.videoElement.addEventListener('error', (e) => {
            console.error('视频播放错误:', e);
            this.handleStreamError(e);
        });
    }

    /**
     * 设置检测覆盖层
     */
    setupDetectionOverlay() {
        if (!this.detectionOverlay) return;

        this.context = this.detectionOverlay.getContext('2d');
        this.updateCanvasSize();
    }

    /**
     * 更新画布大小
     */
    updateCanvasSize() {
        if (!this.videoElement || !this.detectionOverlay) return;

        const rect = this.videoElement.getBoundingClientRect();
        
        this.detectionOverlay.width = rect.width;
        this.detectionOverlay.height = rect.height;
        this.detectionOverlay.style.width = rect.width + 'px';
        this.detectionOverlay.style.height = rect.height + 'px';
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 监听窗口大小变化
        window.addEventListener('resize', () => {
            this.updateCanvasSize();
        });

        // 监听WebSocket视觉数据
        if (window.wsManager) {
            window.wsManager.addEventListener('multimodal_data', (data) => {
                if (data.vision) {
                    this.updateDetectionOverlay(data.vision);
                }
            });
        }

        // 视频控制按钮
        const startBtn = document.getElementById('startVideoStream');
        const stopBtn = document.getElementById('stopVideoStream');
        
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startStream());
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopStream());
        }
    }

    /**
     * 启动摄像头流
     */
    async startCameraStream() {
        try {
            // 请求摄像头权限
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: this.frameRate }
                },
                audio: false
            });

            this.videoElement.srcObject = this.stream;
            await this.videoElement.play();
            
            console.log('摄像头流启动成功');
            this.showStreamStatus('本地摄像头', 'success');
            
        } catch (error) {
            console.error('启动摄像头流失败:', error);
            this.handleStreamError(error);
            
            // 回退到网络流
            this.startNetworkStream();
        }
    }

    /**
     * 启动网络视频流
     */
    async startNetworkStream() {
        try {
            // 使用网络视频流URL
            this.videoElement.src = this.streamUrl;
            this.videoElement.load();
            
            console.log('网络视频流启动成功');
            this.showStreamStatus('网络视频流', 'info');
            
        } catch (error) {
            console.error('启动网络视频流失败:', error);
            this.startMockStream();
        }
    }

    /**
     * 启动模拟视频流
     */
    startMockStream() {
        console.log('启动模拟视频流');
        
        // 创建模拟视频数据
        this.generateMockVideoFrame();
        this.showStreamStatus('模拟视频流', 'warning');
    }

    /**
     * 生成模拟视频帧
     */
    generateMockVideoFrame() {
        if (!this.context) return;

        const width = this.detectionOverlay.width;
        const height = this.detectionOverlay.height;

        // 清空画布
        this.context.clearRect(0, 0, width, height);

        // 绘制模拟背景
        const gradient = this.context.createLinearGradient(0, 0, width, height);
        gradient.addColorStop(0, '#1e3c72');
        gradient.addColorStop(1, '#2a5298');
        
        this.context.fillStyle = gradient;
        this.context.fillRect(0, 0, width, height);

        // 绘制模拟对象
        this.drawMockObjects();

        // 绘制时间戳
        this.drawTimestamp();

        // 继续动画
        if (this.isStreaming) {
            setTimeout(() => this.generateMockVideoFrame(), 1000 / this.frameRate);
        }
    }

    /**
     * 绘制模拟对象
     */
    drawMockObjects() {
        const objects = [
            { type: 'book', x: 100, y: 80, w: 120, h: 80, color: '#ff6b6b' },
            { type: 'pencil', x: 250, y: 120, w: 80, h: 20, color: '#4ecdc4' },
            { type: 'paper', x: 180, y: 200, w: 100, h: 100, color: '#45b7d1' }
        ];

        objects.forEach(obj => {
            // 绘制检测框
            this.context.strokeStyle = obj.color;
            this.context.lineWidth = 2;
            this.context.strokeRect(obj.x, obj.y, obj.w, obj.h);

            // 绘制标签
            this.context.fillStyle = obj.color;
            this.context.font = '12px Arial';
            this.context.fillText(obj.type, obj.x, obj.y - 5);

            // 绘制置信度
            const confidence = (85 + Math.random() * 10).toFixed(1);
            this.context.fillText(`${confidence}%`, obj.x + obj.w - 40, obj.y - 5);
        });

        // 绘制OCR文字区域
        this.context.strokeStyle = '#ffd93d';
        this.context.lineWidth = 2;
        this.context.setLineDash([5, 5]);
        this.context.strokeRect(150, 50, 200, 30);
        this.context.setLineDash([]);

        this.context.fillStyle = '#ffd93d';
        this.context.font = '14px Arial';
        this.context.fillText('数学题: 3 + 5 = ?', 155, 70);
    }

    /**
     * 绘制时间戳
     */
    drawTimestamp() {
        const now = new Date();
        const timestamp = now.toLocaleTimeString();

        this.context.fillStyle = 'rgba(255, 255, 255, 0.8)';
        this.context.font = '12px monospace';
        this.context.textAlign = 'right';
        this.context.fillText(
            timestamp, 
            this.detectionOverlay.width - 10, 
            20
        );
        this.context.textAlign = 'left';
    }

    /**
     * 启动流
     */
    async startStream() {
        if (this.isStreaming) {
            console.log('视频流已在运行中');
            return;
        }

        console.log('启动视频流...');
        
        // 优先尝试本地摄像头
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            await this.startCameraStream();
        } else {
            // 回退到网络流
            await this.startNetworkStream();
        }

        this.isStreaming = true;
    }

    /**
     * 停止流
     */
    stopStream() {
        console.log('停止视频流');
        
        this.isStreaming = false;

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.videoElement) {
            this.videoElement.pause();
            this.videoElement.srcObject = null;
            this.videoElement.src = '';
        }

        // 清空检测覆盖层
        if (this.context) {
            this.context.clearRect(0, 0, this.detectionOverlay.width, this.detectionOverlay.height);
        }

        this.showStreamStatus('已停止', 'secondary');
    }

    /**
     * 更新检测覆盖层
     */
    updateDetectionOverlay(visionData) {
        if (!this.context || !visionData) return;

        // 清空之前的绘制内容
        this.context.clearRect(0, 0, this.detectionOverlay.width, this.detectionOverlay.height);

        // 绘制对象检测结果
        if (visionData.objects && visionData.objects.length > 0) {
            this.drawDetectedObjects(visionData.objects);
        }

        // 绘制OCR文字结果
        if (visionData.text) {
            this.drawOCRResults(visionData.text);
        }

        // 绘制人脸检测结果
        if (visionData.faces && visionData.faces.length > 0) {
            this.drawFaceDetection(visionData.faces);
        }

        // 绘制情绪分析结果
        if (visionData.emotion) {
            this.drawEmotionAnalysis(visionData.emotion);
        }
    }

    /**
     * 绘制检测到的对象
     */
    drawDetectedObjects(objects) {
        const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffd93d'];
        
        objects.forEach((obj, index) => {
            const color = colors[index % colors.length];
            
            // 模拟边界框位置
            const bbox = this.getMockBoundingBox(obj, index);
            
            // 绘制边界框
            this.context.strokeStyle = color;
            this.context.lineWidth = 2;
            this.context.strokeRect(bbox.x, bbox.y, bbox.w, bbox.h);

            // 绘制标签背景
            const labelWidth = this.context.measureText(obj).width + 10;
            this.context.fillStyle = color;
            this.context.fillRect(bbox.x, bbox.y - 20, labelWidth, 20);

            // 绘制标签文字
            this.context.fillStyle = 'white';
            this.context.font = '12px Arial';
            this.context.fillText(obj, bbox.x + 5, bbox.y - 5);
        });
    }

    /**
     * 获取模拟边界框
     */
    getMockBoundingBox(objectType, index) {
        const width = this.detectionOverlay.width;
        const height = this.detectionOverlay.height;
        
        // 根据对象类型返回不同的边界框
        const bboxMap = {
            'book': { x: width * 0.1, y: height * 0.2, w: width * 0.3, h: height * 0.25 },
            'pencil': { x: width * 0.5, y: height * 0.4, w: width * 0.15, h: height * 0.1 },
            'paper': { x: width * 0.3, y: height * 0.5, w: width * 0.25, h: height * 0.3 },
            'laptop': { x: width * 0.6, y: height * 0.1, w: width * 0.35, h: height * 0.25 },
            'default': { x: width * 0.2 + index * 50, y: height * 0.3 + index * 30, w: 80, h: 60 }
        };

        return bboxMap[objectType] || bboxMap['default'];
    }

    /**
     * 绘制OCR结果
     */
    drawOCRResults(text) {
        // 模拟OCR文字区域
        const textArea = {
            x: this.detectionOverlay.width * 0.2,
            y: this.detectionOverlay.height * 0.1,
            w: this.detectionOverlay.width * 0.6,
            h: 30
        };

        // 绘制文字区域框
        this.context.strokeStyle = '#ffd93d';
        this.context.lineWidth = 2;
        this.context.setLineDash([5, 5]);
        this.context.strokeRect(textArea.x, textArea.y, textArea.w, textArea.h);
        this.context.setLineDash([]);

        // 绘制识别到的文字
        this.context.fillStyle = '#ffd93d';
        this.context.font = '14px Arial';
        this.context.fillText(text, textArea.x + 5, textArea.y + 20);
    }

    /**
     * 绘制人脸检测结果
     */
    drawFaceDetection(faces) {
        faces.forEach((face, index) => {
            // 模拟人脸位置
            const faceBox = {
                x: this.detectionOverlay.width * 0.7,
                y: this.detectionOverlay.height * 0.2 + index * 100,
                w: 80,
                h: 100
            };

            // 绘制人脸框
            this.context.strokeStyle = '#e74c3c';
            this.context.lineWidth = 2;
            this.context.strokeRect(faceBox.x, faceBox.y, faceBox.w, faceBox.h);

            // 绘制关键点（眼睛、鼻子、嘴巴）
            this.drawFacialLandmarks(faceBox);

            // 显示人脸ID
            this.context.fillStyle = '#e74c3c';
            this.context.font = '12px Arial';
            this.context.fillText(`Face ${index + 1}`, faceBox.x, faceBox.y - 5);
        });
    }

    /**
     * 绘制面部关键点
     */
    drawFacialLandmarks(faceBox) {
        this.context.fillStyle = '#e74c3c';
        
        // 左眼
        this.context.beginPath();
        this.context.arc(faceBox.x + 20, faceBox.y + 30, 3, 0, 2 * Math.PI);
        this.context.fill();

        // 右眼
        this.context.beginPath();
        this.context.arc(faceBox.x + 60, faceBox.y + 30, 3, 0, 2 * Math.PI);
        this.context.fill();

        // 鼻子
        this.context.beginPath();
        this.context.arc(faceBox.x + 40, faceBox.y + 50, 2, 0, 2 * Math.PI);
        this.context.fill();

        // 嘴巴
        this.context.strokeStyle = '#e74c3c';
        this.context.lineWidth = 2;
        this.context.beginPath();
        this.context.arc(faceBox.x + 40, faceBox.y + 70, 15, 0, Math.PI);
        this.context.stroke();
    }

    /**
     * 绘制情绪分析结果
     */
    drawEmotionAnalysis(emotion) {
        const emotionBox = {
            x: 10,
            y: this.detectionOverlay.height - 60,
            w: 150,
            h: 50
        };

        // 绘制情绪框背景
        this.context.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.context.fillRect(emotionBox.x, emotionBox.y, emotionBox.w, emotionBox.h);

        // 绘制情绪文字
        this.context.fillStyle = 'white';
        this.context.font = '14px Arial';
        this.context.fillText(`情绪: ${emotion}`, emotionBox.x + 10, emotionBox.y + 20);

        // 绘制情绪图标
        const emotionIcons = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😠',
            'surprised': '😲',
            'neutral': '😐',
            'confused': '😕',
            'focused': '🤔'
        };

        const icon = emotionIcons[emotion] || '😐';
        this.context.font = '20px Arial';
        this.context.fillText(icon, emotionBox.x + 120, emotionBox.y + 25);
    }

    /**
     * 开始检测循环
     */
    startDetectionLoop() {
        if (!this.isStreaming) return;

        // 模拟定期检测更新
        setTimeout(() => {
            if (this.isStreaming) {
                // 触发模拟检测数据更新
                this.generateMockDetectionData();
                this.startDetectionLoop();
            }
        }, 1000); // 每秒更新一次检测结果
    }

    /**
     * 生成模拟检测数据
     */
    generateMockDetectionData() {
        const mockData = {
            objects: ['book', 'pencil', 'paper'].slice(0, Math.floor(Math.random() * 3) + 1),
            text: Math.random() > 0.5 ? '3 + 5 = ?' : '',
            faces: Math.random() > 0.3 ? [{ id: 1 }] : [],
            emotion: ['happy', 'focused', 'confused', 'neutral'][Math.floor(Math.random() * 4)]
        };

        this.updateDetectionOverlay(mockData);
    }

    /**
     * 显示流状态
     */
    showStreamStatus(status, type) {
        const statusElement = document.querySelector('.video-status .badge');
        if (statusElement) {
            statusElement.className = `badge bg-${type}`;
            statusElement.innerHTML = `<i class="fas fa-circle pulse"></i> ${status}`;
        }
    }

    /**
     * 处理流错误
     */
    handleStreamError(error) {
        console.error('视频流错误:', error);
        
        let errorMessage = '视频流错误';
        if (error.name === 'NotAllowedError') {
            errorMessage = '摄像头权限被拒绝';
        } else if (error.name === 'NotFoundError') {
            errorMessage = '未找到摄像头设备';
        } else if (error.name === 'NetworkError') {
            errorMessage = '网络连接错误';
        }

        this.showStreamStatus(errorMessage, 'danger');
        
        // 显示错误通知
        if (window.wsManager) {
            window.wsManager.showNotification(errorMessage, 'error');
        }
    }

    /**
     * 截取当前帧
     */
    captureFrame() {
        if (!this.videoElement || !this.isStreaming) {
            console.warn('无法截取帧：视频未播放');
            return null;
        }

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = this.videoElement.videoWidth;
        canvas.height = this.videoElement.videoHeight;
        
        ctx.drawImage(this.videoElement, 0, 0);
        
        return canvas.toDataURL('image/png');
    }

    /**
     * 保存截图
     */
    saveScreenshot() {
        const dataUrl = this.captureFrame();
        if (!dataUrl) return;

        const link = document.createElement('a');
        link.download = `screenshot_${new Date().getTime()}.png`;
        link.href = dataUrl;
        link.click();
    }

    /**
     * 销毁视频流管理器
     */
    destroy() {
        this.stopStream();
        
        if (this.videoElement) {
            this.videoElement.removeEventListener('loadedmetadata', this.updateCanvasSize);
            this.videoElement.removeEventListener('play', this.startDetectionLoop);
            this.videoElement.removeEventListener('pause', () => {});
            this.videoElement.removeEventListener('error', this.handleStreamError);
        }
    }
}

// 全局视频流管理器实例
let videoStreamManager = null;

// 初始化视频流管理器
document.addEventListener('DOMContentLoaded', () => {
    videoStreamManager = new VideoStreamManager();
    window.videoStreamManager = videoStreamManager;
    
    // 自动启动视频流
    setTimeout(() => {
        if (videoStreamManager) {
            videoStreamManager.startStream();
        }
    }, 1000);
    
    console.log('视频流管理器已初始化');
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (videoStreamManager) {
        videoStreamManager.destroy();
    }
});