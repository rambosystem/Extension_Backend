#!/usr/bin/env python3
"""
测试embedding索引更新功能
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"


def test_add_term_and_search():
    """测试添加术语并搜索"""

    print("🧪 测试embedding索引更新功能")
    print("=" * 50)

    # 1. 检查当前索引状态
    print("\n1. 检查当前索引状态...")
    try:
        response = requests.get(f"{BASE_URL}/term-match/stats")
        if response.status_code == 200:
            stats = response.json()
            if 'index_stats' in stats:
                print(f"✅ 索引状态: {stats['index_stats']}")
            elif 'stats' in stats and 'faiss_stats' in stats['stats']:
                print(f"✅ 索引状态: {stats['stats']['faiss_stats']}")
            else:
                print(f"✅ 索引状态: {stats}")
        else:
            print(f"❌ 获取索引状态失败: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    # 2. 添加新术语
    print("\n2. 添加新术语...")
    new_term = {
        "en": "artificial intelligence",
        "cn": "人工智能",
        "jp": "人工知能"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/users/1/terms",
            json=[new_term],
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 术语添加成功: {result['terms'][0]}")
        else:
            print(f"❌ 术语添加失败: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ 添加术语失败: {e}")
        return

    # 3. 等待索引更新
    print("\n3. 等待索引更新...")
    time.sleep(2)  # 等待异步更新完成

    # 4. 手动触发增量更新
    print("\n4. 手动触发增量更新...")
    try:
        response = requests.post(f"{BASE_URL}/term-match/update-index")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 索引更新结果: {result}")
        else:
            print(f"❌ 索引更新失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 索引更新失败: {e}")

    # 5. 测试搜索新术语
    print("\n5. 测试搜索新术语...")
    try:
        response = requests.post(
            f"{BASE_URL}/term-match/match",
            params={"similarity_threshold": 0.6, "top_k": 5},
            json=["artificial intelligence", "AI", "machine learning"],
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            results = response.json()
            print(f"✅ 搜索成功，找到 {len(results)} 个匹配结果:")
            for i, term in enumerate(results, 1):
                print(f"  {i}. {term['en']} ({term['cn']})")
        else:
            print(f"❌ 搜索失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 搜索失败: {e}")

    # 6. 检查最终索引状态
    print("\n6. 检查最终索引状态...")
    try:
        response = requests.get(f"{BASE_URL}/term-match/stats")
        if response.status_code == 200:
            stats = response.json()
            if 'index_stats' in stats:
                print(f"✅ 最终索引状态: {stats['index_stats']}")
            elif 'stats' in stats and 'faiss_stats' in stats['stats']:
                print(f"✅ 最终索引状态: {stats['stats']['faiss_stats']}")
            else:
                print(f"✅ 最终索引状态: {stats}")
        else:
            print(f"❌ 获取索引状态失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取状态失败: {e}")

    print("\n" + "=" * 50)
    print("🎉 测试完成！")


def test_incremental_update():
    """测试增量更新功能"""

    print("\n🧪 测试增量更新功能")
    print("=" * 50)

    # 1. 检查当前索引
    print("\n1. 检查当前索引...")
    try:
        response = requests.get(f"{BASE_URL}/term-match/stats")
        if response.status_code == 200:
            stats = response.json()
            if 'index_stats' in stats:
                current_count = stats['index_stats']['total_vectors']
            elif 'stats' in stats and 'faiss_stats' in stats['stats']:
                current_count = stats['stats']['faiss_stats']['total_vectors']
            else:
                print(f"❌ 无法获取索引统计信息")
                return
            print(f"✅ 当前索引包含 {current_count} 个向量")
        else:
            print(f"❌ 获取索引状态失败: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    # 2. 触发增量更新
    print("\n2. 触发增量更新...")
    try:
        response = requests.post(f"{BASE_URL}/term-match/update-index")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 增量更新结果: {result}")

            if result['status'] == 'updated':
                print(f"   - 新增术语数: {result['new_terms_count']}")
                print(f"   - 新增术语: {result['new_terms']}")
            elif result['status'] == 'up_to_date':
                print("   - 索引已是最新状态")
        else:
            print(f"❌ 增量更新失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 增量更新失败: {e}")


if __name__ == "__main__":
    # 测试添加术语和搜索
    test_add_term_and_search()

    # 测试增量更新
    test_incremental_update()
