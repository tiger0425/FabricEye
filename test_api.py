#!/usr/bin/env python3
"""
FabricEye API 测试脚本
在本地运行FastAPI服务后，使用此脚本测试所有API端点

使用方法:
1. 先启动后端服务: uvicorn app.main:app --reload
2. 运行测试脚本: python test_api.py
"""

import requests
import json
import sys
from datetime import datetime

# API基础配置
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# 测试报告
test_results = []


def log_test(name, status, details=""):
    """记录测试结果"""
    result = {
        "name": name,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    icon = "✅" if status == "PASS" else "❌"
    print(f"{icon} {name}: {status}")
    if details:
        print(f"   Details: {details}")


def test_health():
    """测试健康检查端点"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("Health Check", "PASS", f"Status: {data.get('status', 'unknown')}")
            return True
        else:
            log_test("Health Check", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("Health Check", "FAIL", str(e))
        return False


def test_create_roll():
    """测试创建布卷"""
    try:
        payload = {
            "roll_number": f"TEST_{datetime.now().strftime('%H%M%S')}",
            "fabric_type": "涤纶平纹",
            "batch_number": "LOT-2025-001",
            "length_meters": 500.0
        }
        response = requests.post(
            f"{API_V1}/rolls/",
            json=payload,
            timeout=5
        )
        if response.status_code in [200, 201]:
            data = response.json()
            log_test("Create Roll", "PASS", f"ID: {data.get('id')}")
            return data.get('id')
        else:
            log_test("Create Roll", "FAIL", f"HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        log_test("Create Roll", "FAIL", str(e))
        return None


def test_list_rolls():
    """测试获取布卷列表"""
    try:
        response = requests.get(f"{API_V1}/rolls/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            log_test("List Rolls", "PASS", f"Count: {count}")
            return True
        else:
            log_test("List Rolls", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("List Rolls", "FAIL", str(e))
        return False


def test_get_roll(roll_id):
    """测试获取单个布卷"""
    if not roll_id:
        log_test("Get Roll", "SKIP", "No roll_id provided")
        return False
    
    try:
        response = requests.get(f"{API_V1}/rolls/{roll_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("Get Roll", "PASS", f"Found: {data.get('roll_number')}")
            return True
        else:
            log_test("Get Roll", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("Get Roll", "FAIL", str(e))
        return False


def test_update_roll(roll_id):
    """测试更新布卷"""
    if not roll_id:
        log_test("Update Roll", "SKIP", "No roll_id provided")
        return False
    
    try:
        payload = {
            "status": "recording",
            "length_meters": 550.0
        }
        response = requests.put(
            f"{API_V1}/rolls/{roll_id}",
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            log_test("Update Roll", "PASS", f"New status: {data.get('status')}")
            return True
        else:
            log_test("Update Roll", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("Update Roll", "FAIL", str(e))
        return False


def test_delete_roll(roll_id):
    """测试删除布卷"""
    if not roll_id:
        log_test("Delete Roll", "SKIP", "No roll_id provided")
        return False
    
    try:
        response = requests.delete(f"{API_V1}/rolls/{roll_id}", timeout=5)
        if response.status_code in [200, 204]:
            log_test("Delete Roll", "PASS", "Deleted successfully")
            return True
        else:
            log_test("Delete Roll", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("Delete Roll", "FAIL", str(e))
        return False


def test_swagger_ui():
    """测试Swagger文档"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200 and "swagger" in response.text.lower():
            log_test("Swagger UI", "PASS", "Documentation accessible")
            return True
        else:
            log_test("Swagger UI", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("Swagger UI", "FAIL", str(e))
        return False


def test_openapi_schema():
    """测试OpenAPI规范"""
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            paths = list(data.get('paths', {}).keys())
            log_test("OpenAPI Schema", "PASS", f"Paths: {len(paths)}")
            return True
        else:
            log_test("OpenAPI Schema", "FAIL", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("OpenAPI Schema", "FAIL", str(e))
        return False


def print_summary():
    """打印测试摘要"""
    print("\n" + "="*60)
    print("📊 API测试摘要")
    print("="*60)
    
    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = sum(1 for r in test_results if r['status'] == 'FAIL')
    skipped = sum(1 for r in test_results if r['status'] == 'SKIP')
    total = len(test_results)
    
    print(f"总计: {total} | 通过: {passed} ✅ | 失败: {failed} ❌ | 跳过: {skipped} ⏭️")
    print(f"成功率: {passed/total*100:.1f}%" if total > 0 else "N/A")
    
    if failed > 0:
        print("\n失败的测试:")
        for r in test_results:
            if r['status'] == 'FAIL':
                print(f"  - {r['name']}: {r['details']}")
    
    print("="*60)


def main():
    """主测试流程"""
    print("🚀 FabricEye API 测试开始")
    print(f"目标: {BASE_URL}")
    print("="*60)
    
    # 测试服务可用性
    if not test_health():
        print("\n❌ 服务未启动，请先运行:")
        print("   cd backend && uvicorn app.main:app --reload")
        sys.exit(1)
    
    # 测试文档
    test_swagger_ui()
    test_openapi_schema()
    
    # 测试布卷CRUD
    test_list_rolls()
    roll_id = test_create_roll()
    
    if roll_id:
        test_get_roll(roll_id)
        test_update_roll(roll_id)
        test_delete_roll(roll_id)
    
    # 打印摘要
    print_summary()
    
    # 返回退出码
    failed = sum(1 for r in test_results if r['status'] == 'FAIL')
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
