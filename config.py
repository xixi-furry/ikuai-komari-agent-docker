#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iKuai连接配置信息
支持环境变量配置
"""

import os

def str_to_bool(value):
    """将字符串转换为布尔值"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return False

# iKuai路由器配置
IKUAI_CONFIG = {
    "base_url": os.environ.get("IKUAI_BASE_URL", "http://192.168.1.1"),
    "username": os.environ.get("IKUAI_USERNAME", "admin"),
    "password": os.environ.get("IKUAI_PASSWORD", "admin"),
    "timeout": int(os.environ.get("IKUAI_TIMEOUT", "10"))
}

# Komari服务器配置
KOMARI_CONFIG = {
    "endpoint": os.environ.get("KOMARI_ENDPOINT", "https://komari.server.com"),
    "token": os.environ.get("KOMARI_TOKEN", "your_token_here"),
    "websocket_interval": float(os.environ.get("KOMARI_WEBSOCKET_INTERVAL", "1.0")), # 监控数据上报间隔（默认 1.0秒）
    "basic_info_interval": int(os.environ.get("KOMARI_BASIC_INFO_INTERVAL", "5")),  # 基础信息上报间隔（默认 5分钟）
    "ignore_unsafe_cert": str_to_bool(os.environ.get("KOMARI_IGNORE_UNSAFE_CERT", "False")) # 忽略不安全的 SSL 证书
}

# 日志配置
LOGGING_CONFIG = {
    "level": os.environ.get("LOG_LEVEL", "WARNING"),  # 日志级别
    "file": os.environ.get("LOG_FILE", "ikuai_agent.log"),
    "max_bytes": int(os.environ.get("LOG_MAX_BYTES", "10485760")),  # 10MB
    "backup_count": int(os.environ.get("LOG_BACKUP_COUNT", "3"))  # 备份文件数量
} 
