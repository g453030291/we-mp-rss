# Redis 连接失败快速修复指南

## 问题诊断

### 1. 运行诊断工具

```bash
python diagnose_redis.py
```

或使用快速测试：

```bash
python quick_test_redis.py
```

### 2. 检查 Redis 服务状态

#### Windows
```bash
# 检查 Redis 是否在运行
tasklist | findstr redis

# 启动 Redis（如果已安装）
redis-server.exe

# 测试连接
redis-cli ping
```

#### Linux/Mac
```bash
# 检查 Redis 服务状态
systemctl status redis
# 或
service redis status

# 启动 Redis
systemctl start redis
# 或
service redis start

# 测试连接
redis-cli ping
```

## 常见问题和解决方案

### 问题 1: Redis 服务未启动

**症状:**
```
✗ 连接失败: Error 10061: 由于目标计算机积极拒绝，无法连接
```

**解决方案:**

1. **Windows:**
   ```bash
   # 方式1: 直接运行
   redis-server.exe
   
   # 方式2: 作为服务安装
   redis-server.exe --service-install redis.windows.conf
   redis-server.exe --service-start
   ```

2. **Linux:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis
   
   # CentOS/RHEL
   sudo yum install redis
   sudo systemctl start redis
   ```

3. **Mac:**
   ```bash
   brew install redis
   brew services start redis
   ```

4. **Docker:**
   ```bash
   docker run -d -p 6379:6379 --name redis redis:7-alpine
   ```

### 问题 2: Redis URL 未配置

**症状:**
```
✗ Redis URL 未配置
```

**解决方案:**

选择以下任一方式配置：

**方式 1: 修改 config.yaml**
```yaml
redis:
  url: redis://localhost:6379/0
```

**方式 2: 设置环境变量**

Windows:
```cmd
set REDIS_URL=redis://localhost:6379/0
```

Linux/Mac:
```bash
export REDIS_URL=redis://localhost:6379/0
```

**方式 3: Docker Compose**
```yaml
services:
  web:
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
```

### 问题 3: 认证失败

**症状:**
```
✗ 认证失败: Authentication failed
```

**解决方案:**

检查 Redis 是否需要密码：

```bash
# 连接 Redis
redis-cli

# 检查是否需要密码
> ping
# 如果返回 NOAUTH，则需要密码
```

修改配置：

```yaml
# 无密码
redis:
  url: redis://localhost:6379/0

# 有密码
redis:
  url: redis://:your_password@localhost:6379/0
```

### 问题 4: 连接超时

**症状:**
```
✗ 连接超时: Timeout connecting to server
```

**解决方案:**

1. **检查防火墙:**
   ```bash
   # Windows - 允许端口 6379
   netsh advfirewall firewall add rule name="Redis" dir=in action=allow protocol=tcp localport=6379
   
   # Linux - 使用 ufw
   sudo ufw allow 6379
   ```

2. **检查 Redis 绑定地址:**
   
   编辑 `redis.conf`:
   ```conf
   # 允许所有连接（开发环境）
   bind 0.0.0.0
   
   # 或只允许本地
   bind 127.0.0.1
   ```

3. **检查网络连接:**
   ```bash
   # 测试端口是否可达
   telnet localhost 6379
   # 或
   nc -zv localhost 6379
   ```

### 问题 5: Redis 包未安装

**症状:**
```
✗ Redis 包未安装: No module named 'redis'
```

**解决方案:**

```bash
pip install redis==7.2.1
```

或使用项目的 requirements.txt：

```bash
pip install -r requirements.txt
```

## 配置示例

### 本地开发环境

```yaml
# config.yaml
redis:
  url: redis://localhost:6379/0
```

### Docker 环境

```yaml
# config.yaml
redis:
  url: redis://redis:6379/0  # redis 是容器名
```

### 生产环境（带密码）

```yaml
# config.yaml
redis:
  url: redis://:strong_password@redis.example.com:6379/0
```

### Redis SSL 连接

```yaml
# config.yaml
redis:
  url: rediss://:password@redis.example.com:6379/0
```

## 验证连接

### 1. 使用 Redis CLI

```bash
# 连接 Redis
redis-cli

# 测试基本操作
127.0.0.1:6379> ping
PONG

127.0.0.1:6379> SET test "hello"
OK

127.0.0.1:6379> GET test
"hello"
```

### 2. 使用 Python

```python
import redis

# 连接 Redis
r = redis.from_url("redis://localhost:6379/0")

# 测试
r.ping()  # 返回 True
```

### 3. 检查环境异常统计

```bash
# 访问 API
curl http://localhost:8001/api/env-exception/today \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 无需 Redis 运行

如果暂时不需要环境异常统计功能，可以：

1. **不配置 Redis URL** - 系统会自动禁用统计功能
2. **Redis 连接失败** - 不影响文章获取等核心功能

统计功能是可选的增强功能，不影响系统正常运行。

## 获取帮助

如果以上方法都无法解决问题：

1. 查看详细诊断：
   ```bash
   python diagnose_redis.py
   ```

2. 检查日志文件中的错误信息

3. 提交 Issue 并附带：
   - 诊断工具输出
   - Redis 配置（隐藏密码）
   - 操作系统版本
   - Python 版本
