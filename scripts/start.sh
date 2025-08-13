#!/bin/bash

# 智能教育助手机器人启动脚本
# Usage: ./scripts/start.sh [mode]
# Modes: normal, demo, monitor, debug

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 打印横幅
print_banner() {
    echo "=================================================================="
    echo "           智能教育助手机器人 - 蓝桥杯参赛作品"
    echo "        基于RISC-V K1芯片的多模态AI教育系统"
    echo "=================================================================="
    echo ""
}

# 检查系统环境
check_environment() {
    log_info "检查系统环境..."
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    log_info "Python版本: $python_version"
    
    # 检查必要的硬件设备
    log_info "检查硬件设备..."
    
    # 检查摄像头
    if ls /dev/video* &> /dev/null; then
        log_info "摄像头设备: $(ls /dev/video*)"
    else
        log_warn "未检测到摄像头设备"
    fi
    
    # 检查音频设备
    if command -v aplay &> /dev/null; then
        audio_devices=$(aplay -l 2>/dev/null | grep -c "card" || echo "0")
        log_info "音频设备数量: $audio_devices"
    else
        log_warn "音频系统未配置"
    fi
    
    # 检查串口设备（机械臂）
    if ls /dev/ttyUSB* &> /dev/null; then
        log_info "串口设备: $(ls /dev/ttyUSB*)"
    else
        log_warn "未检测到串口设备（机械臂可能未连接）"
    fi
    
    # 检查GPU/AI加速器
    if command -v nvidia-smi &> /dev/null; then
        log_info "NVIDIA GPU 可用"
    elif ls /dev/npu* &> /dev/null 2>&1; then
        log_info "NPU设备可用"
    else
        log_info "使用CPU进行AI推理"
    fi
}

# 检查依赖项
check_dependencies() {
    log_info "检查Python依赖项..."
    
    # 检查requirements.txt是否存在
    if [[ ! -f "requirements.txt" ]]; then
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    # 检查关键依赖
    critical_deps=("torch" "opencv-python" "transformers" "whisper" "ultralytics")
    
    for dep in "${critical_deps[@]}"; do
        if python3 -c "import $dep" &> /dev/null; then
            log_info "✓ $dep 已安装"
        else
            log_error "✗ $dep 未安装"
            log_info "正在安装依赖项..."
            pip3 install -r requirements.txt
            break
        fi
    done
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    directories=("logs" "models" "knowledge_base" "data" "cache")
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done
}

# 下载模型文件
download_models() {
    log_info "检查AI模型文件..."
    
    models_dir="models"
    
    # 检查YOLOv8模型
    if [[ ! -f "$models_dir/yolov8n.pt" ]]; then
        log_info "下载YOLOv8模型..."
        python3 -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
print('YOLOv8模型下载完成')
"
        mv yolov8n.pt "$models_dir/" 2>/dev/null || true
    fi
    
    # 检查Whisper模型
    log_info "检查Whisper模型（首次使用时自动下载）..."
    
    # 检查Qwen模型
    if [[ ! -d "$models_dir/qwen1.5-1.8b-chat" ]]; then
        log_warn "Qwen模型未找到，将使用在线模型（需要网络连接）"
    fi
}

# 初始化知识库
init_knowledge_base() {
    log_info "初始化教育知识库..."
    
    if [[ ! -f "knowledge_base/sample_knowledge.json" ]]; then
        log_info "创建示例知识库..."
        python3 -c "
import json
import os

sample_knowledge = [
    {
        'title': '加法基础概念',
        'content': '加法是数学中的基本运算之一，表示将两个或多个数值相加得到总和的过程。例如：3 + 5 = 8',
        'subject': 'math',
        'difficulty': 'easy',
        'keywords': ['加法', '运算', '数学', '基础']
    },
    {
        'title': '古诗词欣赏',
        'content': '古诗词是中华文化的瑰宝，通过优美的语言表达深刻的情感和哲理。学习古诗词有助于提高语言文字能力。',
        'subject': 'chinese',
        'difficulty': 'medium',
        'keywords': ['古诗词', '文学', '语文', '传统文化']
    },
    {
        'title': '英语语法基础',
        'content': '英语语法是英语学习的基础，包括词汇、句型、时态等要素。掌握基本语法规则对提高英语能力很重要。',
        'subject': 'english',
        'difficulty': 'medium',
        'keywords': ['英语', '语法', '学习', '基础']
    }
]

os.makedirs('knowledge_base', exist_ok=True)
with open('knowledge_base/sample_knowledge.json', 'w', encoding='utf-8') as f:
    json.dump(sample_knowledge, f, ensure_ascii=False, indent=2)

print('示例知识库创建完成')
"
    fi
}

