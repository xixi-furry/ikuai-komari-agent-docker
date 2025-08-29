#!/bin/bash

# iKuai Komari 监控代理 v1.0 一键安装脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# GitHub仓库信息
GITHUB_REPO="ZeroTwoDa/ikuai-komari-agent"
GITHUB_BRANCH="main"
DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/archive/refs/heads/${GITHUB_BRANCH}.zip"
TEMP_DIR="/tmp/ikuai_komari_agent_install"
INSTALL_PATH="/opt/ikuai_Komari_agent"
SERVICE_NAME="ikuai_Komari_agent"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

show_title() {
    clear
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    iKuai Komari 监控代理 v1.0${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}错误: 此脚本需要root权限运行${NC}"
        echo "请使用: sudo $0"
        exit 1
    fi
}

check_system() {
    if [[ ! -f /etc/os-release ]]; then
        echo -e "${RED}错误: 无法检测系统类型${NC}"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "debian" && "$ID" != "ubuntu" && "$ID" != "centos" && "$ID" != "rhel" ]]; then
        echo -e "${YELLOW}警告: 此脚本主要支持Debian/Ubuntu/CentOS系统${NC}"
        echo -e "${YELLOW}当前系统: $ID${NC}"
        echo -e "${YELLOW}如果遇到问题，请手动安装依赖包${NC}"
        echo ""
    fi
}

install_dependencies() {
    echo -e "${BLUE}检查系统依赖...${NC}"
    
    # 检测包管理器
    local pkg_manager=""
    if command -v apt-get &> /dev/null; then
        pkg_manager="apt-get"
    elif command -v yum &> /dev/null; then
        pkg_manager="yum"
    elif command -v dnf &> /dev/null; then
        pkg_manager="dnf"
    else
        echo -e "${RED}错误: 不支持的包管理器${NC}"
        exit 1
    fi
    
    # 需要检查的包列表
    local packages=("unzip" "python3" "python3-pip" "python3-venv")
    local missing_packages=()
    
    echo -e "${BLUE}检查已安装的包...${NC}"
    
    for package in "${packages[@]}"; do
        if command -v "$package" &> /dev/null; then
            echo -e "${GREEN}✓ $package 已安装${NC}"
        else
            echo -e "${YELLOW}✗ $package 未安装${NC}"
            missing_packages+=("$package")
        fi
    done
    
    # 如果有缺失的包，则安装
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        echo -e "${BLUE}安装缺失的包...${NC}"
        
        if [[ "$pkg_manager" == "apt-get" ]]; then
            apt-get update
            apt-get install -y "${missing_packages[@]}"
        elif [[ "$pkg_manager" == "yum" ]]; then
            yum install -y "${missing_packages[@]}"
        elif [[ "$pkg_manager" == "dnf" ]]; then
            dnf install -y "${missing_packages[@]}"
        fi
        
        echo -e "${GREEN}缺失的包安装完成${NC}"
    else
        echo -e "${GREEN}所有依赖包已安装${NC}"
    fi
    
    echo -e "${GREEN}系统依赖检查完成${NC}"
}

download_project() {
    echo -e "${BLUE}从GitHub下载项目文件...${NC}"
    
    mkdir -p "${TEMP_DIR}"
    cd "${TEMP_DIR}"
    
    echo -e "${BLUE}下载地址: ${GITHUB_REPO}${NC}"
    if curl -L -o project.zip "${DOWNLOAD_URL}"; then
        echo -e "${GREEN}下载完成${NC}"
    else
        echo -e "${RED}下载失败，请检查网络连接或GitHub仓库地址${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}解压文件...${NC}"
    unzip -q project.zip
    rm project.zip
    
    PROJECT_DIR=$(find . -name "ikuai-komari-agent-*" -type d | head -1)
    if [[ -z "$PROJECT_DIR" ]]; then
        echo -e "${RED}错误: 无法找到项目目录${NC}"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    echo -e "${GREEN}项目文件准备完成${NC}"
}

