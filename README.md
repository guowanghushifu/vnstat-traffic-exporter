# vnstat流量导出器

这是一个基于Python的vnstat流量数据导出工具，提供HTTP API接口来获取网络流量统计数据。

## 功能特性

- 定期（每5分钟）从vnstat读取网络流量数据
- 提供HTTP API接口返回JSON格式的流量数据
- 支持自定义起始日期和webhook路径
- 自动检测可用的网络接口
- 内存缓存数据，提高响应速度

## 安装要求

- Python 3.6+
- vnstat工具已安装并配置
- Flask库

## 安装步骤

1. 安装Python依赖：
```bash
pip install -r requirements.txt
```

2. 确保vnstat已安装：
```bash
# Ubuntu/Debian
sudo apt-get install vnstat

# CentOS/RHEL
sudo yum install vnstat

# macOS
brew install vnstat
```

## 配置

脚本支持以下环境变量配置：

- `WEBHOOK_PATH`: webhook路径（默认：`/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae`）
- `START_DAY`: 每月起始日期（默认：1）
- `PORT`: 服务端口（默认：50000）

## 使用方法

### 🚀 Docker快速开始（推荐）

```bash
# 1. 确保宿主机vnstat服务正在运行
sudo systemctl status vnstat
sudo systemctl start vnstat  # 如果未运行

# 2. 启动容器服务
docker compose up -d

# 3. 查看日志
docker compose logs -f

# 4. 测试API
curl http://localhost:50000/health

# 5. 获取流量数据
curl http://localhost:50000/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae
```

> **重要**：容器读取宿主机vnstat数据，需要确保宿主机的vnstat服务正在运行

### 传统方式使用

```bash
python3 vnstat_traffic_exporter.py
```

### 使用环境变量

```bash
export WEBHOOK_PATH="/webhook/my-secret-path"
export START_DAY="15"
export PORT="8080"
python3 vnstat_traffic_exporter.py
```

### 使用systemd服务（推荐）

创建服务文件 `/etc/systemd/system/vnstat-exporter.service`：

```ini
[Unit]
Description=Vnstat Traffic Exporter
After=network.target

[Service]
Type=simple
User=vnstat
WorkingDirectory=/path/to/vnstat-traffic-exporter
Environment=WEBHOOK_PATH=/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae
Environment=START_DAY=1
Environment=PORT=50000
ExecStart=/usr/bin/python3 vnstat_traffic_exporter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable vnstat-exporter
sudo systemctl start vnstat-exporter
```

## Docker部署

### 构建和运行（推荐）

**使用host网络模式（推荐）：**
```bash
# 构建镜像
docker compose build

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f
```

**使用bridge网络模式：**
```bash
# 使用bridge网络配置文件
docker compose -f docker-compose.bridge.yml up -d
```

> **注意**: 如果您使用的是Docker Compose V1，请将 `docker compose` 替换为 `docker-compose`

### Docker环境配置

您可以通过修改`docker-compose.yml`中的环境变量来配置服务：

```yaml
environment:
  - WEBHOOK_PATH=/webhook/your-custom-path
  - START_DAY=15
  - PORT=50000
```

### 网络模式说明

**Host网络模式（推荐）：**
- 容器直接使用宿主机网络
- 可以完全访问物理网卡数据
- 性能更好，配置更简单

**Bridge网络模式：**
- 容器使用独立网络并映射端口
- 需要特权模式和系统目录挂载
- 适用于有网络隔离需求的环境

**健康检查和日志管理：**
- 健康检查频率：每10分钟检查一次服务状态
- 日志轮转：单个日志文件最大10MB，保留3个文件
- 总日志大小限制：最大30MB（10MB × 3个文件）

### 重要挂载说明

通过host网络模式和适当的权限配置，容器可以直接访问物理网卡流量数据：

> **配置说明**: 
> - 使用**host网络模式**，容器直接访问宿主机网络栈
> - 配置**NET_ADMIN**和**SYS_ADMIN**权限
> - **只读挂载宿主机vnstat数据库**，容器不修改数据，只读取
> - **数据收集**：由宿主机的vnstat daemon负责收集数据
> - **数据读取**：容器内应用只读取宿主机收集的流量数据
> 
> **挂载目录**：
> ```
> /var/lib/vnstat:/var/lib/vnstat:ro    # 只读挂载vnstat数据库
> /etc/vnstat.conf:/etc/vnstat.conf:ro  # 只读挂载vnstat配置
> ```

