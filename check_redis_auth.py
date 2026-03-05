#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 Redis 版本和认证方式"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import cfg

redis_url = cfg.get("redis.url", "")

if not redis_url:
    print("Redis URL 未配置")
    sys.exit(1)

print("=" * 60)
print("Redis 认证检查")
print("=" * 60)

# 解析 URL
from urllib.parse import urlparse

parsed = urlparse(redis_url)

print(f"\n当前配置:")
print(f"  主机: {parsed.hostname}")
print(f"  端口: {parsed.port}")
print(f"  数据库: {parsed.path.lstrip('/') if parsed.path else '0'}")

if parsed.username or parsed.password:
    print(f"  用户名: {parsed.username or '(无)'}")
    print(f"  密码: {'***' if parsed.password else '(无)'}")

print("\n尝试连接...")

import redis

# 测试不同格式
test_urls = []

if parsed.password and not parsed.username:
    # 当前只有密码，尝试不同格式
    test_urls = [
        ("当前配置", redis_url),
        ("修正格式（密码前加冒号）", f"redis://:{parsed.password}@{parsed.hostname}:{parsed.port}{parsed.path}"),
        ("使用 default 用户名", f"redis://default:{parsed.password}@{parsed.hostname}:{parsed.port}{parsed.path}"),
    ]
elif parsed.username and parsed.password:
    test_urls = [
        ("当前配置", redis_url),
        ("只用密码", f"redis://:{parsed.password}@{parsed.hostname}:{parsed.port}{parsed.path}"),
    ]
else:
    test_urls = [("当前配置", redis_url)]

for desc, url in test_urls:
    print(f"\n尝试 {desc}:")
    try:
        client = redis.from_url(url, socket_connect_timeout=3)
        info = client.info('server')
        
        print(f"  ✓ 连接成功！")
        print(f"  Redis 版本: {info.get('redis_version', '未知')}")
        
        # 检查认证模式
        if float(info.get('redis_version', '0').split('.')[0]) >= 6:
            print(f"  认证方式: ACL (Redis 6.0+)")
            print(f"  建议格式: redis://username:password@host:port/db")
        else:
            print(f"  认证方式: 传统密码 (Redis < 6.0)")
            print(f"  建议格式: redis://:password@host:port/db")
        
        print(f"\n正确的 URL 格式:")
        print(f"  {url}")
        
        client.close()
        sys.exit(0)
        
    except redis.exceptions.AuthenticationError as e:
        print(f"  ✗ 认证失败: {e}")
    except redis.exceptions.ConnectionError as e:
        print(f"  ✗ 连接失败: {e}")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

print("\n所有格式都失败了，请检查:")
print("  1. Redis 密码是否正确")
print("  2. Redis 用户权限是否被禁用")
print("  3. 使用 redis-cli 测试连接:")
print(f"     redis-cli -h {parsed.hostname} -p {parsed.port}")
if parsed.password:
    print(f"     > AUTH {parsed.username or ''} {parsed.password}")