create_venv() {
    echo -e "${BLUE}创建Python虚拟环境...${NC}"
    
    if [[ -d "${INSTALL_PATH}" ]]; then
        echo -e "${YELLOW}安装目录已存在，正在备份...${NC}"
        mv "${INSTALL_PATH}" "${INSTALL_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    mkdir -p "${INSTALL_PATH}"
    python3 -m venv "${INSTALL_PATH}/venv"
    
    echo -e "${GREEN}虚拟环境创建完成${NC}"
}

copy_files() {
    echo -e "${BLUE}复制程序文件...${NC}"
    
    cp ikuai_komari_agent.py "${INSTALL_PATH}/"
    cp ikuai_client.py "${INSTALL_PATH}/"
    cp config.py "${INSTALL_PATH}/"
    cp README.md "${INSTALL_PATH}/"
    
    chmod +x "${INSTALL_PATH}/ikuai_komari_agent.py"
    chown -R root:root "${INSTALL_PATH}"
    
    echo -e "${GREEN}文件复制完成${NC}"
}

install_python_deps() {
    echo -e "${BLUE}安装Python依赖...${NC}"
    
    source "${INSTALL_PATH}/venv/bin/activate"
    pip install --upgrade pip
    pip install requests websocket-client psutil
    
    echo -e "${GREEN}Python依赖安装完成${NC}"
}

