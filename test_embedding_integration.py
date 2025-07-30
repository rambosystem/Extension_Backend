#!/usr/bin/env python3
"""
测试embedding集成功能
"""

import os
import sys
import logging
import requests
import time
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API基础URL
BASE_URL = "http://localhost:8000"


def test_embedding_status():
    """测试embedding状态API"""
    print("🔍 Testing embedding status API...")

    try:
        # 获取embedding状态
        response = requests.get(f"{BASE_URL}/embedding/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Embedding status: {data['embedding_status']}")
            print(f"📅 Last embedding time: {data['last_embedding_time']}")
            return data
        else:
            print(f"❌ Failed to get embedding status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error testing embedding status: {e}")
        return None


def test_user_terms_status(user_id: int):
    """测试用户术语状态API"""
    print(f"🔍 Testing user terms status for user {user_id}...")

    try:
        response = requests.get(f"{BASE_URL}/users/{user_id}/terms/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Total terms: {data['total_terms']}")
            print(f"🔧 Embedding status: {data['embedding_status']}")
            print(f"📅 Last embedding time: {data['last_embedding_time']}")
            return data
        else:
            print(f"❌ Failed to get user terms status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error testing user terms status: {e}")
        return None


def test_embedding_build(user_id: int):
    """测试embedding构建API"""
    print(f"🔨 Testing embedding build for user {user_id}...")

    try:
        response = requests.post(f"{BASE_URL}/embedding/build/user/{user_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Build task started: {data['message']}")
            print(f"🔄 Status: {data['status']}")
            return data
        else:
            print(f"❌ Failed to start build: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error testing embedding build: {e}")
        return None


def test_embedding_search(query: str):
    """测试embedding搜索API"""
    print(f"🔍 Testing embedding search for query: '{query}'...")

    try:
        response = requests.get(f"{BASE_URL}/embedding/search", params={
            "query": query,
            "top_k": 5,
            "threshold": 0.7
        })
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search results: {data['total_results']} matches")
            for result in data['results']:
                print(
                    f"  - Term ID: {result['term_id']}, Score: {result['similarity_score']:.4f}")
            return data
        else:
            print(f"❌ Failed to search: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error testing embedding search: {e}")
        return None


def test_embedding_stats():
    """测试embedding统计API"""
    print("📊 Testing embedding stats API...")

    try:
        response = requests.get(f"{BASE_URL}/embedding/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Embedding stats:")
            for key, value in data.items():
                print(f"  - {key}: {value}")
            return data
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error testing embedding stats: {e}")
        return None


def test_update_embedding_status(status: str):
    """测试更新embedding状态API"""
    print(f"🔄 Testing update embedding status to: {status}...")

    try:
        response = requests.put(f"{BASE_URL}/embedding/status", json={
            "embedding_status": status,
            "last_embedding_time": datetime.now().isoformat() if status == "success" else None
        })
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status updated: {data['embedding_status']}")
            return data
        else:
            print(f"❌ Failed to update status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error testing status update: {e}")
        return None


def main():
    """主测试函数"""
    print("🔄 Starting embedding integration tests...")

    # 测试用户ID
    test_user_id = 1

    try:
        # 1. 测试embedding状态
        print("\n" + "="*50)
        status_data = test_embedding_status()

        # 2. 测试用户术语状态
        print("\n" + "="*50)
        user_status = test_user_terms_status(test_user_id)

        # 3. 测试embedding统计
        print("\n" + "="*50)
        stats_data = test_embedding_stats()

        # 4. 测试embedding搜索
        print("\n" + "="*50)
        search_data = test_embedding_search("artificial intelligence")

        # 5. 测试状态更新
        print("\n" + "="*50)
        update_data = test_update_embedding_status("building")

        # 6. 测试embedding构建（可选，需要时间）
        print("\n" + "="*50)
        print("⚠️  Note: Embedding build test is commented out as it takes time")
        print("   Uncomment the following line to test building:")
        print("   build_data = test_embedding_build(test_user_id)")

        # build_data = test_embedding_build(test_user_id)

        print("\n" + "="*50)
        print("🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
