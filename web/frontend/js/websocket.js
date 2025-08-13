/**
 * WebSocket实时通信模块
 */

class WebSocketManager {
    constructor(url = 'http://localhost:5000') {
        this.url = url;
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        
        // 事件监听器
        this.eventListeners = {
            'connect': [],
            'disconnect': [],
            'system_status': [],
            'multimodal_data': [],
            'arm_status': [],
            'log_message': [],
            'demo_status': [],
            'scenario_changed': []
        };
        
        this.init();
    }

    /**
     * 初始化WebSocket连接
     */
    init() {
        try {
            this.socket = io(this.url, {
                transports: ['websocket', 'polling'],
                timeout: 10000,
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay
            });

            this.setupEventHandlers();
            console.log('WebSocket管理器初始化完成');
        } catch (error) {
            console.error('WebSocket初始化失败:', error);
            this.handleConnectionError(error);
        }
    }

    /**
     * 设置事件处理器
     */
    setupEventHandlers() {
        // 连接成功
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            console.log('WebSocket连接成功');
            this.updateConnectionIndicator('connected');
            this.emit('connect');
        });

        // 连接断开
        this.socket.on('disconnect', (reason) => {
            this.isConnected = false;
            console.log('WebSocket连接断开:', reason);
            this.updateConnectionIndicator('disconnected');
            this.emit('disconnect', reason);
            
            // 如果不是主动断开，尝试重连
            if (reason !== 'io client disconnect') {
                this.handleReconnection();
            }
        });

        // 连接错误
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket连接错误:', error);
            this.handleConnectionError(error);
        });

        // 重连尝试
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`尝试重连... (${attemptNumber}/${this.maxReconnectAttempts})`);
            this.updateConnectionIndicator('connecting');
        });

        // 重连成功
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`重连成功 (尝试次数: ${attemptNumber})`);
            this.reconnectAttempts = 0;
        });

        // 重连失败
        this.socket.on('reconnect_failed', () => {
            console.error('重连失败，已达到最大重连次数');
            this.updateConnectionIndicator('disconnected');
            this.showReconnectionOptions();
        });

        // 系统状态更新
        this.socket.on('system_status', (data) => {
            this.emit('system_status', data);
        });

        // 多模态数据更新
        this.socket.on('multimodal_data', (data) => {
            this.emit('multimodal_data', data);
        });

        // 机械臂状态更新
        this.socket.on('arm_status', (data) => {
            this.emit('arm_status', data);
        });

        // 日志消息
        this.socket.on('log_message', (data) => {
            this.emit('log_message', data);
        });

        // 演示状态变化
        this.socket.on('demo_status', (data) => {
            this.emit('demo_status', data);
        });

        // 场景变化
        this.socket.on('scenario_changed', (data) => {
            this.emit('scenario_changed', data);
        });

        // Ping-Pong保持连接
        this.socket.on('ping', () => {
            this.socket.emit('pong');
        });
    }

    /**
     * 更新连接状态指示器
     */
    updateConnectionIndicator(status) {
        const indicator = document.getElementById('connectionIndicator');
        if (!indicator) return;

        indicator.className = `connection-indicator ${status}`;
        
        const statusTexts = {
            'connected': '<i class="fas fa-wifi"></i><span>已连接</span>',
            'connecting': '<i class="fas fa-spinner fa-spin"></i><span>连接中...</span>',
            'disconnected': '<i class="fas fa-wifi-slash"></i><span>连接断开</span>'
        };

        indicator.innerHTML = statusTexts[status] || statusTexts['disconnected'];

        // 更新系统状态badge
        const systemStatus = document.getElementById('systemStatus');
        if (systemStatus) {
            switch(status) {
                case 'connected':
                    systemStatus.innerHTML = '<i class="fas fa-circle pulse"></i> 系统运行中';
                    systemStatus.className = 'badge bg-success';
                    break;
                case 'connecting':
                    systemStatus.innerHTML = '<i class="fas fa-circle"></i> 连接中';
                    systemStatus.className = 'badge bg-warning';
                    break;
                case 'disconnected':
                    systemStatus.innerHTML = '<i class="fas fa-circle"></i> 系统离线';
                    systemStatus.className = 'badge bg-danger';
                    break;
            }
        }
    }

    /**
     * 处理连接错误
     */
    handleConnectionError(error) {
        this.isConnected = false;
        this.updateConnectionIndicator('disconnected');
        
        console.error('连接错误详情:', error);
        
        // 显示错误提示
        this.showNotification('连接服务器失败，请检查网络连接', 'error');
    }

    /**
     * 处理重连逻辑
     */
    handleReconnection() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateConnectionIndicator('connecting');
            
            setTimeout(() => {
                if (!this.isConnected) {
                    console.log(`尝试重连... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    this.socket.connect();
                }
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            this.showReconnectionOptions();
        }
    }

    /**
     * 显示重连选项
     */
    showReconnectionOptions() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">连接断开</h5>
                    </div>
                    <div class="modal-body">
                        <p>与服务器的连接已断开，请选择操作：</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="location.reload()">刷新页面</button>
                        <button type="button" class="btn btn-primary" onclick="this.reconnect()">手动重连</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // 显示模态框
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
    }

    /**
     * 手动重连
     */
    reconnect() {
        this.reconnectAttempts = 0;
        this.updateConnectionIndicator('connecting');
        this.socket.connect();
        
        // 关闭所有模态框
        document.querySelectorAll('.modal').forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }

    /**
     * 添加事件监听器
     */
    addEventListener(event, callback) {
        if (this.eventListeners[event]) {
            this.eventListeners[event].push(callback);
        }
    }

    /**
     * 移除事件监听器
     */
    removeEventListener(event, callback) {
        if (this.eventListeners[event]) {
            const index = this.eventListeners[event].indexOf(callback);
            if (index > -1) {
                this.eventListeners[event].splice(index, 1);
            }
        }
    }

    /**
     * 触发事件
     */
    emit(event, data = null) {
        if (this.eventListeners[event]) {
            this.eventListeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`事件处理器错误 (${event}):`, error);
                }
            });
        }
    }

    /**
     * 发送消息到服务器
     */
    send(event, data = {}) {
        if (this.isConnected && this.socket) {
            this.socket.emit(event, data);
            return true;
        } else {
            console.warn('WebSocket未连接，消息发送失败:', event, data);
            this.showNotification('连接断开，操作失败', 'warning');
            return false;
        }
    }

    /**
     * 开始演示
     */
    startDemo() {
        return this.send('start_demo');
    }

    /**
     * 暂停演示
     */
    pauseDemo() {
        return this.send('pause_demo');
    }

    /**
     * 停止演示
     */
    stopDemo() {
        return this.send('stop_demo');
    }

    /**
     * 切换场景
     */
    switchScenario(scenario) {
        return this.send('switch_scenario', { scenario });
    }

    /**
     * 触发手势
     */
    triggerGesture(gesture) {
        return this.send('trigger_gesture', { gesture });
    }

    /**
     * 测试语音
     */
    testSpeech(text) {
        return this.send('test_speech', { text });
    }

    /**
     * 获取连接状态
     */
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            maxAttempts: this.maxReconnectAttempts
        };
    }

    /**
     * 显示通知
     */
    showNotification(message, type = 'info', duration = 5000) {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // 自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, duration);
    }

    /**
     * 监控连接质量
     */
    startConnectionMonitoring() {
        setInterval(() => {
            if (this.isConnected) {
                const startTime = Date.now();
                this.socket.emit('ping', startTime);
                
                this.socket.once('pong', (timestamp) => {
                    const latency = Date.now() - timestamp;
                    this.updateLatencyDisplay(latency);
                });
            }
        }, 5000); // 每5秒检查一次
    }

    /**
     * 更新延迟显示
     */
    updateLatencyDisplay(latency) {
        const latencyElement = document.getElementById('connectionLatency');
        if (latencyElement) {
            latencyElement.textContent = `${latency}ms`;
            
            // 根据延迟设置颜色
            if (latency < 100) {
                latencyElement.className = 'text-success fw-bold';
            } else if (latency < 300) {
                latencyElement.className = 'text-warning fw-bold';
            } else {
                latencyElement.className = 'text-danger fw-bold';
            }
        }
    }

    /**
     * 断开连接
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }

    /**
     * 销毁WebSocket管理器
     */
    destroy() {
        this.disconnect();
        this.eventListeners = {};
        this.socket = null;
    }
}

// 全局WebSocket管理器实例
let wsManager = null;

// 初始化WebSocket管理器
document.addEventListener('DOMContentLoaded', () => {
    wsManager = new WebSocketManager();
    
    // 将管理器暴露到全局
    window.wsManager = wsManager;
    
    // 开始连接监控
    wsManager.startConnectionMonitoring();
    
    console.log('WebSocket管理器已初始化');
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (wsManager) {
        wsManager.destroy();
    }
});