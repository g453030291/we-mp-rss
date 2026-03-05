#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试 Redis 连接"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Redis 连接快速测试")
print("=" * 60)

# 1. 检查 Redis 包
print("\n1. 检查 Redis 包...")
try:
    import redis
    print(f"✓ Redis 包已安装，版本: {redis.__version__}")
except ImportError as e:
    print(f"✗ Redis 包未安装: {e}")
    print("  请运行: pip install redis==7.2.1")
    sys.exit(1)

# 2. 检查配置
print("\n2. 检查 Redis 配置...")
from core.config import cfg

redis_url = cfg.get("redis.url", "")
if redis_url:
    # 隐藏密码显示
    safe_url = redis_url
    if '@' in redis_url:
        parts = redis_url.split('@')
        if ':' in parts[0].split('://')[-1]:
            protocol = parts[0].split('://')[0]
            safe_url = f"{protocol}://***@{parts[1]}"
    print(f"✓ Redis URL: {safe_url}")
else:
    print("✗ Redis URL 未配置")
    print("\n配置方法：")
    print("  方式1 - 在 config.yaml 中添加:")
    print("    redis:")
    print("      url: redis://localhost:6379/0")
    print("  方式2 - 设置环境变量:")
    print("    set REDIS_URL=redis://localhost:6379/0")
    sys.exit(1)

# 3. 测试连接
print("\n3. 测试 Redis 连接...")
try:
    client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    
    # 测试 ping
    result = client.ping()
    print(f"✓ Redis 服务响应: {result}")
    
    # 测试基本操作
    test_key = "werss:test:connection"
    client.set(test_key, "test", ex=10)
    value = client.get(test_key)
    client.delete(test_key)
    
    if value == "test":
        print("✓ Redis 读写测试成功")
    
except redis.exceptions.ConnectionError as e:
    print(f"✗ 连接失败: {e}")
    print("\n可能的原因:")
    print("  1. Redis 服务未启动")
    print("     - Windows: 运行 redis-server.exe")
    print("     - Linux/Mac: 运行 redis-server 或 systemctl start redis")
    print("  2. Redis 地址或端口错误")
    print("     - 测试: redis-cli ping")
    print("  3. 防火墙阻止连接")
    sys.exit(1)
    
except redis.exceptions.AuthenticationError as e:
    print(f"✗ 认证失败: {e}")
    print("  请检查 Redis 密码配置是否正确")
    sys.exit(1)
    
except Exception as e:
    print(f"✗ 错误: {type(e).__name__} - {e}")
    sys.exit(1)

# 4. 测试环境异常记录功能
print("\n4. 测试环境异常记录功能...")
try:
    from core.redis_client import record_env_exception, get_env_exception_stats
    
    success = record_env_exception(
        url="https://test.com/test",
        mp_name="测试公众号",
        mp_id="MP_TEST"
    )
    
    if success:
        print("✓ 环境异常记录功能正常")
        
        stats = get_env_exception_stats()
        print(f"✓ 统计查询功能正常，今日异常数: {stats.get('total', 0)}")
    else:
        print("✗ 环境异常记录失败")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ 功能测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ 所有测试通过！Redis 连接正常")
print("=" * 60)
