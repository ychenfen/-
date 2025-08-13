#!/usr/bin/env python3
"""
智能教育助手机器人 - 快速启动脚本
"""

import os
import sys
import webbrowser
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from datetime import datetime

class RobotDemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="frontend", **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.handle_api_request()
        else:
            super().do_GET()
    
    def handle_api_request(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # 模拟API响应
        if self.path == '/api/status':
            data = {
                'status': 'running',
                'connected_clients': 1,
                'demo_running': True,
                'cpu': 45 + int(time.time()) % 20,
                'memory': 60 + int(time.time()) % 15,
                'response_time': 1000 + int(time.time()) % 800,
                'connections': 1,
                'speech_accuracy': 85 + int(time.time()) % 10,
                'vision_accuracy': 90 + int(time.time()) % 8,
                'timestamp': datetime.now().isoformat()
            }
        else:
            data = {'message': 'API endpoint'}
        
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        # 简化日志输出
        pass

def start_server(port=8765):
    """启动服务器"""
    print("=" * 60)
    print("🤖 智能教育助手机器人 - Web展示平台")
    print("   第十六届蓝桥杯大赛参赛作品")
    print("=" * 60)
    print()
    
    try:
        server = HTTPServer(('localhost', port), RobotDemoHandler)
        url = f"http://localhost:{port}"
        
        print(f"🚀 服务器启动成功！")
        print(f"📱 访问地址: {url}")
        print()
        print("💡 功能特色:")
        print("   ✅ 实时多模态AI数据展示")
        print("   ✅ 交互式机器人控制面板")
        print("   ✅ 系统性能监控可视化")
        print("   ✅ 移动端响应式设计")
        print("   ✅ 教学场景模拟演示")
        print()
        print("🎮 操作说明:")
        print("   • 点击'开始演示'查看完整功能")
        print("   • 使用控制面板测试各项功能")
        print("   • 支持手机/平板访问展示")
        print("   • 按 Ctrl+C 停止服务器")
        print()
        
        # 延迟打开浏览器
        def open_browser():
            time.sleep(2)
            print(f"🌐 正在打开浏览器: {url}")
            webbrowser.open(url)
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 服务器运行在端口 {port}...")
        server.serve_forever()
        
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在停止服务器...")
        server.shutdown()
        print("✅ 服务器已停止")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ 端口 {port} 已被占用")
            print(f"💡 请尝试其他端口: python3 {sys.argv[0]} {port + 1}")
        else:
            print(f"❌ 启动失败: {e}")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    start_server(port)