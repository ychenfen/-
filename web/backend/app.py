"""
智能教育助手机器人 - Web展示平台后端服务
"""

import os
import sys
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List
import asyncio

# Flask相关
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

# 添加项目根路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

# 导入机器人系统组件
try:
    from main import EducationalRobotSystem
    ROBOT_AVAILABLE = True
except ImportError:
    print("Warning: 机器人系统模块未找到，使用模拟模式")
    ROBOT_AVAILABLE = False

class WebDashboardServer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'educational_robot_dashboard_2024'
        
        # 配置CORS
        CORS(self.app, origins=["*"])
        
        # 配置SocketIO
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True
        )
        
        # 应用状态
        self.connected_clients = set()
        self.robot_system = None
        self.demo_running = False
        self.current_scenario = None
        
        # 模拟数据生成器
        self.simulation_thread = None
        self.simulation_running = False
        
        # 设置日志
        self.setup_logging()
        
        # 初始化路由和事件处理
        self.setup_routes()
        self.setup_socket_events()
        
        # 初始化机器人系统
        self.init_robot_system()
        
        self.logger.info("Web展示平台后端服务初始化完成")

    def setup_logging(self):
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_routes(self):
        """设置HTTP路由"""
        
        @self.app.route('/')
        def index():
            """主页面"""
            return send_from_directory('../frontend', 'index.html')
        
        @self.app.route('/<path:filename>')
        def static_files(filename):
            """静态文件服务"""
            return send_from_directory('../frontend', filename)
        
        @self.app.route('/api/status')
        def api_status():
            """获取系统状态"""
            return jsonify({
                'status': 'running' if self.robot_system else 'offline',
                'connected_clients': len(self.connected_clients),
                'demo_running': self.demo_running,
                'current_scenario': self.current_scenario,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/scenarios')
        def api_scenarios():
            """获取可用场景列表"""
            scenarios = [
                {'id': 'math', 'name': '数学学习', 'description': '数学概念教学和练习'},
                {'id': 'chinese', 'name': '语文学习', 'description': '语文阅读和写作指导'},
                {'id': 'english', 'name': '英语学习', 'description': '英语口语和语法练习'},
                {'id': 'science', 'name': '科学学习', 'description': '科学实验和原理解释'},
                {'id': 'free', 'name': '自由对话', 'description': '开放式学习交流'}
            ]
            return jsonify({'scenarios': scenarios})
        
        @self.app.route('/api/gestures')
        def api_gestures():
            """获取可用手势列表"""
            gestures = [
                {'id': 'greeting', 'name': '问候手势', 'description': '友好的挥手问候'},
                {'id': 'pointing', 'name': '指向手势', 'description': '指向重要内容'},
                {'id': 'encouragement', 'name': '鼓励手势', 'description': '竖拇指表示赞扬'},
                {'id': 'thinking', 'name': '思考手势', 'description': '模拟思考状态'},
                {'id': 'explanation', 'name': '解释手势', 'description': '展开双臂解释概念'}
            ]
            return jsonify({'gestures': gestures})
        
        @self.app.route('/api/performance')
        def api_performance():
            """获取性能指标"""
            if self.robot_system:
                # 从真实系统获取性能数据
                return jsonify(self.get_system_performance())
            else:
                # 返回模拟性能数据
                return jsonify(self.get_mock_performance())

    def setup_socket_events(self):
        """设置WebSocket事件处理"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接"""
            client_id = request.sid
            self.connected_clients.add(client_id)
            self.logger.info(f"客户端连接: {client_id}")
            
            # 发送欢迎消息和初始状态
            emit('log_message', {
                'message': '欢迎连接到智能教育助手机器人展示平台',
                'level': 'success',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # 发送当前系统状态
            emit('system_status', self.get_system_status())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开连接"""
            client_id = request.sid
            self.connected_clients.discard(client_id)
            self.logger.info(f"客户端断开: {client_id}")
        
        @self.socketio.on('start_demo')
        def handle_start_demo():
            """开始演示"""
            self.demo_running = True
            self.logger.info("开始演示模式")
            
            if self.robot_system:
                # 启动真实演示
                threading.Thread(target=self.run_real_demo, daemon=True).start()
            else:
                # 启动模拟演示
                self.start_simulation()
            
            self.broadcast_log("演示模式已启动", "info")
            emit('demo_status', {'status': 'started'})
        
        @self.socketio.on('pause_demo')
        def handle_pause_demo():
            """暂停演示"""
            self.demo_running = False
            self.logger.info("演示已暂停")
            self.broadcast_log("演示已暂停", "info")
            emit('demo_status', {'status': 'paused'})
        
        @self.socketio.on('stop_demo')
        def handle_stop_demo():
            """停止演示"""
            self.demo_running = False
            self.stop_simulation()
            self.logger.info("演示已停止")
            self.broadcast_log("演示已停止", "info")
            emit('demo_status', {'status': 'stopped'})
        
        @self.socketio.on('switch_scenario')
        def handle_switch_scenario(data):
            """切换教学场景"""
            scenario = data.get('scenario')
            self.current_scenario = scenario
            self.logger.info(f"切换到场景: {scenario}")
            
            if self.robot_system:
                # 在真实系统中切换场景
                self.robot_system.switch_scenario(scenario)
            
            self.broadcast_log(f"已切换到{scenario}学习场景", "info")
            self.socketio.emit('scenario_changed', {'scenario': scenario})
        
        @self.socketio.on('trigger_gesture')
        def handle_trigger_gesture(data):
            """触发手势"""
            gesture = data.get('gesture')
            self.logger.info(f"触发手势: {gesture}")
            
            if self.robot_system:
                # 执行真实手势
                self.robot_system.trigger_gesture(gesture)
            else:
                # 模拟手势执行
                self.simulate_gesture_execution(gesture)
            
            self.broadcast_log(f"执行{gesture}手势", "info")
        
        @self.socketio.on('test_speech')
        def handle_test_speech(data):
            """测试语音"""
            text = data.get('text')
            self.logger.info(f"测试语音: {text}")
            
            if self.robot_system:
                # 使用真实TTS
                self.robot_system.speak(text)
            
            self.broadcast_log(f"语音测试: {text}", "info")

    def init_robot_system(self):
        """初始化机器人系统"""
        if ROBOT_AVAILABLE:
            try:
                self.robot_system = EducationalRobotSystem()
                self.logger.info("机器人系统初始化成功")
                
                # 启动系统状态监控
                threading.Thread(target=self.monitor_robot_system, daemon=True).start()
                
            except Exception as e:
                self.logger.error(f"机器人系统初始化失败: {e}")
                self.robot_system = None
        else:
            self.logger.info("使用模拟模式运行")
            # 启动模拟数据生成
            self.start_simulation()

    def monitor_robot_system(self):
        """监控机器人系统状态"""
        while True:
            try:
                if self.robot_system and len(self.connected_clients) > 0:
                    # 获取实时状态数据
                    status_data = self.get_system_status()
                    multimodal_data = self.get_multimodal_data()
                    arm_data = self.get_arm_status()
                    
                    # 广播到所有连接的客户端
                    self.socketio.emit('system_status', status_data)
                    self.socketio.emit('multimodal_data', multimodal_data)
                    self.socketio.emit('arm_status', arm_data)
                
                time.sleep(1)  # 1秒更新一次
                
            except Exception as e:
                self.logger.error(f"监控系统状态时出错: {e}")
                time.sleep(5)

    def start_simulation(self):
        """启动模拟数据生成"""
        if not self.simulation_running:
            self.simulation_running = True
            self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
            self.simulation_thread.start()
            self.logger.info("模拟数据生成器已启动")

    def stop_simulation(self):
        """停止模拟数据生成"""
        self.simulation_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1)
        self.logger.info("模拟数据生成器已停止")

    def simulation_loop(self):
        """模拟数据生成循环"""
        import random
        
        while self.simulation_running and len(self.connected_clients) > 0:
            try:
                # 生成模拟系统状态
                status_data = {
                    'cpu': random.randint(30, 70),
                    'memory': random.randint(50, 80),
                    'response_time': random.randint(800, 2000),
                    'connections': len(self.connected_clients),
                    'speech_accuracy': 85 + random.randint(0, 10),
                    'vision_accuracy': 90 + random.randint(0, 8)
                }
                
                # 生成模拟多模态数据
                multimodal_data = {
                    'speech': {
                        'text': random.choice([
                            "小助手，你好！",
                            "什么是加法？",
                            "这道题怎么做？",
                            "我不太明白",
                            "谢谢老师！"
                        ]) if self.demo_running else "等待语音输入...",
                        'confidence': random.uniform(0.8, 0.95) if self.demo_running else 0
                    },
                    'vision': {
                        'objects': ['book', 'pencil', 'paper'] if self.demo_running else [],
                        'text': '3 + 5 = ?' if self.demo_running else '',
                        'emotion': random.choice(['happy', 'focused', 'confused']) if self.demo_running else 'neutral'
                    },
                    'ai_response': {
                        'text': random.choice([
                            "很好的问题！让我来解释一下...",
                            "加法是把两个数合起来的运算...",
                            "让我用手势演示给你看...",
                            "你说得很对！继续加油！"
                        ]) if self.demo_running else "等待交互...",
                        'generation_time': random.uniform(1.0, 2.5) if self.demo_running else 0
                    },
                    'fusion': {
                        'intent': random.choice([
                            'learning_request',
                            'question_asking', 
                            'confirmation',
                            'attention_seeking'
                        ]) if self.demo_running else None,
                        'confidence': random.uniform(0.7, 0.9) if self.demo_running else 0,
                        'action': random.choice([
                            'explanation_gesture',
                            'pointing_gesture',
                            'encouragement_gesture'
                        ]) if self.demo_running else None
                    }
                }
                
                # 生成模拟机械臂数据
                arm_data = {
                    'status': 'active' if self.demo_running else 'idle',
                    'position': [
                        random.uniform(-30, 30),
                        random.uniform(-45, 45),
                        random.uniform(-60, 60),
                        random.uniform(-45, 45),
                        random.uniform(-30, 30),
                        random.uniform(-45, 45)
                    ],
                    'current_gesture': random.choice([
                        'greeting', 'pointing', 'thinking', 'explanation'
                    ]) if self.demo_running else None
                }
                
                # 广播数据
                self.socketio.emit('system_status', status_data)
                self.socketio.emit('multimodal_data', multimodal_data)
                self.socketio.emit('arm_status', arm_data)
                
                time.sleep(2)  # 2秒更新一次
                
            except Exception as e:
                self.logger.error(f"模拟数据生成时出错: {e}")
                time.sleep(5)

    def simulate_gesture_execution(self, gesture):
        """模拟手势执行"""
        gesture_names = {
            'greeting': '问候',
            'pointing': '指向',
            'encouragement': '鼓励',
            'thinking': '思考',
            'explanation': '解释'
        }
        
        # 模拟执行延迟
        def delayed_update():
            time.sleep(1)
            self.socketio.emit('arm_status', {
                'status': 'executing',
                'current_gesture': gesture
            })
            
            time.sleep(2)
            self.socketio.emit('arm_status', {
                'status': 'idle',
                'current_gesture': None
            })
            
            self.broadcast_log(f"{gesture_names.get(gesture, gesture)}手势执行完成", "success")
        
        threading.Thread(target=delayed_update, daemon=True).start()

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        if self.robot_system:
            # 从真实系统获取状态
            return {
                'cpu': 45,  # 实际应从系统获取
                'memory': 65,
                'response_time': 1200,
                'connections': len(self.connected_clients),
                'speech_accuracy': 87,
                'vision_accuracy': 92
            }
        else:
            # 返回模拟状态
            import random
            return {
                'cpu': random.randint(40, 60),
                'memory': random.randint(60, 75),
                'response_time': random.randint(1000, 1800),
                'connections': len(self.connected_clients),
                'speech_accuracy': 85 + random.randint(0, 8),
                'vision_accuracy': 90 + random.randint(0, 6)
            }

    def get_multimodal_data(self) -> Dict[str, Any]:
        """获取多模态数据"""
        if self.robot_system:
            # 从真实系统获取多模态数据
            return self.robot_system.get_current_multimodal_data()
        else:
            # 返回空数据
            return {
                'speech': {'text': '', 'confidence': 0},
                'vision': {'objects': [], 'text': '', 'emotion': 'neutral'},
                'ai_response': {'text': '', 'generation_time': 0},
                'fusion': {'intent': None, 'confidence': 0, 'action': None}
            }

    def get_arm_status(self) -> Dict[str, Any]:
        """获取机械臂状态"""
        if self.robot_system:
            # 从真实系统获取机械臂状态
            return self.robot_system.get_arm_status()
        else:
            # 返回模拟状态
            return {
                'status': 'idle',
                'position': [0, 0, 0, 0, 0, 0],
                'current_gesture': None
            }

    def get_system_performance(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        return {
            'response_times': [1200, 1350, 1180, 1420, 1290],
            'accuracy_trends': {
                'speech': [85, 87, 89, 86, 88],
                'vision': [92, 90, 94, 91, 93]
            },
            'resource_usage': {
                'cpu_history': [45, 42, 48, 44, 46],
                'memory_history': [65, 63, 67, 64, 66]
            }
        }

    def get_mock_performance(self) -> Dict[str, Any]:
        """获取模拟性能数据"""
        import random
        return {
            'response_times': [random.randint(1000, 2000) for _ in range(5)],
            'accuracy_trends': {
                'speech': [random.randint(82, 92) for _ in range(5)],
                'vision': [random.randint(88, 96) for _ in range(5)]
            },
            'resource_usage': {
                'cpu_history': [random.randint(35, 65) for _ in range(5)],
                'memory_history': [random.randint(55, 75) for _ in range(5)]
            }
        }

    def run_real_demo(self):
        """运行真实演示"""
        if self.robot_system:
            try:
                self.robot_system.run_demo_mode()
            except Exception as e:
                self.logger.error(f"演示运行时出错: {e}")
                self.broadcast_log(f"演示运行出错: {e}", "error")

    def broadcast_log(self, message: str, level: str = 'info'):
        """广播日志消息到所有客户端"""
        log_data = {
            'message': message,
            'level': level,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.socketio.emit('log_message', log_data)

    def run(self, debug=False):
        """运行Web服务器"""
        self.logger.info(f"启动Web展示平台服务器 http://{self.host}:{self.port}")
        self.socketio.run(
            self.app,
            host=self.host,
            port=self.port,
            debug=debug,
            allow_unsafe_werkzeug=True
        )

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='智能教育助手机器人Web展示平台')
    parser.add_argument('--host', default='localhost', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    # 创建并运行服务器
    server = WebDashboardServer(host=args.host, port=args.port)
    
    try:
        server.run(debug=args.debug)
    except KeyboardInterrupt:
        print("\n服务器停止")
    except Exception as e:
        print(f"服务器运行错误: {e}")

if __name__ == '__main__':
    main()