### Docker命令示例

```bash
# 直接使用Docker运行（host网络）
docker run -d \
  --name vnstat-exporter \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add SYS_ADMIN \
  -v /var/lib/vnstat:/var/lib/vnstat:ro \
  -v /etc/vnstat.conf:/etc/vnstat.conf:ro \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  -e WEBHOOK_PATH=/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae \
  -e START_DAY=1 \
  -e PORT=50000 \
  vnstat-traffic-exporter:latest

# 使用bridge网络
docker run -d \
  --name vnstat-exporter \
  -p 50000:50000 \
  --privileged \
  -v /var/lib/vnstat:/var/lib/vnstat:ro \
  -v /etc/vnstat.conf:/etc/vnstat.conf:ro \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  -e WEBHOOK_PATH=/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae \
  -e START_DAY=1 \
  -e PORT=50000 \
  vnstat-traffic-exporter:latest
```

## API接口

### 获取流量数据

**请求：**
```
GET http://localhost:50000/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae
```

**响应：**
```json
{
    "start_date": "2025-01-15",
    "in": 1024.50,
    "out": 2048.75
}
```

- `start_date`: 统计起始日期
- `in`: 入站流量（MB）
- `out`: 出站流量（MB）

### 健康检查

**请求：**
```
GET http://localhost:50000/health
```

**响应：**
```json
{
    "status": "ok",
    "timestamp": "2025-01-15T10:30:00.123456"
}
```

## 日期计算逻辑

起始日期的计算逻辑如下：

- 如果今天的日期 >= 设定的起始日期：使用本月的起始日期到今天
- 如果今天的日期 < 设定的起始日期：使用上个月的起始日期到今天

**示例：**
- 设定起始日期为15号
- 如果今天是1月25号：统计时间为1月15号到1月25号
- 如果今天是1月10号：统计时间为12月15号到1月10号

## 故障排除

### vnstat命令失败

1. 确认vnstat已正确安装：
```bash
vnstat --version
```

2. 检查网络接口：
```bash
vnstat --iflist
```

3. 手动测试vnstat命令：
```bash
vnstat --json
```

### 权限问题

确保运行脚本的用户有权限执行vnstat命令。

### 端口占用

如果默认端口50000被占用，请使用环境变量`PORT`指定其他端口。

### Docker相关问题

**容器无法获取流量数据：**
1. **检查宿主机vnstat服务**：`sudo systemctl status vnstat`
2. **确保数据库存在**：`ls -la /var/lib/vnstat/`
3. **检查权限**：容器需要能读取宿主机vnstat数据库文件

**权限问题：**
如果容器无法读取宿主机vnstat数据库，检查文件权限：
```bash
# 检查vnstat数据库权限
sudo ls -la /var/lib/vnstat/

# 如果需要，调整权限（让容器用户能读取）
sudo chmod 644 /var/lib/vnstat/*

# 查看容器日志排查问题
docker logs vnstat-exporter
```

**网络接口检测失败：**
```bash
# 检查宿主机vnstat接口列表
sudo vnstat --iflist

# 检查宿主机vnstat数据库状态
sudo vnstat

# 检查容器是否能正确读取数据
docker exec -it vnstat-exporter vnstat --iflist
```

**Docker Compose版本兼容性：**
- 新版本（推荐）：`docker compose`
- 老版本：`docker-compose`
- 脚本会自动检测并使用合适的命令

## 日志

脚本会输出详细的日志信息，包括：
- 初始化信息
- 数据更新状态
- 错误信息
- vnstat命令执行结果

## 注意事项

1. **宿主机vnstat服务**：容器读取宿主机vnstat数据，必须确保宿主机vnstat服务正在运行
2. **数据来源**：流量数据来自宿主机vnstat daemon的收集，容器只负责读取和提供API
3. **只读模式**：容器以只读方式挂载vnstat数据库，不会修改宿主机数据
4. **历史数据**：API返回的历史数据取决于宿主机vnstat的收集时长
5. **流量单位**：API返回的流量数据以MB为单位
6. **服务依赖**：确保宿主机和容器服务都在持续运行
7. **健康检查**：系统每10分钟检查一次服务状态，降低系统开销
8. **日志管理**：自动限制日志文件大小，防止磁盘空间耗尽 