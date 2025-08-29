#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ikuai客户端模块
基于提供的登录逻辑实现
"""

import hashlib
import base64
import requests
import json
import logging
from typing import Dict, Any, Optional
from config import IKUAI_CONFIG

logger = logging.getLogger(__name__)

class IkuaiClient:
    def __init__(self, base_url: str = None, username: str = None, password: str = None, timeout: int = None):
        """
        初始化ikuai客户端
        
        Args:
            base_url: ikuai路由器基础URL
            username: 登录用户名
            password: 登录密码
            timeout: 请求超时时间
        """
        # 使用配置文件中的默认值，如果参数提供则覆盖
        self.base_url = base_url or IKUAI_CONFIG["base_url"]
        self.username = username or IKUAI_CONFIG["username"]
        self.password = password or IKUAI_CONFIG["password"]
        self.timeout = timeout or IKUAI_CONFIG["timeout"]
        
        # 确保URL格式正确
        self.base_url = self.base_url.rstrip('/')
        self.action_url = f"{self.base_url}/Action/call"
        self.login_url = f"{self.base_url}/Action/login"
        
        # 会话管理
        self.session = requests.Session()
        self.sess_key = None
        self.is_logged_in = False
        
        logger.info(f"ikuai客户端初始化完成: {self.base_url}")
    
    def process_password(self, password: str) -> tuple:
        """
        处理密码（基于提供的逻辑）
        
        Args:
            password: 原始密码
            
        Returns:
            tuple: (md5_hash, base64_encoded)
        """
        md5_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        salted_password = "salt_11" + password
        base64_encoded = base64.b64encode(salted_password.encode('utf-8')).decode('utf-8')
        
        return md5_hash, base64_encoded
    
    def login(self) -> bool:
        """
        登录ikuai路由器
        
        Returns:
            bool: 登录是否成功
        """
        try:
            logger.info("尝试登录ikuai路由器...")
            
            # 处理密码
            md5_hash, base64_encoded = self.process_password(self.password)
            
            # 构造登录数据
            payload = {
                "username": self.username,
                "passwd": md5_hash,
                "pass": base64_encoded,
                "remember_password": "true"
            }
            
            logger.debug(f"登录URL: {self.login_url}")
            logger.debug(f"登录数据: {json.dumps(payload, ensure_ascii=False)}")
            
            # 发送登录请求
            response = self.session.post(self.login_url, json=payload, timeout=self.timeout)
            
            logger.debug(f"登录响应状态: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.debug(f"登录响应: {json.dumps(result, ensure_ascii=False)}")
                    
                    if result.get("Result") == 10000:
                        # 获取sess_key
                        if 'Set-Cookie' in response.headers:
                            set_cookie = response.headers['Set-Cookie']
                            if 'sess_key=' in set_cookie:
                                self.sess_key = set_cookie.split('sess_key=')[1].split(';')[0]
                                logger.info("✓ 登录成功，获取到sess_key")
                                self.is_logged_in = True
                                return True
                        
                        logger.info("✓ 登录成功")
                        self.is_logged_in = True
                        return True
                    else:
                        logger.error(f"✗ 登录失败: {result.get('ErrMsg', '未知错误')}")
                        return False
                        
                except json.JSONDecodeError:
                    # 可能是重定向到主页，检查是否包含登录成功标识
                    if "login" not in response.url.lower():
                        logger.info("✓ 登录可能成功（重定向到主页）")
                        self.is_logged_in = True
                        return True
                    else:
                        logger.error("✗ 登录失败（仍在登录页面）")
                        return False
            else:
                logger.error(f"✗ 登录请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 登录异常: {e}")
            return False
    
    def call_api(self, func_name: str, action: str = "show", params: Dict = None) -> Optional[Dict]:
        """
        调用ikuai API
        
        Args:
            func_name: 函数名称
            action: 动作
            params: 参数
            
        Returns:
            Dict: API响应数据，失败返回None
        """
        try:
            # 确保已登录
            if not self.is_logged_in:
                if not self.login():
                    logger.error("未登录，无法调用API")
                    return None
            
            # 构造请求数据
            payload = {
                "func_name": func_name,
                "action": action
            }
            
            if params:
                payload["param"] = params
            
            # 发送请求
            response = self.session.post(self.action_url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("Result") == 30000:
                    return data
                elif data.get("Result") == 10014:
                    logger.warning("会话过期，尝试重新登录")
                    self.is_logged_in = False
                    # 清除旧的会话
                    self.session.cookies.clear()
                    if self.login():
                        # 重新尝试API调用
                        return self.call_api(func_name, action, params)
                    else:
                        logger.error("重新登录失败")
                        return None
                else:
                    logger.error(f"API返回错误: {data.get('ErrMsg', '未知错误')}")
                    return None
            else:
                logger.error(f"API请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return None
    
    def get_hardware_info(self) -> Optional[Dict]:
        """获取硬件信息"""
        result = self.call_api("hardwareinfo", "show")
        return result["Data"].get("hardwareinfo", {}) if result and "Data" in result else None

    def get_system_stats(self, types: str = "verinfo,cpu,memory,stream,cputemp") -> Optional[Dict]:
        """获取系统状态信息"""
        result = self.call_api("sysstat", "show", {"TYPE": types})
        return result["Data"].get("sysstat", {}) if result and "Data" in result else None

    def get_network_stats(self) -> Optional[Dict]:
        """获取网络统计信息"""
        try:
            # 从首页统计信息获取网络数据
            result = self.call_api("homepage", "show", {"TYPE": "sysstat,ac_status"})
            if result and "Data" in result:
                sysstat = result["Data"].get("sysstat", {})
                stream = sysstat.get("stream", {})
                
                # 返回网络统计信息
                return {
                    "upload": stream.get("upload", 0),
                    "download": stream.get("download", 0),
                    "total_up": stream.get("total_up", 0),
                    "total_down": stream.get("total_down", 0),
                    "connect_num": stream.get("connect_num", 0)
                }
            
            # 如果上面的方法失败，尝试原来的API
            result = self.call_api("sysstat", "show", {"TYPE": "stream"})
            return result["Data"].get("sysstat", {}).get("stream", {}) if result and "Data" in result else None
        except Exception as e:
            logger.error(f"获取网络统计异常: {e}")
            return None
    
    def get_connection_stats(self) -> Optional[Dict]:
        """获取连接数统计信息"""
        try:
            # 从首页统计信息获取连接数
            result = self.call_api("homepage", "show", {"TYPE": "sysstat,ac_status"})
            if result and "Data" in result:
                sysstat = result["Data"].get("sysstat", {})
                stream = sysstat.get("stream", {})
                
                # 从stream字段获取连接数
                connect_num = stream.get("connect_num", 0)
                
                return {
                    "tcp": connect_num,  # 总连接数作为TCP连接数
                    "udp": 0,  # UDP连接数默认为0
                    "total": connect_num
                }
            
            return None
        except Exception as e:
            logger.error(f"获取连接数统计异常: {e}")
            return None

    def get_cpu_memory_stats(self) -> Optional[Dict]:
        """获取CPU和内存统计信息"""
        result = self.call_api("sysstat", "show", {"TYPE": "cpu,memory"})
        return result["Data"].get("sysstat", {}) if result and "Data" in result else None

    def get_homepage_stats(self) -> Optional[Dict]:
        """获取首页统计信息"""
        result = self.call_api("homepage", "show", {"TYPE": "sysstat,ac_status"})
        if result and "Data" in result:
            return result["Data"]
        return None

    def get_uptime(self) -> Optional[int]:
        """获取iKuai运行时间"""
        try:
            homepage_data = self.get_homepage_stats()
            if homepage_data and "sysstat" in homepage_data:
                uptime = homepage_data["sysstat"].get("uptime", 0)
                return uptime
            return None
        except Exception as e:
            logger.error(f"获取运行时间异常: {e}")
            return None
    
    def get_load_stats(self) -> Optional[Dict]:
        """
        获取系统负载信息
        
        Returns:
            Dict: 负载信息，失败返回None
        """
        logger.info("获取系统负载信息...")
        result = self.call_api("sysstat", "show", {"TYPE": "load"})
        
        if result and "Data" in result:
            return result["Data"].get("load", {})
        return None
    
    def get_disk_stats(self) -> Optional[Dict]:
        """
        获取磁盘使用信息
        
        Returns:
            Dict: 磁盘信息，失败返回None
        """
        logger.info("获取磁盘使用信息...")
        result = self.call_api("sysstat", "show", {"TYPE": "disk"})
        
        if result and "Data" in result:
            return result["Data"].get("disk", {})
        return None
    
    def get_disk_mgmt_info(self) -> Optional[Dict]:
        """获取磁盘管理信息"""
        result = self.call_api("disk_mgmt", "show", {"TYPE": "data"})
        if result and "Data" in result:
            return result["Data"].get("data", [])
        return None

    def get_disk_usage_stats(self) -> Optional[Dict]:
        """获取磁盘使用统计"""
        try:
            disk_data = self.get_disk_mgmt_info()
            if not disk_data:
                return None
            
            total_size = 0
            total_used = 0
            total_available = 0
            
            for disk in disk_data:
                disk_size = disk.get("size", 0)
                total_size += disk_size
                
                partitions = disk.get("partition", [])
                for partition in partitions:
                    mounted = partition.get("mounted", {})
                    if mounted:
                        total_bytes_partition = int(mounted.get("mt_total", 0))
                        used_bytes = int(mounted.get("mt_used", 0))
                        avail_bytes = int(mounted.get("mt_avail", 0))
                        total_used += used_bytes
                        total_available += avail_bytes
            
            return {
                "total": total_size,
                "used": total_used,
                "available": total_available
            }
        except Exception as e:
            logger.error(f"计算磁盘使用情况异常: {e}")
            return None
    
    def get_load_from_homepage(self) -> Optional[Dict]:
        """
        尝试从首页统计信息中获取负载数据
        
        Returns:
            Dict: 负载信息，失败返回None
        """
        try:
            homepage_data = self.get_homepage_stats()
            if homepage_data and "sysstat" in homepage_data:
                sysstat = homepage_data["sysstat"]
                
                # 检查是否有负载相关字段
                logger.debug(f"首页统计信息字段: {list(sysstat.keys())}")
                
                # 如果有load字段，直接使用
                if "load" in sysstat:
                    load_data = sysstat["load"]
                    logger.info(f"找到负载数据: {load_data}")
                    return load_data
                
                # 如果没有load字段，尝试从其他字段计算
                # 例如从CPU使用率估算负载
                if "cpu" in sysstat:
                    cpu_data = sysstat["cpu"]
                    logger.debug(f"CPU数据: {cpu_data}")
                    
                    # 简单的负载估算：基于CPU使用率
                    try:
                        cpu_values = [float(x.strip('%')) for x in cpu_data if x.strip('%').replace('.', '').isdigit()]
                        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                        
                        # 将CPU使用率转换为负载值（简化估算）
                        load_value = avg_cpu / 100.0  # 转换为0-1范围
                        
                        return {
                            "load1": round(load_value, 2),
                            "load5": round(load_value * 0.8, 2),  # 5分钟负载略低
                            "load15": round(load_value * 0.6, 2)  # 15分钟负载更低
                        }
                    except:
                        pass
                
                return None
        except Exception as e:
            logger.error(f"从首页获取负载信息异常: {e}")
            return None
    
    def logout(self):
        """登出"""
        logger.info("登出ikuai路由器")
        self.session.close()
        self.is_logged_in = False
        self.sess_key = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.logout()
    
    def get_interface_info(self) -> Optional[Dict]:
        try:
            result = self.call_api("monitor_iface", "show", {"TYPE": "iface_check,iface_stream"})
            if result and "Data" in result:
                return result["Data"]
            return None
        except Exception as e:
            logger.error(f"获取接口信息异常: {e}")
            return None
    
    def get_wan_network_stats(self) -> Optional[Dict]:
        try:
            result = self.call_api("monitor_iface", "show", {"TYPE": "iface_check,iface_stream"})
            if result and "Data" in result:
                data = result["Data"]
                iface_stream = data.get("iface_stream", [])
                
                for iface in iface_stream:
                    interface_name = iface.get("interface", "")
                    if interface_name.startswith("wan"):
                        return {
                            "upload": iface.get("upload", 0),
                            "download": iface.get("download", 0),
                            "total_up": iface.get("total_up", 0),
                            "total_down": iface.get("total_down", 0),
                            "connect_num": iface.get("connect_num", 0)
                        }
                
                for iface in iface_stream:
                    ip_addr = iface.get("ip_addr", "")
                    if ip_addr and not self._is_private_ip(ip_addr):
                        return {
                            "upload": iface.get("upload", 0),
                            "download": iface.get("download", 0),
                            "total_up": iface.get("total_up", 0),
                            "total_down": iface.get("total_down", 0),
                            "connect_num": iface.get("connect_num", 0)
                        }
            
            return None
        except Exception as e:
            logger.error(f"获取WAN口网络统计异常: {e}")
            return None
    
    def _is_private_ip(self, ip: str) -> bool:
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except:
            return False 