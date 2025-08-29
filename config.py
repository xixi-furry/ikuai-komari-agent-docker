#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iKuai连接配置信息
"""

# iKuai路由器配置
IKUAI_CONFIG = {
    "base_url": "http://192.168.1.1",
    "username": "komari_user",
    "password": "password",
    "timeout": 10
}

# Komari服务器配置
KOMARI_CONFIG = {
    "endpoint": "https://komari.server.com",
    "token": "komari_token",
    "websocket_interval": 1.0, # 监控数据上报间隔（默认 1.0秒）
    "basic_info_interval": 5,  # 基础信息上报间隔（默认 5分钟）
    "ignore_unsafe_cert": False # 忽略不安全的 SSL 证书
}

# 日志配置
LOGGING_CONFIG = {
    "level": "WARNING",  # 日志级别
    "file": "ikuai_agent.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 3  # 备份文件数量

} 
