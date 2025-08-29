## 1. 安装系统依赖

### Debian/Ubuntu
```bash
sudo apt-get update
sudo apt-get install -y curl unzip python3 python3-pip python3-venv
```

### CentOS/RHEL
```bash
sudo yum install -y curl unzip python3 python3-pip python3-venv
```

## 2. 下载项目文件

```bash
cd /tmp
curl -L -o ikuai-komari-agent.zip https://github.com/ZeroTwoDa/ikuai-komari-agent/archive/refs/heads/main.zip
unzip ikuai-komari-agent.zip
cd ikuai-komari-agent-main
```

## 3. 创建安装目录

```bash
sudo mkdir -p /opt/ikuai_Komari_agent
```

## 4. 创建Python虚拟环境

```bash
sudo python3 -m venv /opt/ikuai_Komari_agent/venv
```

## 5. 复制程序文件

```bash
sudo cp ikuai_komari_agent.py /opt/ikuai_Komari_agent/
sudo cp ikuai_client.py /opt/ikuai_Komari_agent/
sudo cp config.py /opt/ikuai_Komari_agent/
sudo chmod +x /opt/ikuai_Komari_agent/ikuai_komari_agent.py
sudo chown -R root:root /opt/ikuai_Komari_agent
```

## 6. 安装Python依赖

```bash
sudo /opt/ikuai_Komari_agent/venv/bin/pip install --upgrade pip
sudo /opt/ikuai_Komari_agent/venv/bin/pip install requests websocket-client psutil
```

## 7. 配置连接信息

编辑配置文件：
```bash
sudo nano /opt/ikuai_Komari_agent/config.py
```

修改以下配置：
```python
# iKuai路由器配置
IKUAI_CONFIG = {
    "base_url": "http://192.168.1.1",  # 修改为你的iKuai地址
    "username": "admin",               # 修改为你的用户名
    "password": "password",            # 修改为你的密码
    "timeout": 10
}

# Komari服务器配置
KOMARI_CONFIG = {
    "endpoint": "https://komari.server.com",  # 修改为你的Komari服务器地址
    "token": "your_token",                    # 修改为你的认证令牌
    "websocket_interval": 1.0,
    "basic_info_interval": 5,
    "ignore_unsafe_cert": False
}
```

## 8. 创建systemd服务

```bash
sudo tee /etc/systemd/system/ikuai_Komari_agent.service > /dev/null << EOF
[Unit]
Description=iKuai Komari Monitoring Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ikuai_komari_agent
ExecStart=/opt/ikuai_komari_agent/venv/bin/python /opt/ikuai_komari_agent/ikuai_komari_agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

## 9. 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable ikuai_Komari_agent
sudo systemctl start ikuai_Komari_agent
```

## 10. 检查服务状态

```bash
sudo systemctl status ikuai_Komari_agent
sudo journalctl -u ikuai_Komari_agent -f
```

## 11. 卸载命令

```bash
sudo systemctl stop ikuai_Komari_agent
sudo systemctl disable ikuai_Komari_agent
sudo rm /etc/systemd/system/ikuai_Komari_agent.service
sudo systemctl daemon-reload
sudo rm -rf /opt/ikuai_Komari_agent
``` 
