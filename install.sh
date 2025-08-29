#!/bin/bash

# iKuai Komari 监控代理 v1.0 一键安装脚本
# 从GitHub下载并自动部署

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# GitHub仓库信息
GITHUB_REPO="your-username/ikuai-komari-agent"
GITHUB_BRANCH="main"
DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/archive/refs/heads/${GITHUB_BRANCH}.zip"
TEMP_DIR="/tmp/ikuai_komari_agent_install"

# 显示标题
show_title() {
    clear
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    iKuai Komari 监控代理 v1.0${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}        GitHub一键安装脚本${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}错误: 此脚本需要root权限运行${NC}"
        echo "请使用: sudo $0"
        exit 1
    fi
}

# 检查系统类型
check_system() {
    if [[ ! -f /etc/os-release ]]; then
        echo -e "${RED}错误: 无法检测系统类型${NC}"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "debian" && "$ID" != "ubuntu" && "$ID" != "centos" && "$ID" != "rhel" ]]; then
        echo -e "${YELLOW}警告: 此脚本主要支持Debian/Ubuntu/CentOS系统${NC}"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 安装系统依赖
install_dependencies() {
    echo -e "${BLUE}安装系统依赖...${NC}"
    
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        apt-get update
        apt-get install -y curl wget unzip python3 python3-pip python3-venv
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        yum install -y curl wget unzip python3 python3-pip python3-venv
    elif command -v dnf &> /dev/null; then
        # Fedora
        dnf install -y curl wget unzip python3 python3-pip python3-venv
    else
        echo -e "${RED}错误: 不支持的包管理器${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}系统依赖安装完成${NC}"
}

# 下载项目文件
download_project() {
    echo -e "${BLUE}从GitHub下载项目文件...${NC}"
    
    # 创建临时目录
    mkdir -p "${TEMP_DIR}"
    cd "${TEMP_DIR}"
    
    # 下载项目
    echo -e "${BLUE}下载地址: ${GITHUB_REPO}${NC}"
    if curl -L -o project.zip "${DOWNLOAD_URL}"; then
        echo -e "${GREEN}下载完成${NC}"
    else
        echo -e "${RED}下载失败，请检查网络连接或GitHub仓库地址${NC}"
        exit 1
    fi
    
    # 解压文件
    echo -e "${BLUE}解压文件...${NC}"
    unzip -q project.zip
    rm project.zip
    
    # 查找项目目录
    PROJECT_DIR=$(find . -name "ikuai-komari-agent-*" -type d | head -1)
    if [[ -z "$PROJECT_DIR" ]]; then
        echo -e "${RED}错误: 无法找到项目目录${NC}"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    echo -e "${GREEN}项目文件准备完成${NC}"
}

# 运行部署脚本
run_deploy_script() {
    echo -e "${BLUE}运行部署脚本...${NC}"
    
    if [[ -f "deploy.sh" ]]; then
        chmod +x deploy.sh
        ./deploy.sh
    else
        echo -e "${RED}错误: 未找到deploy.sh脚本${NC}"
        exit 1
    fi
}

# 清理临时文件
cleanup() {
    echo -e "${BLUE}清理临时文件...${NC}"
    rm -rf "${TEMP_DIR}"
    echo -e "${GREEN}清理完成${NC}"
}

# 主安装流程
main_install() {
    show_title
    echo -e "${BLUE}开始一键安装iKuai Komari监控代理...${NC}"
    echo ""
    
    read -p "确认从GitHub下载并安装? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}安装已取消${NC}"
        exit 0
    fi
    
    echo ""
    
    # 执行安装步骤
    install_dependencies
    download_project
    run_deploy_script
    cleanup
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    GitHub一键安装完成!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}服务管理命令:${NC}"
    echo "查看状态: systemctl status ikuai_Komari_agent"
    echo "启动服务: systemctl start ikuai_Komari_agent"
    echo "停止服务: systemctl stop ikuai_Komari_agent"
    echo "查看日志: journalctl -u ikuai_Komari_agent -f"
    echo ""
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}iKuai Komari 监控代理一键安装脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -v, --version  显示版本信息"
    echo ""
    echo "示例:"
    echo "  sudo $0          # 一键安装"
    echo "  sudo $0 --help   # 显示帮助"
    echo ""
}

# 显示版本信息
show_version() {
    echo -e "${BLUE}iKuai Komari 监控代理 v1.0${NC}"
    echo "GitHub一键安装脚本"
    echo "支持系统: Debian/Ubuntu/CentOS/RHEL"
}

# 主程序
main() {
    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--version)
            show_version
            exit 0
            ;;
        "")
            check_root
            check_system
            main_install
            ;;
        *)
            echo -e "${RED}错误: 未知选项 $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 运行主程序
main "$@" 