#!/bin/bash

# 智能教育助手机器人Web展示平台启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    echo "       智能教育助手机器人 - Web展示平台启动器"
    echo "         第十六届蓝桥杯大赛参赛作品展示系统"
    echo "=================================================================="
    echo ""
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    log_info "Python版本: $python_version"
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 未安装"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    log_info "检查并安装依赖项..."
    
    cd "$WEB_ROOT/backend"
    
    if [[ ! -f "requirements.txt" ]]; then
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    # 检查虚拟环境
    if [[ ! -d "venv" ]]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    log_info "安装Python依赖..."
    pip install -r requirements.txt
    
    log_info "依赖安装完成"
}

# 检查端口可用性
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        log_warn "端口 $port 已被占用"
        return 1
    else
        log_info "端口 $port 可用"
        return 0
    fi
}

# 启动后端服务
start_backend() {
    local host=${1:-localhost}
    local port=${2:-5000}
    local debug=${3:-false}
    
    log_info "启动后端服务 (${host}:${port})..."
    
    cd "$WEB_ROOT/backend"
    
    # 激活虚拟环境
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    
    # 设置环境变量
    export FLASK_APP=app.py
    export FLASK_ENV=development
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    
    # 检查端口
    if ! check_port $port; then
        log_error "端口 $port 被占用，请选择其他端口或停止占用进程"
        exit 1
    fi
    
    # 启动服务
    if [[ "$debug" == "true" ]]; then
        log_info "以调试模式启动..."
        python3 app.py --host $host --port $port --debug
    else
        log_info "以生产模式启动..."
        python3 app.py --host $host --port $port
    fi
}

# 打开浏览器
open_browser() {
    local url=$1
    
    log_info "正在打开浏览器: $url"
    
    # 等待服务启动
    sleep 3
    
    # 根据操作系统打开浏览器
    case "$(uname -s)" in
        Darwin)  # macOS
            open "$url"
            ;;
        Linux)   # Linux
            if command -v xdg-open &> /dev/null; then
                xdg-open "$url"
            elif command -v firefox &> /dev/null; then
                firefox "$url" &
            elif command -v google-chrome &> /dev/null; then
                google-chrome "$url" &
            else
                log_warn "无法自动打开浏览器，请手动访问: $url"
            fi
            ;;
        *)       # 其他系统
            log_warn "无法自动打开浏览器，请手动访问: $url"
            ;;
    esac
}

# 显示使用说明
show_usage() {
    cat << EOF
智能教育助手机器人Web展示平台启动脚本

用法: $0 [选项]

选项:
    --host HOST         服务器主机地址 (默认: localhost)
    --port PORT         服务器端口 (默认: 5000)
    --debug             启用调试模式
    --no-browser        不自动打开浏览器
    --install-only      仅安装依赖，不启动服务
    --help              显示此帮助信息

示例:
    $0                          # 使用默认设置启动
    $0 --host 0.0.0.0 --port 8080  # 指定主机和端口
    $0 --debug                  # 调试模式启动
    $0 --install-only           # 仅安装依赖

访问地址:
    主界面: http://localhost:5000
    API文档: http://localhost:5000/api/status

功能特色:
    ✅ 实时多模态数据展示
    ✅ 交互式机器人控制
    ✅ 性能监控和可视化
    ✅ WebSocket实时通信
    ✅ 响应式移动端适配

EOF
}

# 检查系统依赖
check_system_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查必要的系统工具
    local deps=("curl" "lsof")
    
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            log_warn "$dep 未安装，可能影响某些功能"
        else
            log_debug "$dep 已安装"
        fi
    done
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    local dirs=("$WEB_ROOT/logs" "$WEB_ROOT/static" "$WEB_ROOT/temp")
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_debug "创建目录: $dir"
        fi
    done
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    
    # 清理临时文件
    find "$WEB_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    find "$WEB_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # 清理日志文件（保留最近3天）
    find "$WEB_ROOT/logs" -name "*.log" -mtime +3 -delete 2>/dev/null || true
    
    log_info "清理完成"
}

# 显示服务信息
show_service_info() {
    local host=$1
    local port=$2
    
    cat << EOF

🚀 Web展示平台启动成功！

📊 服务信息:
   • 主界面: http://${host}:${port}
   • API状态: http://${host}:${port}/api/status
   • WebSocket: ws://${host}:${port}/socket.io

🎮 主要功能:
   • 实时多模态数据展示
   • 交互式机器人控制
   • 系统性能监控
   • 教学场景演示

💡 操作提示:
   • 使用 Ctrl+C 停止服务
   • 访问浏览器查看展示界面
   • 检查控制台日志了解运行状态

📱 移动端:
   • 支持平板和手机访问
   • 响应式设计自动适配

EOF
}

# 主函数
main() {
    local host="localhost"
    local port="5000"
    local debug="false"
    local open_browser_flag="true"
    local install_only="false"
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                host="$2"
                shift 2
                ;;
            --port)
                port="$2"
                shift 2
                ;;
            --debug)
                debug="true"
                shift
                ;;
            --no-browser)
                open_browser_flag="false"
                shift
                ;;
            --install-only)
                install_only="true"
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_banner
    
    # 检查系统环境
    check_system_dependencies
    check_python
    create_directories
    
    # 安装依赖
    install_dependencies
    
    # 如果只是安装依赖，则退出
    if [[ "$install_only" == "true" ]]; then
        log_info "依赖安装完成，退出"
        exit 0
    fi
    
    # 显示服务启动信息
    show_service_info "$host" "$port"
    
    # 在后台打开浏览器
    if [[ "$open_browser_flag" == "true" ]]; then
        open_browser "http://${host}:${port}" &
    fi
    
    # 设置信号处理
    trap 'echo ""; log_info "正在停止服务..."; cleanup; exit 0' INT TERM
    
    # 启动后端服务
    start_backend "$host" "$port" "$debug"
}

# 执行主函数
main "$@"