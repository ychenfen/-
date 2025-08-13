#!/usr/bin/env python3
"""
智能教育助手机器人 - 一键运行演示
"""

import os
import sys
import webbrowser
import threading
import time
import signal
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from datetime import datetime
import random

class EnhancedRobotDemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="frontend", **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
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
        
        # 生成动态API响应
        current_time = time.time()
        
        if self.path == '/api/status':
            data = {
                'status': 'running',
                'connected_clients': 1,
                'demo_running': True,
                'cpu': int(45 + math.sin(current_time / 10) * 15 + random.random() * 10),
                'memory': int(60 + math.cos(current_time / 8) * 10 + random.random() * 8),
                'response_time': int(1000 + math.sin(current_time / 5) * 300 + random.random() * 200),
                'connections': 1,
                'speech_accuracy': int(85 + math.sin(current_time / 20) * 5 + random.random() * 3),
                'vision_accuracy': int(90 + math.cos(current_time / 15) * 4 + random.random() * 2),
                'timestamp': datetime.now().isoformat()
            }
        elif self.path == '/api/scenarios':
            data = {
                'scenarios': [
                    {'id': 'welcome', 'name': '欢迎展示', 'description': '系统介绍和功能概览'},
                    {'id': 'math', 'name': '数学学习', 'description': '数学概念教学和练习'},
                    {'id': 'chinese', 'name': '语文学习', 'description': '语文阅读和古诗词学习'},
                    {'id': 'english', 'name': '英语学习', 'description': '英语口语和发音练习'},
                    {'id': 'science', 'name': '科学学习', 'description': '科学实验和原理解释'}
                ]
            }
        elif self.path == '/api/gestures':
            data = {
                'gestures': [
                    {'id': 'greeting', 'name': '问候手势', 'description': '友好的挥手问候'},
                    {'id': 'pointing', 'name': '指向手势', 'description': '指向重要内容'},
                    {'id': 'encouragement', 'name': '鼓励手势', 'description': '竖拇指表示赞扬'},
                    {'id': 'thinking', 'name': '思考手势', 'description': '托下巴思考状态'},
                    {'id': 'explanation', 'name': '解释手势', 'description': '张开双臂解释概念'},
                    {'id': 'counting', 'name': '数数手势', 'description': '手指计数演示'},
                    {'id': 'writing', 'name': '书写手势', 'description': '模拟书写过程'},
                    {'id': 'reading', 'name': '朗读手势', 'description': '朗读表达手势'}
                ]
            }
        else:
            data = {'message': f'API endpoint: {self.path}', 'timestamp': datetime.now().isoformat()}
        
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        # 简化日志，只显示重要信息
        if 'api' in format % args:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] API: {format % args}")

# 导入数学模块用于生成动态数据
import math

def signal_handler(sig, frame):
    """优雅地处理中断信号"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 收到停止信号，正在关闭服务器...")
    sys.exit(0)

def print_banner():
    """打印启动横幅"""
    print("\n" + "=" * 70)
    print("🤖 智能教育助手机器人 - 增强版Web展示平台")
    print("🏆 第十六届蓝桥杯大赛数字科技创新赛参赛作品")
    print("🚀 基于RISC-V K1芯片的多模态AI教育系统")
    print("=" * 70)

def print_features():
    """打印功能特色"""
    print("\n💡 核心功能特色:")
    print("   ✅ 实时多模态AI数据融合展示")
    print("   ✅ 智能机械臂3D可视化控制")
    print("   ✅ 教学场景自动化演示系统")
    print("   ✅ 语音识别与合成交互测试")
    print("   ✅ 计算机视觉检测结果展示")
    print("   ✅ 系统性能实时监控面板")
    print("   ✅ 响应式移动端界面适配")

def print_tech_specs():
    """打印技术规格"""
    print("\n🔧 技术规格:")
    print("   • 主控芯片: RISC-V K1 (8核, 2.0 TOPS AI算力)")
    print("   • 视觉识别: YOLOv8 + PaddleOCR + OpenCV")
    print("   • 语音处理: Whisper + pyttsx3")
    print("   • 语言模型: Qwen1.5-1.8B (本地推理)")
    print("   • 机械臂: myCobot 280 (6轴, ±0.5mm精度)")
    print("   • 前端技术: HTML5 + CSS3 + JavaScript + Chart.js")
    print("   • 后端技术: Python + HTTP Server + JSON API")

def print_instructions():
    """打印操作说明"""
    print("\n🎮 操作说明:")
    print("   1. 🌐 浏览器会自动打开展示页面")
    print("   2. 🖱️  点击'开始演示'体验完整功能")
    print("   3. 🎛️  使用控制面板测试各项功能:")
    print("      • 切换不同教学场景 (数学/语文/英语/科学)")
    print("      • 控制机械臂执行各种手势动作")
    print("      • 测试语音合成和智能问答")
    print("      • 查看实时性能监控图表")
    print("   4. 📱 支持手机/平板访问 (响应式设计)")
    print("   5. ⌨️  快捷键: Ctrl+1开始, Ctrl+2暂停, Ctrl+3停止")
    print("   6. 🛑 按 Ctrl+C 停止服务器")

def start_server(port=8888):
    """启动增强版服务器"""
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    print_banner()
    print_features()
    print_tech_specs()
    print_instructions()
    
    try:
        # 创建HTTP服务器
        server = HTTPServer(('localhost', port), EnhancedRobotDemoHandler)
        url = f"http://localhost:{port}"
        
        print(f"\n🚀 服务器启动成功！")
        print(f"📊 主界面地址: {url}")
        print(f"🔗 API状态接口: {url}/api/status")
        print(f"📋 场景列表接口: {url}/api/scenarios")
        print(f"🤖 手势列表接口: {url}/api/gestures")
        
        # 延迟打开浏览器
        def open_browser():
            time.sleep(2.5)
            print(f"\n🌐 正在打开浏览器: {url}")
            try:
                webbrowser.open(url)
                print("✅ 浏览器已打开")
            except Exception as e:
                print(f"⚠️  无法自动打开浏览器: {e}")
                print(f"💡 请手动访问: {url}")
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎯 服务器运行中 (端口: {port})")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 等待客户端连接...")
        
        # 启动服务器
        server.serve_forever()
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ 端口 {port} 已被占用")
            print(f"💡 尝试其他端口: python3 {sys.argv[0]} {port + 1}")
            print("🔍 或者关闭占用端口的程序后重试")
        else:
            print(f"❌ 启动失败: {e}")
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ 服务器已停止")
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")

def main():
    """主函数"""
    # 检查当前目录
    if not os.path.exists('frontend'):
        print("❌ 错误: 未找到 frontend 目录")
        print("💡 请确保在 web 目录下运行此脚本")
        print(f"📁 当前目录: {os.getcwd()}")
        return
    
    if not os.path.exists('frontend/index.html'):
        print("❌ 错误: 未找到 frontend/index.html 文件")
        print("💡 请确保前端文件完整")
        return
    
    # 获取端口参数
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    
    # 启动服务器
    start_server(port)

if __name__ == '__main__':
    main()