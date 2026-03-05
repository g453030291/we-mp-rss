#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Redis 连接诊断工具"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import cfg
from core.print import print_info, print_error, print_success, print_warning


def diagnose_redis():
    """诊断 Redis 连接问题"""
    print("=" * 60)
    print("Redis 连接诊断工具")
    print("=" * 60)
    
    # 1. 检查 Redis 是否已安装
    print("\n[1/5] 检查 Redis 依赖...")
    try:
        import redis
        print_success(f"✓ Redis 包已安装，版本: {redis.__version__}")
    except ImportError:
        print_error("✗ Redis 包未安装")
        print_info("请运行: pip install redis==7.2.1")
        return False
    
    # 2. 检查配置
    print("\n[2/5] 检查 Redis 配置...")
    redis_url = cfg.get("redis.url", "")
    
    if not redis_url:
        print_warning("⚠ Redis URL 未配置")
        print_info("配置方式：")
        print_info("  方式1: 在 config.yaml 中设置")
        print_info("    redis:")
        print_info("      url: redis://localhost:6379/0")
        print_info("  方式2: 设置环境变量")
        print_info("    export REDIS_URL=redis://localhost:6379/0")
        print_info("  方式3: 使用带密码的连接")
        print_info("    redis://:password@localhost:6379/0")
        return False
    else:
        # 隐藏密码
        safe_url = redis_url
        if '@' in redis_url:
            parts = redis_url.split('@')
            if ':' in parts[0].split('://')[-1]:
                protocol = parts[0].split('://')[0]
                safe_url = f"{protocol}://***@{parts[1]}"
        
        print_success(f"✓ Redis URL 已配置: {safe_url}")
    
    # 3. 测试 Redis 服务连接
    print("\n[3/5] 测试 Redis 服务连接...")
    try:
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # 测试 ping
        result = client.ping()
        print_success(f"✓ Redis 服务响应: {result}")
        
    except redis.exceptions.ConnectionError as e:
        print_error(f"✗ 连接失败: {e}")
        print_info("\n可能的原因：")
        print_info("  1. Redis 服务未启动")
        print_info("     解决: 启动 Redis 服务")
        print_info("       Windows: redis-server.exe")
        print_info("       Linux/Mac: redis-server 或 systemctl start redis")
        print_info("  2. Redis 主机地址或端口错误")
        print_info("     检查: 确认 Redis 运行在配置的地址和端口")
        print_info("       测试: redis-cli ping")
        print_info("  3. 防火墙阻止连接")
        print_info("     解决: 检查防火墙规则或使用本地 Redis")
        return False
        
    except redis.exceptions.AuthenticationError as e:
        print_error(f"✗ 认证失败: {e}")
        print_info("\n可能的原因：")
        print_info("  1. Redis 密码错误")
        print_info("     检查: 确认 Redis 配置的密码正确")
        print_info("  2. Redis 未设置密码但配置中包含密码")
        print_info("     解决: 移除 URL 中的密码部分")
        return False
        
    except redis.exceptions.TimeoutError as e:
        print_error(f"✗ 连接超时: {e}")
        print_info("\n可能的原因：")
        print_info("  1. Redis 服务响应慢")
        print_info("  2. 网络延迟高")
        print_info("  3. Redis 服务器负载过高")
        return False
        
    except Exception as e:
        print_error(f"✗ 未知错误: {e}")
        print_error(f"   错误类型: {type(e).__name__}")
        return False
    
    # 4. 测试基本操作
    print("\n[4/5] 测试 Redis 基本操作...")
    try:
        test_key = "werss:test:connection"
        test_value = "test_value"
        
        # 设置值
        client.set(test_key, test_value, ex=10)  # 10秒过期
        print_success("✓ SET 操作成功")
        
        # 获取值
        result = client.get(test_key)
        if result == test_value:
            print_success("✓ GET 操作成功")
        else:
            print_error(f"✗ GET 结果不匹配: {result}")
            return False
        
        # 删除测试键
        client.delete(test_key)
        print_success("✓ DELETE 操作成功")
        
    except Exception as e:
        print_error(f"✗ 操作失败: {e}")
        return False
    
    # 5. 测试环境异常记录功能
    print("\n[5/5] 测试环境异常记录功能...")
    try:
        from core.redis_client import record_env_exception, get_env_exception_stats
        
        # 测试记录
        success = record_env_exception(
            url="https://test.com/test",
            mp_name="测试公众号",
            mp_id="MP_TEST"
        )
        
        if success:
            print_success("✓ 环境异常记录功能正常")
            
            # 测试查询
            stats = get_env_exception_stats()
            print_success(f"✓ 统计查询功能正常，今日异常数: {stats.get('total', 0)}")
        else:
            print_error("✗ 环境异常记录失败")
            return False
            
    except Exception as e:
        print_error(f"✗ 功能测试失败: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False
    
    # 所有测试通过
    print("\n" + "=" * 60)
    print_success("✓ 所有诊断测试通过！Redis 连接正常")
    print("=" * 60)
    return True


def check_redis_service():
    """检查 Redis 服务状态"""
    print("\n" + "=" * 60)
    print("Redis 服务检查")
    print("=" * 60)
    
    import socket
    
    # 常见 Redis 端口
    redis_url = cfg.get("redis.url", "")
    default_ports = [6379]
    
    if redis_url:
        try:
            # 从 URL 中提取主机和端口
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            default_ports = [port]
            
            print_info(f"检查主机: {host}:{port}")
            
            # 测试端口是否开放
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print_success(f"✓ 端口 {port} 开放")
            else:
                print_error(f"✗ 端口 {port} 无法访问")
                print_info("  可能 Redis 服务未启动或防火墙阻止连接")
                
        except Exception as e:
            print_error(f"检查失败: {e}")
    
    # 检查本地 Redis
    print_info("\n检查本地 Redis 服务:")
    for port in default_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print_success(f"✓ 本地 Redis 端口 {port} 开放")
            else:
                print_warning(f"⚠ 本地 Redis 端口 {port} 未监听")
        except:
            pass


def show_config_examples():
    """显示配置示例"""
    print("\n" + "=" * 60)
    print("Redis 配置示例")
    print("=" * 60)
    
    print_info("\n1. 本地 Redis (无密码):")
    print_info("   redis:")
    print_info("     url: redis://localhost:6379/0")
    print_info("   或环境变量:")
    print_info("   export REDIS_URL=redis://localhost:6379/0")
    
    print_info("\n2. 本地 Redis (有密码):")
    print_info("   redis:")
    print_info("     url: redis://:your_password@localhost:6379/0")
    
    print_info("\n3. 远程 Redis:")
    print_info("   redis:")
    print_info("     url: redis://:password@redis.example.com:6379/0")
    
    print_info("\n4. Redis SSL 连接:")
    print_info("   redis:")
    print_info("     url: rediss://:password@redis.example.com:6379/0")
    
    print_info("\n5. Docker 环境:")
    print_info("   redis:")
    print_info("     url: redis://redis:6379/0")
    print_info("   (假设 Redis 容器名称为 redis)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis 连接诊断工具")
    parser.add_argument('--check-service', action='store_true', help='检查 Redis 服务状态')
    parser.add_argument('--show-config', action='store_true', help='显示配置示例')
    
    args = parser.parse_args()
    
    if args.check_service:
        check_redis_service()
    elif args.show_config:
        show_config_examples()
    else:
        # 运行完整诊断
        diagnose_redis()
        check_redis_service()
        show_config_examples()
