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
        
        # 设置日志
        self.setup_logging()
        
        # 创建ikuai客户端
        self.ikuai_client = IkuaiClient()
        
        logger.info("iKuai监控代理初始化完成")
    
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
    
    def get_local_system_info(self) -> Dict[str, Any]:
        """获取本地系统信息作为备用"""
        try:
            # CPU信息
            cpu_info = {
                "cpu_name": platform.processor(),
                "cpu_cores": psutil.cpu_count(logical=False),
                "cpu_threads": psutil.cpu_count(logical=True)
            }
            
            # 内存信息
            memory = psutil.virtual_memory()
            memory_info = {
                "mem_total": memory.total,
                "mem_used": memory.used,
                "mem_available": memory.available
            }
            
            # 磁盘信息
            try:
                disk = psutil.disk_usage('/')
                disk_info = {
                    "disk_total": disk.total,
                    "disk_used": disk.used,
                    "disk_free": disk.free
                }
            except:
                disk_info = {"disk_total": 0, "disk_used": 0, "disk_free": 0}
            
            # 网络信息
            network = psutil.net_io_counters()
            network_info = {
                "network_up": network.bytes_sent,
                "network_down": network.bytes_recv
            }
            
            return {
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "network": network_info
            }
        except Exception as e:
            logger.error(f"获取本地系统信息异常: {e}")
            return {}
    
    def format_basic_info(self) -> Dict[str, Any]:
        """格式化基础信息上报数据"""
        # 优先使用ikuai数据，备用本地数据
        ikuai_data = self.get_ikuai_data()
        local_info = self.get_local_system_info()
        
        # 获取IP地址
        try:
            hostname = socket.gethostname()
            ipv4 = socket.gethostbyname(hostname)
        except:
            ipv4 = "127.0.0.1"
        
        # 从ikuai数据中提取信息
        hw_info = ikuai_data.get("hardware", {})
        sys_info = ikuai_data.get("system", {})
        verinfo = sys_info.get("verinfo", {})
        
        # 获取ikuai版本信息
        ikuai_version = verinfo.get("verstring", "")
        if ikuai_version:
            os_info = f"iKuai ({ikuai_version})"
        else:
            os_info = "iKuai"
        
        # 修复内存数值：ikuai返回的是MB，需要转换为字节
        mem_total_bytes = 0
        if hw_info.get("memory"):
            mem_total_bytes = hw_info.get("memory") * 1024 * 1024  # MB转字节
        else:
            mem_total_bytes = local_info.get("memory", {}).get("mem_total", 0)
        
        # 获取ikuai硬盘容量
        disk_total_bytes = 0
        hdd_info = hw_info.get("hdd", "")
        if hdd_info and "GB" in hdd_info:
            try:
                # 从 "ATA SanDisk SDSA6MM- 006 (14.91GB)" 提取 "14.91"
                import re
                match = re.search(r'\((\d+\.?\d*)GB\)', hdd_info)
                if match:
                    disk_gb = float(match.group(1))
                    disk_total_bytes = int(disk_gb * 1024 * 1024 * 1024)  # GB转字节
                    logger.info(f"ikuai硬盘容量: {disk_gb}GB ({disk_total_bytes} bytes)")
            except:
                disk_total_bytes = local_info.get("disk", {}).get("disk_total", 0)
        else:
            disk_total_bytes = local_info.get("disk", {}).get("disk_total", 0)
        
        basic_info = {
            "arch": platform.machine(),
            "cpu_cores": hw_info.get("cpucores", local_info.get("cpu", {}).get("cpu_cores", 0)),
            "cpu_name": hw_info.get("cpumodel", local_info.get("cpu", {}).get("cpu_name", "Unknown")),
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
        local_info = self.get_local_system_info()
        
        # CPU使用率
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
        
        # 内存信息 - 修复数值问题
        hw_info = ikuai_data.get("hardware", {})
        memory = sys_stats.get("memory", {})
        
        if hw_info.get("memory") and memory:
            # 使用硬件信息中的内存大小作为基准（MB）
            mem_total_mb = hw_info.get("memory", 0)  # 3514 MB
            mem_used_percent = memory.get("used", "0%").strip('%')
            try:
                mem_used_percent = float(mem_used_percent)
                mem_total_bytes = mem_total_mb * 1024 * 1024  # MB转字节
                mem_used_bytes = int(mem_total_bytes * mem_used_percent / 100)
            except:
                mem_total_bytes = 0
                mem_used_bytes = 0
        else:
            mem_info = local_info.get("memory", {})
            mem_total_bytes = mem_info.get("mem_total", 0)
            mem_used_bytes = mem_info.get("mem_used", 0)
        
        # 网络信息
        net_stats = ikuai_data.get("network", {})
        if net_stats:
            net_up = net_stats.get("upload", 0)
            net_down = net_stats.get("download", 0)
            net_total_up = net_stats.get("total_up", 0)
            net_total_down = net_stats.get("total_down", 0)
            connections = net_stats.get("connect_num", 0)
        else:
            net_info = local_info.get("network", {})
            net_up = net_info.get("network_up", 0)
            net_down = net_info.get("network_down", 0)
            net_total_up = net_up
            net_total_down = net_down
            connections = 0
        
        # 磁盘信息 - 使用ikuai磁盘管理API获取真实使用情况
        disk_info = local_info.get("disk", {})
        
        # 获取ikuai磁盘使用信息
        try:
            ikuai_disk_stats = self.ikuai_client.get_disk_usage_stats()
            if ikuai_disk_stats:
                # 如果获取到ikuai磁盘信息，使用ikuai的真实数据
                disk_info = {
                    "disk_total": ikuai_disk_stats.get("total", 0),
                    "disk_used": ikuai_disk_stats.get("used", 0),
                    "disk_free": ikuai_disk_stats.get("available", 0)
                }
            else:
                # 如果获取失败，使用硬件信息中的硬盘容量作为备用
                hw_info = ikuai_data.get("hardware", {})
                hdd_info = hw_info.get("hdd", "")
                ikuai_disk_total = 0
                
                if hdd_info and "GB" in hdd_info:
                    try:
                        import re
                        match = re.search(r'\((\d+\.?\d*)GB\)', hdd_info)
                        if match:
                            disk_gb = float(match.group(1))
                            ikuai_disk_total = int(disk_gb * 1024 * 1024 * 1024)  # GB转字节
                            logger.info(f"ikuai硬盘容量: {disk_gb}GB ({ikuai_disk_total} bytes)")
                    except:
                        ikuai_disk_total = disk_info.get("disk_total", 0)
                else:
                    ikuai_disk_total = disk_info.get("disk_total", 0)
                
                # 使用估算的磁盘使用量（假设使用20%）
                ikuai_disk_used = int(ikuai_disk_total * 0.2)  # 估算20%使用率
                
                disk_info = {
                    "disk_total": ikuai_disk_total,
                    "disk_used": ikuai_disk_used,
                    "disk_free": ikuai_disk_total - ikuai_disk_used
                }
        except Exception as e:
            logger.error(f"获取ikuai磁盘信息失败: {e}")
            # 使用本地磁盘信息作为备用
            pass
        
        # 获取负载信息 - 尝试从首页统计信息获取或估算
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
        
        # 获取ikuai运行时间
        ikuai_uptime = 0
        try:
            ikuai_uptime = self.ikuai_client.get_uptime() or 0
        except:
            # 如果获取失败，使用本地运行时间作为备用
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
                "up": net_up,
                "down": net_down,
                "totalUp": net_total_up,
                "totalDown": net_total_down
            },
            "connections": {
                "tcp": connections,
                "udp": 0
            },
            "uptime": ikuai_uptime,
            "process": len(psutil.pids()),
            "message": f"ikuai监控 - CPU: {cpu_usage:.1f}%, 内存: {mem_used_bytes/1024/1024/1024:.1f}GB, 连接数: {connections}"
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
            ws_url = f"{self.endpoint.replace('http', 'ws')}/api/clients/report?token={self.token}"
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_websocket_open,
                on_message=self.on_websocket_message,
                on_error=self.on_websocket_error,
                on_close=self.on_websocket_close
            )
            
            self.ws.run_forever()
            
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
                # 获取并上报监控数据
                monitoring_data = self.format_monitoring_data()
                
                # 通过WebSocket发送数据
                if hasattr(self, 'ws') and self.ws and self.ws.sock and self.ws.sock.connected:
                    self.ws.send(json.dumps(monitoring_data))
                
                # 检查是否需要上报基础信息
                current_time = time.time()
                if current_time - self.last_basic_info_report >= self.info_report_interval * 60:
                    self.report_basic_info()
                
                # 等待下一次监控
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(self.interval)
        
        logger.info("监控循环已停止")
    
    def start(self):
        """启动监控代理"""
        try:
            logger.info("启动iKuai监控代理...")
            
            # 登录ikuai
            if not self.ikuai_client.login():
                logger.error("ikuai登录失败，程序退出")
                return False
            
            # 上报基础信息
            self.report_basic_info()
            
            # 启动WebSocket连接
            self.start_websocket_connection()
            
            # 启动监控循环
            self.monitoring_loop()
            
            logger.info("✓ iKuai监控代理启动成功！")
            logger.info("✓ 基础信息已上报到Komari服务器")
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
        # 创建监控代理实例（使用配置文件中的默认值）
        agent = IkuaiAgent()
        
        if args.test:
            # 测试模式
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