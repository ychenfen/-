"""
智能教育助手机器人 - 简化版Web展示平台
用于快速演示，不依赖复杂的依赖包
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import webbrowser

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="../frontend", **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status_data = {
                'status': 'running',
                'connected_clients': 1,
                'demo_running': True,
                'current_scenario': 'demo',
                'timestamp': datetime.now().isoformat(),
                'cpu': 45,
                'memory': 65,
                'response_time': 1200,
                'connections': 1,
                'speech_accuracy': 87,
                'vision_accuracy': 92
            }
            
            self.wfile.write(json.dumps(status_data).encode())
            return
        
        elif self.path == '/api/scenarios':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            scenarios_data = {
                'scenarios': [
                    {'id': 'math', 'name': '数学学习', 'description': '数学概念教学和练习'},
                    {'id': 'chinese', 'name': '语文学习', 'description': '语文阅读和写作指导'},
                    {'id': 'english', 'name': '英语学习', 'description': '英语口语和语法练习'},
                    {'id': 'science', 'name': '科学学习', 'description': '科学实验和原理解释'},
                    {'id': 'free', 'name': '自由对话', 'description': '开放式学习交流'}
                ]
            }
            
            self.wfile.write(json.dumps(scenarios_data).encode())
            return
        
        elif self.path == '/api/gestures':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            gestures_data = {
                'gestures': [
                    {'id': 'greeting', 'name': '问候手势', 'description': '友好的挥手问候'},
                    {'id': 'pointing', 'name': '指向手势', 'description': '指向重要内容'},
                    {'id': 'encouragement', 'name': '鼓励手势', 'description': '竖拇指表示赞扬'},
                    {'id': 'thinking', 'name': '思考手势', 'description': '模拟思考状态'},
                    {'id': 'explanation', 'name': '解释手势', 'description': '展开双臂解释概念'}
                ]
            }
            
            self.wfile.write(json.dumps(gestures_data).encode())
            return
        
        elif self.path == '/api/performance':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            import random
            performance_data = {
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
            
            self.wfile.write(json.dumps(performance_data).encode())
            return
        
        # 默认处理静态文件
        super().do_GET()
    
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

class SimpleEducationalRobotServer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.httpd = None
        
    def start(self):
        """启动简化版服务器"""
        print("=" * 70)
        print("     智能教育助手机器人 - 简化版Web展示平台")
        print("       第十六届蓝桥杯大赛参赛作品展示系统")
        print("=" * 70)
        print()
        
        try:
            # 创建HTTP服务器
            self.httpd = HTTPServer((self.host, self.port), CustomHTTPRequestHandler)
            
            print(f"🚀 服务器启动成功！")
            print(f"📊 访问地址: http://{self.host}:{self.port}")
            print(f"📱 API接口: http://{self.host}:{self.port}/api/status")
            print()
            print("💡 功能特色:")
            print("   • 智能教育助手机器人展示界面")
            print("   • 多模态AI数据可视化")
            print("   • 实时交互控制面板")
            print("   • 系统性能监控")
            print("   • 移动端响应式设计")
            print()
            print("🎮 操作提示:")
            print("   • 界面会自动显示模拟数据")
            print("   • 支持交互式控制测试")
            print("   • 按 Ctrl+C 停止服务")
            print()
            
            # 自动打开浏览器
            threading.Timer(2.0, lambda: webbrowser.open(f'http://{self.host}:{self.port}')).start()
            
            # 启动服务器
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 服务器正在监听 {self.host}:{self.port}...")
            self.httpd.serve_forever()
            
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 收到停止信号，正在关闭服务器...")
            if self.httpd:
                self.httpd.shutdown()
                self.httpd.server_close()
            print("服务器已停止")
        except Exception as e:
            print(f"❌ 服务器启动失败: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='智能教育助手机器人简化版Web展示平台')
    parser.add_argument('--host', default='localhost', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    
    args = parser.parse_args()
    
    # 检查端口是否被占用
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((args.host, args.port))
    sock.close()
    
    if result == 0:
        print(f"❌ 端口 {args.port} 已被占用，请尝试其他端口")
        print(f"例如: python {__file__} --port 8080")
        return
    
    # 启动服务器
    server = SimpleEducationalRobotServer(args.host, args.port)
    server.start()

if __name__ == '__main__':
    main()