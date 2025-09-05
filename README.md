# iKuai Komari 监控代理

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](https://www.linux.org/)

一个用于监控iKuai路由器并将数据上报到Komari服务器的Python代理程序。

## ✨ 功能特性

- 🔄 实时监控iKuai路由器状态
- 📊 自动上报数据到Komari服务器
- 🔐 智能会话管理和自动重连
- 📝 优化的日志输出
- 🛡️ 完善的错误处理

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 复制配置文件
cp env.example .env

# 2. 编辑配置文件，设置你的路由器和服务器信息
nano .env

# 3. 启动服务
docker-compose up -d

# 4. 查看运行状态
docker-compose logs -f
```

### 方式二：传统安装

#### 安装文档

[安装文档](https://github.com/ZeroTwoDa/ikuai-komari-agent/blob/main/Install.md)

#### 配置信息

安装过程中需要输入以下信息：

- **iKuai地址**: 如 `http://192.168.1.1`
- **iKuai用户名**: 如 `komari_user`
- **iKuai密码**: 如 `komari_password`
- **Komari服务器地址**: 如 `https://komari.server.com`
- **Komari认证令牌**: 输入认证令牌

## 🔧 服务管理

### Docker 部署管理

```bash
# 查看容器状态
docker-compose ps

# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看实时日志
docker-compose logs -f

# 重新构建并启动
docker-compose up --build -d

# 进入容器调试
docker-compose exec ikuai-komari-agent bash
```

### 传统部署管理

```bash
# 查看服务状态
sudo systemctl status ikuai_Komari_agent

# 启动服务
sudo systemctl start ikuai_Komari_agent

# 停止服务
sudo systemctl stop ikuai_Komari_agent

# 重启服务
sudo systemctl restart ikuai_Komari_agent

# 查看实时日志
sudo journalctl -u ikuai_Komari_agent -f

# 查看程序日志
sudo tail -f /opt/ikuai_Komari_agent/ikuai_agent.log
```

## 📊 监控数据

程序会监控并上报以下数据：

- **CPU使用率**：实时CPU使用情况
- **内存使用**：总内存和已使用内存
- **磁盘使用**：总容量和已使用空间
- **网络流量**：实时上传/下载速度和总流量
- **连接数**：当前TCP连接数
- **运行时间**：iKuai路由器运行时间
- **负载信息**：基于CPU使用率的智能估算

## 🔒 安全建议

### iKuai账户设置

为了安全和权限管理，建议在iKuai Web页面中创建一个单独的账户用于此代理程序：

1. **登录iKuai Web管理界面**
2. 导航到 **系统设置** → **登录管理** → **账号设置**
3. 点击 **添加** 或 **修改** 现有账户
4. **用户名**：例如 `komari_user`
5. **密码**：设置一个强密码
6. **允许访问IP**：设置为部署代理机器的内网IP地址
7. **默认权限**：选择 **新功能可见**
8. **登录状态超时时间**：设置为最高 `999` 分钟
9. **权限等级设置**：
   - 在 **页面权限** 列表中，只勾选 **访问** 列
   - 确保 **修改** 列全部不勾选，以限制代理程序只能读取数据

## ⚙️ 环境变量配置

### 核心配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `IKUAI_BASE_URL` | `http://192.168.1.1` | iKuai路由器管理地址 |
| `IKUAI_USERNAME` | `admin` | iKuai登录用户名 |
| `IKUAI_PASSWORD` | `admin` | iKuai登录密码 |
| `KOMARI_ENDPOINT` | `https://komari.server.com` | Komari服务器地址 |
| `KOMARI_TOKEN` | `your_token_here` | Komari认证令牌 |

### 可选配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `IKUAI_TIMEOUT` | `10` | iKuai请求超时时间(秒) |
| `KOMARI_WEBSOCKET_INTERVAL` | `1.0` | WebSocket数据上报间隔(秒) |
| `KOMARI_BASIC_INFO_INTERVAL` | `5` | 基础信息上报间隔(分钟) |
| `KOMARI_IGNORE_UNSAFE_CERT` | `False` | 忽略不安全的SSL证书 |

### 日志配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LOG_LEVEL` | `WARNING` | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FILE` | `ikuai_agent.log` | 日志文件名 |
| `LOG_MAX_BYTES` | `10485760` | 单个日志文件最大大小(字节) |
| `LOG_BACKUP_COUNT` | `3` | 日志备份文件数量 |

### 配置示例

```bash
# .env 文件示例
IKUAI_BASE_URL=http://192.168.1.1
IKUAI_USERNAME=monitor_user
IKUAI_PASSWORD=your_secure_password
KOMARI_ENDPOINT=https://your-komari-server.com
KOMARI_TOKEN=your_actual_token

# 可选：如果使用自签名SSL证书
KOMARI_IGNORE_UNSAFE_CERT=True

# 可选：调整上报频率
KOMARI_WEBSOCKET_INTERVAL=2.0
KOMARI_BASIC_INFO_INTERVAL=10
```

## 🗂️ 项目结构

```
ikuai-komari-agent-docker/
├── ikuai_komari_agent.py    # 主程序
├── ikuai_client.py          # iKuai API客户端
├── config.py                # 配置文件（支持环境变量）
├── requirements.txt         # Python依赖包
├── Dockerfile              # Docker镜像构建文件
├── docker-compose.yml      # Docker编排文件
├── .dockerignore          # Docker构建忽略文件
├── env.example            # 环境变量配置模板
└── README.md              # 说明文档
```

## 🔍 故障排除

### Docker 部署问题

1. **容器无法启动**：
   ```bash
   # 查看容器状态和错误
   docker-compose ps
   docker-compose logs ikuai-komari-agent
   ```

2. **无法连接iKuai路由器**：
   - 检查 `IKUAI_BASE_URL` 配置是否正确
   - 确认用户名密码是否正确
   - 检查网络连通性：`ping 192.168.1.1`

3. **无法连接Komari服务器**：
   - 检查 `KOMARI_ENDPOINT` 和 `KOMARI_TOKEN` 配置
   - 如果使用自签名证书，设置 `KOMARI_IGNORE_UNSAFE_CERT=True`

4. **权限问题**：
   ```bash
   # 检查并修复日志目录权限
   sudo chown -R $(id -u):$(id -g) ./logs
   ```

### 手动卸载

#### Docker 部署卸载

```bash
# 停止并移除容器
docker-compose down

# 删除镜像（可选）
docker rmi ikuai-komari-agent-docker_ikuai-komari-agent

# 清理未使用的Docker资源
docker system prune -f
```

#### 传统部署卸载

```bash
# 停止服务
sudo systemctl stop ikuai_Komari_agent

# 禁用服务
sudo systemctl disable ikuai_Komari_agent

# 删除服务文件
sudo rm /etc/systemd/system/ikuai_Komari_agent.service

# 重新加载systemd
sudo systemctl daemon-reload

# 删除安装目录
sudo rm -rf /opt/ikuai_Komari_agent
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⭐ 星标

如果这个项目对您有帮助，请给它一个星标 ⭐

---

**注意**: 请确保在使用前正确配置iKuai路由器和Komari服务器的连接信息。 
