# 🚀 快速部署指南

使用预构建的 Docker 镜像，3 分钟完成部署！

## 📋 准备工作

确保你的系统已安装：
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## ⚡ 3步快速部署

### 1️⃣ 下载部署文件

```bash
# 创建项目目录
mkdir ikuai-komari-agent && cd ikuai-komari-agent

# 下载必要文件
wget https://raw.githubusercontent.com/yourusername/ikuai-komari-agent-docker/main/docker-compose.prebuilt.yml
wget https://raw.githubusercontent.com/yourusername/ikuai-komari-agent-docker/main/env.example

# 复制配置模板
cp env.example .env
```

### 2️⃣ 配置参数

编辑 `.env` 文件，填入你的配置：

```bash
nano .env
```

**必须配置的参数：**
```bash
# iKuai 路由器配置
IKUAI_BASE_URL=http://192.168.1.1     # 改为你的路由器地址
IKUAI_USERNAME=your_username           # 改为你的用户名
IKUAI_PASSWORD=your_password           # 改为你的密码

# Komari 服务器配置
KOMARI_ENDPOINT=https://your-server.com # 改为你的服务器地址
KOMARI_TOKEN=your_actual_token          # 改为你的令牌
```

### 3️⃣ 启动服务

```bash
# 启动服务
docker-compose -f docker-compose.prebuilt.yml up -d

# 查看运行状态
docker-compose -f docker-compose.prebuilt.yml logs -f
```

## ✅ 验证部署

看到类似以下日志说明部署成功：

```
ikuai-komari-agent | ✓ 登录成功，获取到sess_key
ikuai-komari-agent | ✓ iKuai监控代理启动成功！
ikuai-komari-agent | ✓ WebSocket连接已建立
ikuai-komari-agent | ✓ 开始实时监控iKuai路由器数据...
```

## 🔧 常用管理命令

```bash
# 查看状态
docker-compose -f docker-compose.prebuilt.yml ps

# 查看日志
docker-compose -f docker-compose.prebuilt.yml logs -f

# 重启服务
docker-compose -f docker-compose.prebuilt.yml restart

# 停止服务
docker-compose -f docker-compose.prebuilt.yml down

# 更新到最新版本
docker-compose -f docker-compose.prebuilt.yml pull
docker-compose -f docker-compose.prebuilt.yml up -d
```

## 🛠️ 故障排除

### 无法连接 iKuai 路由器

1. 检查路由器地址是否正确
2. 确认用户名密码是否正确
3. 测试网络连通性：`ping 192.168.1.1`

### 无法连接 Komari 服务器

1. 检查服务器地址和令牌是否正确
2. 如果使用自签名证书，添加配置：
   ```bash
   KOMARI_IGNORE_UNSAFE_CERT=True
   ```

### 权限问题

```bash
# 创建日志目录并设置权限
mkdir -p logs
sudo chown -R $(id -u):$(id -g) logs
```

## 📚 更多信息

- 完整文档：[README.md](README.md)
- 环境变量说明：[完整配置表](README.md#️-环境变量配置)
- iKuai 安全配置：[安全建议](README.md#-安全建议)

## 🆘 需要帮助？

如果遇到问题：
1. 查看完整的 [故障排除指南](README.md#-故障排除)
2. 在 GitHub Issues 中搜索相似问题
3. 提交新的 Issue 并附带错误日志

---

**享受轻松的 Docker 部署体验！** 🐳
