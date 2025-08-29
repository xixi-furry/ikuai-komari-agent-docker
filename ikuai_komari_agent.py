#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iKuai监控代理 v1.0
"""

import logging
import logging.handlers
import json
import time
import threading
import socket
import platform
import psutil
import argparse
import signal
import sys
import ipaddress
from typing import Dict, Any, Optional
import websocket
import requests
from ikuai_client import IkuaiClient
from config import KOMARI_CONFIG, LOGGING_CONFIG

logger = logging.getLogger(__name__)

class IkuaiAgent:
    def __init__(self):
        """
        初始化iKuai监控代理
        使用config.py中的默认配置
        """
        # 使用配置文件中的默认值
        self.endpoint = KOMARI_CONFIG["endpoint"]
        self.token = KOMARI_CONFIG["token"]
        self.interval = KOMARI_CONFIG["websocket_interval"]
        self.info_report_interval = KOMARI_CONFIG["basic_info_interval"] * 60  # 转换为秒
        self.ignore_unsafe_cert = KOMARI_CONFIG["ignore_unsafe_cert"]
        
        # 运行状态
        self.running = False
        self.ws = None
        self.last_basic_info_report = 0
        self.last_status_report = 0
        
        # 设置日志
        self.setup_logging()
        
        # 创建ikuai客户端
        self.ikuai_client = IkuaiClient()
        
        logger.info("iKuai监控代理初始化完成")
    
    def is_private_ip(self, ip: str) -> bool:
        """判断IP是否为内网IP"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except:
            return False
    
    def get_public_ip_from_ikuai(self) -> str:
        """从iKuai路由器获取公网IP"""
        try:
            interface_info = self.ikuai_client.get_interface_info()
            if interface_info:
                iface_check = interface_info.get("iface_check", [])
                for iface in iface_check:
                    ip_addr = iface.get("ip_addr", "")
                    if ip_addr and not self.is_private_ip(ip_addr):
                        logger.debug(f"从WAN口获取到公网IP: {ip_addr}")
                        return ip_addr
                
                iface_stream = interface_info.get("iface_stream", [])
                for iface in iface_stream:
                    ip_addr = iface.get("ip_addr", "")
                    if ip_addr and not self.is_private_ip(ip_addr):
                        logger.debug(f"从接口流获取到公网IP: {ip_addr}")
                        return ip_addr
            
            return ""
        except Exception as e:
            logger.error(f"获取iKuai公网IP失败: {e}")
            return ""
    
    def setup_logging(self):
        """设置日志"""
        log_config = LOGGING_CONFIG
        
        # 创建日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 设置根日志级别
        logging.basicConfig(level=getattr(logging, log_config["level"]))
        
        # 创建文件处理器
        file_handler = logging.FileHandler(
            log_config["file"],
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # 清除默认处理器
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(getattr(logging, log_config["level"]))
        
        # 设置特定模块的日志级别
        logging.getLogger('websocket').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        
        # 创建全局logger
        global logger
        logger = logging.getLogger(__name__)
    
    def get_ikuai_data(self) -> Dict[str, Any]:
        """获取ikuai数据"""
        try:
            # 获取硬件信息
            hardware_info = self.ikuai_client.get_hardware_info()
            
            # 获取系统状态信息
            system_stats = self.ikuai_client.get_system_stats()
            
            # 获取网络统计信息
            network_stats = self.ikuai_client.get_network_stats()
            
            # 获取CPU和内存统计信息
            cpu_memory_stats = self.ikuai_client.get_cpu_memory_stats()
            
            return {
                "hardware": hardware_info or {},
                "system": system_stats or {},
                "network": network_stats or {},
                "cpu_memory": cpu_memory_stats or {}
            }
        except Exception as e:
            logger.error(f"获取ikuai数据异常: {e}")
            return {}
    

    
    def format_basic_info(self) -> Dict[str, Any]:
        """格式化基础信息上报数据"""
        ikuai_data = self.get_ikuai_data()
        
        ipv4 = self.get_public_ip_from_ikuai()
        
        if not ipv4:
            try:
                hostname = socket.gethostname()
                ipv4 = socket.gethostbyname(hostname)
            except:
                ipv4 = "127.0.0.1"
        
        hw_info = ikuai_data.get("hardware", {})
        sys_info = ikuai_data.get("system", {})
        verinfo = sys_info.get("verinfo", {})
        
        # 尝试从homepage API获取版本信息
        try:
            homepage_data = self.ikuai_client.get_homepage_stats()
            if homepage_data and "sysstat" in homepage_data:
                homepage_verinfo = homepage_data["sysstat"].get("verinfo", {})
                if homepage_verinfo:
                    verinfo = homepage_verinfo
                    logger.debug(f"从homepage获取到版本信息: {verinfo}")
        except Exception as e:
            logger.error(f"获取homepage版本信息失败: {e}")
        
        logger.debug(f"iKuai系统信息: {sys_info}")
        logger.debug(f"iKuai版本信息: {verinfo}")
        
        ikuai_version = verinfo.get("verstring", "")
        if ikuai_version:
            os_info = f"iKuai ({ikuai_version})"
        else:
            os_info = "iKuai"
        
        logger.debug(f"最终操作系统信息: {os_info}")
        
        mem_total_bytes = 0
        try:
            homepage_data = self.ikuai_client.get_homepage_stats()
            if homepage_data and "sysstat" in homepage_data:
                memory_data = homepage_data["sysstat"].get("memory", {})
                mem_total_kb = memory_data.get("total", 0)
                mem_total_bytes = mem_total_kb * 1024
                logger.debug(f"从iKuai API获取内存: {mem_total_kb}KB = {mem_total_bytes}字节")
            else:
                if hw_info.get("memory"):
                    mem_total_bytes = hw_info.get("memory") * 1024 * 1024
                else:
                    mem_total_bytes = 0
        except Exception as e:
            logger.error(f"获取内存数据失败: {e}")
            if hw_info.get("memory"):
                mem_total_bytes = hw_info.get("memory") * 1024 * 1024
            else:
                mem_total_bytes = local_info.get("memory", {}).get("mem_total", 0)
        
        disk_total_bytes = 0
        hdd_info = hw_info.get("hdd", "")
        if hdd_info and "GB" in hdd_info:
            try:
                import re
                match = re.search(r'\((\d+\.?\d*)GB\)', hdd_info)
                if match:
                    disk_gb = float(match.group(1))
                    disk_total_bytes = int(disk_gb * 1024 * 1024 * 1024)
            except:
                disk_total_bytes = 0
        else:
            disk_total_bytes = 0
        
        basic_info = {
            "arch": platform.machine(),
            "cpu_cores": hw_info.get("cpucores", 0),
            "cpu_name": hw_info.get("cpumodel", "Unknown"),
            "disk_total": disk_total_bytes,
            "gpu_name": "Unknown",
            "ipv4": ipv4,
            "ipv6": "",
            "mem_total": mem_total_bytes,
            "os": os_info,
            "kernel_version": platform.release(),
            "swap_total": 0,
            "version": "ikuai-agent-1.0.0",
            "virtualization": "None"
        }
        
        return basic_info
    
    def format_monitoring_data(self) -> Dict[str, Any]:
        """格式化实时监控数据"""
        ikuai_data = self.get_ikuai_data()
        
        cpu_usage = 0
        sys_stats = ikuai_data.get("system", {})
        if sys_stats.get("cpu"):
            try:
                cpu_values = [float(x.strip('%')) for x in sys_stats["cpu"] if x.strip('%').replace('.', '').isdigit()]
                cpu_usage = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            except:
                cpu_usage = psutil.cpu_percent(interval=1)
        else:
            cpu_usage = psutil.cpu_percent(interval=1)
        
        process_count = 0
        try:
            homepage_data = self.ikuai_client.get_homepage_stats()
            if homepage_data and "sysstat" in homepage_data:
                sysstat = homepage_data["sysstat"]
                if sysstat.get("cputemp"):
                    cpu_temp_values = sysstat["cputemp"]
                    if cpu_temp_values and len(cpu_temp_values) > 0:
                        process_count = int(float(cpu_temp_values[0]))
        except Exception as e:
            logger.error(f"获取CPU温度失败: {e}")
            process_count = 0
        
        try:
            homepage_data = self.ikuai_client.get_homepage_stats()
            if homepage_data and "sysstat" in homepage_data:
                memory_data = homepage_data["sysstat"].get("memory", {})
                mem_total_kb = memory_data.get("total", 0)
                mem_used_percent = memory_data.get("used", "0%").strip('%')
                
                try:
                    mem_used_percent = float(mem_used_percent)
                    mem_total_bytes = mem_total_kb * 1024
                    mem_used_bytes = int(mem_total_bytes * mem_used_percent / 100)
                    
                    logger.debug(f"内存数据: 总内存={mem_total_kb}KB, 使用率={mem_used_percent}%, 总字节={mem_total_bytes}, 已用字节={mem_used_bytes}")
                except Exception as e:
                    logger.error(f"内存数据计算错误: {e}")
                    mem_total_bytes = 0
                    mem_used_bytes = 0
            else:
                mem_total_bytes = 0
                mem_used_bytes = 0
        except Exception as e:
            logger.error(f"获取内存数据失败: {e}")
            mem_total_bytes = 3 * 1024 * 1024 * 1024
            mem_used_bytes = int(mem_total_bytes * 0.2)
        
        try:
            wan_net_stats = self.ikuai_client.get_wan_network_stats()
            if wan_net_stats:
                net_up = wan_net_stats.get("upload", 0)
                net_down = wan_net_stats.get("download", 0)
                net_total_up = wan_net_stats.get("total_up", net_up)
                net_total_down = wan_net_stats.get("total_down", net_down)
                
                net_up_rate = int(net_up / 3)
                net_down_rate = int(net_down / 3)
                
                logger.debug(f"WAN口网络数据: 上传={net_up}, 下载={net_down}, 总上传={net_total_up}, 总下载={net_total_down}")
            else:
                net_stats = ikuai_data.get("network", {})
                if net_stats:
                    net_up = net_stats.get("upload", 0)
                    net_down = net_stats.get("download", 0)
                    net_total_up = net_stats.get("total_up", net_up)
                    net_total_down = net_stats.get("total_down", net_down)
                    
                    net_up_rate = int(net_up / 3)
                    net_down_rate = int(net_down / 3)
                else:
                    net_up = 0
                    net_down = 0
                    net_total_up = 0
                    net_total_down = 0
                    net_up_rate = 0
                    net_down_rate = 0
        except Exception as e:
            logger.error(f"获取WAN口网络数据失败: {e}")
            net_stats = ikuai_data.get("network", {})
            if net_stats:
                net_up = net_stats.get("upload", 0)
                net_down = net_stats.get("download", 0)
                net_total_up = net_stats.get("total_up", net_up)
                net_total_down = net_stats.get("total_down", net_down)
                
                net_up_rate = int(net_up / 3)
                net_down_rate = int(net_down / 3)
            else:
                net_up = 0
                net_down = 0
                net_total_up = 0
                net_total_down = 0
                net_up_rate = 0
                net_down_rate = 0
        
        try:
            connection_stats = self.ikuai_client.get_connection_stats()
            if connection_stats:
                tcp_connections = connection_stats.get("tcp", connection_stats.get("total", 0))
                udp_connections = connection_stats.get("udp", 0)
            else:
                tcp_connections = 0
                udp_connections = 0
        except:
            tcp_connections = 0
            udp_connections = 0
        
        disk_info = {}
        
        try:
            ikuai_disk_stats = self.ikuai_client.get_disk_usage_stats()
            if ikuai_disk_stats:
                disk_info = {
                    "disk_total": ikuai_disk_stats.get("total", 0),
                    "disk_used": ikuai_disk_stats.get("used", 0),
                    "disk_free": ikuai_disk_stats.get("available", 0)
                }
            else:
                hw_info = ikuai_data.get("hardware", {})
                hdd_info = hw_info.get("hdd", "")
                ikuai_disk_total = 0
                
                if hdd_info and "GB" in hdd_info:
                    try:
                        import re
                        match = re.search(r'\((\d+\.?\d*)GB\)', hdd_info)
                        if match:
                            disk_gb = float(match.group(1))
                            ikuai_disk_total = int(disk_gb * 1024 * 1024 * 1024)
                    except:
                        ikuai_disk_total = 0
                else:
                    ikuai_disk_total = 0
                
                ikuai_disk_used = int(ikuai_disk_total * 0.2)
                
                disk_info = {
                    "disk_total": ikuai_disk_total,
                    "disk_used": ikuai_disk_used,
                    "disk_free": ikuai_disk_total - ikuai_disk_used
                }
        except Exception as e:
            logger.error(f"获取ikuai磁盘信息失败: {e}")
            pass
        
        load1, load5, load15 = 0, 0, 0
        try:
            load_stats = self.ikuai_client.get_load_from_homepage()
            if load_stats:
                load1 = load_stats.get("load1", 0)
                load5 = load_stats.get("load5", 0)
                load15 = load_stats.get("load15", 0)
            else:
                pass
        except Exception as e:
            logger.error(f"获取负载信息异常: {e}")
            pass
        
        ikuai_uptime = 0
        try:
            ikuai_uptime = self.ikuai_client.get_uptime() or 0
        except:
            ikuai_uptime = int(time.time() - psutil.boot_time())
        
        monitoring_data = {
            "cpu": {
                "usage": round(cpu_usage, 2)
            },
            "ram": {
                "total": mem_total_bytes,
                "used": mem_used_bytes
            },
            "swap": {
                "total": 0,
                "used": 0
            },
            "load": {
                "load1": load1,
                "load5": load5,
                "load15": load15
            },
            "disk": {
                "total": disk_info.get("disk_total", 0),
                "used": disk_info.get("disk_used", 0)
            },
            "network": {
                "up": net_up_rate,
                "down": net_down_rate,
                "totalUp": net_total_up,
                "totalDown": net_total_down
            },
            "connections": {
                "tcp": tcp_connections,
                "udp": udp_connections
            },
            "uptime": ikuai_uptime,
            "process": process_count,
            "message": f"ikuai监控 - CPU: {cpu_usage:.1f}%, 内存: {mem_used_bytes/1024/1024/1024:.1f}GB, 连接数: {tcp_connections}"
        }
        
        return monitoring_data
    
    def report_basic_info(self):
        """上报基础信息"""
        try:
            basic_info = self.format_basic_info()
            url = f"{self.endpoint}/api/clients/uploadBasicInfo?token={self.token}"
            
            response = requests.post(url, json=basic_info, timeout=30, verify=not self.ignore_unsafe_cert)
            response.raise_for_status()
            
            logger.info("基础信息上报成功")
            self.last_basic_info_report = time.time()
            
        except Exception as e:
            logger.error(f"基础信息上报失败: {e}")
    
    def on_websocket_message(self, ws, message):
        """处理WebSocket消息（简化版，只记录日志）"""
        try:
            data = json.loads(message)
            logger.info(f"收到WebSocket消息: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
        except Exception as e:
            logger.error(f"处理WebSocket消息异常: {e}")
    
    def on_websocket_error(self, ws, error):
        """WebSocket错误处理"""
        logger.error(f"WebSocket错误: {error}")
    
    def on_websocket_close(self, ws, close_status_code, close_msg):
        """WebSocket连接关闭处理"""
        logger.info("WebSocket连接已关闭")
        if self.running:
            self.schedule_reconnect()
    
    def on_websocket_open(self, ws):
        """WebSocket连接建立处理"""
        logger.info("WebSocket连接已建立")
    
    def schedule_reconnect(self):
        """安排重连"""
        logger.info("5秒后尝试重连...")
        threading.Timer(5, self.start_websocket_connection).start()
    
    def start_websocket_connection(self):
        """启动WebSocket连接"""
        try:
            ws_url = f"{self.endpoint.replace('https', 'wss').replace('http', 'ws')}/api/clients/report?token={self.token}"
            logger.info(f"尝试连接WebSocket: {ws_url}")
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_websocket_open,
                on_message=self.on_websocket_message,
                on_error=self.on_websocket_error,
                on_close=self.on_websocket_close
            )
            
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            if self.running:
                self.schedule_reconnect()
    
    def monitoring_loop(self):
        """监控循环"""
        self.running = True
        logger.info("开始监控循环...")
        
        while self.running:
            try:
                monitoring_data = self.format_monitoring_data()
                
                if hasattr(self, 'ws') and self.ws and self.ws.sock and self.ws.sock.connected:
                    self.ws.send(json.dumps(monitoring_data))
                
                current_time = time.time()
                if current_time - self.last_basic_info_report >= self.info_report_interval:
                    self.report_basic_info()
                    self.last_basic_info_report = current_time
                
                if current_time - self.last_status_report >= 1800:
                    logger.info("✓ 监控程序运行正常，数据持续上报中...")
                    self.last_status_report = current_time
                
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(self.interval)
        
        logger.info("监控循环已停止")
    
    def start(self):
        """启动监控代理"""
        try:
            logger.info("启动iKuai监控代理...")
            
            if not self.ikuai_client.login():
                logger.error("ikuai登录失败，程序退出")
                return False
            
            self.start_websocket_connection()
            
            # 启动时立即上报基础信息
            self.report_basic_info()
            
            self.monitoring_loop()
            
            logger.info("✓ iKuai监控代理启动成功！")
            logger.info("✓ WebSocket连接已建立")
            logger.info("✓ 开始实时监控iKuai路由器数据...")
            
            return True
            
        except Exception as e:
            logger.error(f"启动失败: {e}")
            return False
    
    def stop(self):
        """停止Agent"""
        logger.info("停止iKuai监控代理...")
        self.running = False
        if self.ws:
            self.ws.close()
        if self.ikuai_client:
            self.ikuai_client.logout()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='iKuai监控代理')
    parser.add_argument('--test', action='store_true', help='测试模式')
    
    args = parser.parse_args()
    
    try:
        agent = IkuaiAgent()
        
        if args.test:
            print("=== 测试模式 ===")
            print("基础信息:")
            basic_info = agent.format_basic_info()
            print(json.dumps(basic_info, indent=2, ensure_ascii=False))
            
            print("\n监控数据:")
            monitoring_data = agent.format_monitoring_data()
            print(json.dumps(monitoring_data, indent=2, ensure_ascii=False))
            
            logger.info("测试完成")
            return
        
        # 设置信号处理
        def signal_handler(signum, frame):
            logger.info("收到停止信号，正在关闭程序...")
            agent.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动监控代理
        if agent.start():
            logger.info("✓ 程序启动成功，正在运行中...")
            logger.info("✓ 按 Ctrl+C 停止程序")
            
            # 保持程序运行
            try:
                while agent.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("收到键盘中断信号")
            finally:
                agent.stop()
                logger.info("✓ 程序已正常停止")
        else:
            logger.error("程序启动失败")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 