create_config() {
    local ikuai_url=$1
    local ikuai_username=$2
    local ikuai_password=$3
    local komari_endpoint=$4
    local komari_token=$5
    
    echo -e "${BLUE}创建配置文件...${NC}"
    
    cat > "${INSTALL_PATH}/config.py" << EOF
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iKuai连接配置信息
"""

# iKuai路由器配置
IKUAI_CONFIG = {
    "base_url": "${ikuai_url}",
    "username": "${ikuai_username}",
    "password": "${ikuai_password}",
    "timeout": 10
}

# Komari服务器配置
KOMARI_CONFIG = {
    "endpoint": "${komari_endpoint}",
    "token": "${komari_token}",
    "websocket_interval": 1.0,
    "basic_info_interval": 5,
    "ignore_unsafe_cert": False
}

# 日志配置
LOGGING_CONFIG = {
    "level": "WARNING",
    "file": "${INSTALL_PATH}/ikuai_agent.log",
    "max_bytes": 10485760,
    "backup_count": 3
}
EOF
    
    echo -e "${GREEN}配置文件创建完成${NC}"
}

create_service() {
    echo -e "${BLUE}创建systemd服务...${NC}"
    
    cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=iKuai Komari Monitoring Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_PATH}
ExecStart=${INSTALL_PATH}/venv/bin/python ${INSTALL_PATH}/ikuai_komari_agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    
    echo -e "${GREEN}systemd服务创建完成${NC}"
}

start_service() {
    echo -e "${BLUE}启动服务...${NC}"
    
    systemctl start "${SERVICE_NAME}"
    
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo -e "${GREEN}服务启动成功${NC}"
        echo -e "${BLUE}服务状态:${NC}"
        systemctl status "${SERVICE_NAME}" --no-pager -l
    else
        echo -e "${RED}服务启动失败${NC}"
        echo -e "${BLUE}查看日志:${NC}"
        journalctl -u "${SERVICE_NAME}" --no-pager -l
        exit 1
    fi
}

get_config_info() {
    echo -e "${YELLOW}请输入配置信息:${NC}"
    echo ""
    
    read -p "iKuai地址 (如 http://192.168.1.1): " ikuai_url
    ikuai_url=${ikuai_url:-"http://192.168.1.1"}
    
    read -p "iKuai用户名 (默认: admin): " ikuai_username
    ikuai_username=${ikuai_username:-"admin"}
    
    read -s -p "iKuai密码: " ikuai_password
    echo
    
    read -p "Komari服务器地址 (如 https://komari.server.com): " komari_endpoint
    komari_endpoint=${komari_endpoint:-"https://komari.server.com"}
    
    read -p "Komari认证令牌: " komari_token
    
    echo ""
    echo -e "${YELLOW}配置信息确认:${NC}"
    echo "iKuai地址: ${ikuai_url}"
    echo "iKuai用户名: ${ikuai_username}"
    echo "Komari服务器: ${komari_endpoint}"
    echo "安装路径: ${INSTALL_PATH}"
    echo ""
    
    create_venv
    copy_files
    install_python_deps
    create_config "$ikuai_url" "$ikuai_username" "$ikuai_password" "$komari_endpoint" "$komari_token"
    create_service
    start_service
}

cleanup() {
    echo -e "${BLUE}清理临时文件...${NC}"
    rm -rf "${TEMP_DIR}"
    echo -e "${GREEN}清理完成${NC}"
}

uninstall_agent() {
    echo -e "${BLUE}开始卸载iKuai Komari监控代理...${NC}"
    echo ""
    
    # 停止服务
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo -e "${BLUE}停止服务...${NC}"
        systemctl stop "${SERVICE_NAME}"
        echo -e "${GREEN}服务已停止${NC}"
    fi
    
    # 禁用服务
    if systemctl is-enabled --quiet "${SERVICE_NAME}"; then
        echo -e "${BLUE}禁用服务...${NC}"
        systemctl disable "${SERVICE_NAME}"
        echo -e "${GREEN}服务已禁用${NC}"
    fi
    
    # 删除服务文件
    if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
        echo -e "${BLUE}删除服务文件...${NC}"
        rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        echo -e "${GREEN}服务文件已删除${NC}"
    fi
    
    # 重新加载systemd
    echo -e "${BLUE}重新加载systemd...${NC}"
    systemctl daemon-reload
    echo -e "${GREEN}systemd已重新加载${NC}"
    
    # 删除安装目录
    if [[ -d "${INSTALL_PATH}" ]]; then
        echo -e "${BLUE}删除安装目录...${NC}"
        rm -rf "${INSTALL_PATH}"
        echo -e "${GREEN}安装目录已删除${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    iKuai Komari 监控代理卸载完成!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

show_menu() {
    show_title
    echo -e "${BLUE}默认安装到: ${INSTALL_PATH}${NC}"
    echo ""
    echo -e "${YELLOW}请选择操作:${NC}"
    echo "1. 安装iKuai Komari 监控代理"
    echo "2. 卸载iKuai Komari 监控代理"
    echo "3. 退出"
    echo ""
}

main_install() {
    show_title
    echo -e "${BLUE}开始安装iKuai Komari监控代理...${NC}"
    echo ""
    
    install_dependencies
    download_project
    get_config_info
    cleanup
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    iKuai Komari 监控代理安装完成!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}安装路径: ${INSTALL_PATH}${NC}"
    echo -e "${BLUE}服务名称: ${SERVICE_NAME}${NC}"
    echo -e "${BLUE}日志文件: ${INSTALL_PATH}/ikuai_agent.log${NC}"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "启动服务: systemctl start ${SERVICE_NAME}"
    echo "停止服务: systemctl stop ${SERVICE_NAME}"
    echo "查看状态: systemctl status ${SERVICE_NAME}"
    echo "查看日志: journalctl -u ${SERVICE_NAME} -f"
    echo ""
}

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

show_version() {
    echo -e "${BLUE}iKuai Komari 监控代理 v1.0${NC}"
}

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
            while true; do
                show_menu
                read -r -p "请输入选择 (1-3): " choice
                choice=$(echo "$choice" | tr -d '[:space:]')  # 移除空白字符
                case $choice in
                    1)
                        main_install
                        break
                        ;;
                    2)
                        uninstall_agent
                        break
                        ;;
                    3)
                        echo -e "${BLUE}退出安装程序${NC}"
                        exit 0
                        ;;
                    *)
                        echo -e "${RED}无效选择: '$choice'，请输入 1、2 或 3${NC}"
                        echo ""
                        ;;
                esac
            done
            ;;
        *)
            echo -e "${RED}错误: 未知选项 $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@" 