# 设置权限
set_permissions() {
    log_info "设置文件权限..."
    
    # 确保脚本可执行
    chmod +x scripts/*.sh 2>/dev/null || true
    
    # 设置日志目录权限
    chmod 755 logs/ 2>/dev/null || true
    
    # 设置设备访问权限（需要sudo权限）
    if [[ -c /dev/ttyUSB0 ]]; then
        sudo chmod 666 /dev/ttyUSB0 2>/dev/null || log_warn "无法设置串口权限，可能需要sudo权限"
    fi
}

# 启动系统
start_system() {
    local mode="${1:-normal}"
    
    log_info "启动智能教育助手机器人 (模式: $mode)..."
    
    # 导出Python路径
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    
    # 设置环境变量
    export ROBOT_CONFIG_PATH="$PROJECT_ROOT/config/config.json"
    export ROBOT_LOG_PATH="$PROJECT_ROOT/logs"
    export ROBOT_DATA_PATH="$PROJECT_ROOT/data"
    
    # 根据模式启动
    case $mode in
        "normal")
            log_info "正常模式启动..."
            python3 src/main.py
            ;;
        "demo")
            log_info "演示模式启动..."
            python3 src/main.py --mode demo
            ;;
        "monitor")
            log_info "监控模式启动..."
            python3 src/main.py --mode monitor
            ;;
        "debug")
            log_info "调试模式启动..."
            export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
            python3 -u src/main.py --debug 2>&1 | tee logs/debug_$(date +%Y%m%d_%H%M%S).log
            ;;
        "test")
            log_info "测试模式启动..."
            python3 -m pytest tests/ -v
            ;;
        *)
            log_error "未知模式: $mode"
            echo "可用模式: normal, demo, monitor, debug, test"
            exit 1
            ;;
    esac
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    
    # 清理Python缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # 清理日志文件（保留最近7天）
    find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    log_info "清理完成"
}

# 停止系统
stop_system() {
    log_info "停止智能教育助手机器人..."
    
    # 查找并终止相关进程
    pids=$(pgrep -f "main.py" || true)
    if [[ -n "$pids" ]]; then
        log_info "终止进程: $pids"
        kill $pids
        sleep 2
        
        # 强制终止仍在运行的进程
        pids=$(pgrep -f "main.py" || true)
        if [[ -n "$pids" ]]; then
            log_warn "强制终止进程: $pids"
            kill -9 $pids
        fi
    else
        log_info "没有找到运行中的机器人进程"
    fi
}

# 显示状态
show_status() {
    log_info "系统状态检查..."
    
    # 检查进程状态
    if pgrep -f "main.py" > /dev/null; then
        log_info "✓ 机器人系统正在运行"
        pgrep -f "main.py" | while read pid; do
            log_info "  进程ID: $pid"
        done
    else
        log_info "✗ 机器人系统未运行"
    fi
    
    # 检查系统资源
    if command -v free &> /dev/null; then
        memory_usage=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
        log_info "内存使用率: $memory_usage"
    fi
    
    if command -v df &> /dev/null; then
        disk_usage=$(df -h "$PROJECT_ROOT" | awk 'NR==2{print $5}')
        log_info "磁盘使用率: $disk_usage"
    fi
    
    # 检查日志文件
    if [[ -f "logs/robot.log" ]]; then
        log_size=$(du -h logs/robot.log | cut -f1)
        log_info "日志文件大小: $log_size"
        
        # 显示最近的日志
        log_info "最近日志内容:"
        tail -10 logs/robot.log | while read line; do
            echo "  $line"
        done
    fi
}

# 显示帮助信息
show_help() {
    echo "智能教育助手机器人启动脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  start [mode]  - 启动系统"
    echo "    normal      - 正常运行模式 (默认)"
    echo "    demo        - 演示模式"
    echo "    monitor     - 监控模式"
    echo "    debug       - 调试模式"
    echo "    test        - 测试模式"
    echo ""
    echo "  stop          - 停止系统"
    echo "  restart [mode]- 重启系统"
    echo "  status        - 显示系统状态"
    echo "  check         - 检查环境和依赖"
    echo "  clean         - 清理临时文件"
    echo "  help          - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start demo     # 演示模式启动"
    echo "  $0 check          # 检查环境"
    echo "  $0 status         # 查看状态"
    echo ""
}

# 主函数
main() {
    local command="${1:-start}"
    local mode="${2:-normal}"
    
    print_banner
    
    case $command in
        "start")
            check_environment
            check_dependencies
            create_directories
            download_models
            init_knowledge_base
            set_permissions
            start_system "$mode"
            ;;
        "stop")
            stop_system
            ;;
        "restart")
            stop_system
            sleep 2
            start_system "$mode"
            ;;
        "status")
            show_status
            ;;
        "check")
            check_environment
            check_dependencies
            ;;
        "clean")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 信号处理
trap 'log_info "收到中断信号，正在清理..."; cleanup; exit 0' INT TERM

# 错误处理
trap 'log_error "脚本执行失败，行号: $LINENO"' ERR

# 执行主函数
main "$@"