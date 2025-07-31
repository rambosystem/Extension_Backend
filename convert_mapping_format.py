#!/usr/bin/env python3
"""
转换FAISS映射文件格式
从旧格式: {term_id: index_position}
到新格式: {'term_id_to_index': {...}, 'index_to_term_id': {...}, 'embedding_dim': 1024}
"""

import pickle
import os


def convert_mapping_format():
    mapping_file = 'faiss_indexes/term_mapping.pkl'

    if not os.path.exists(mapping_file):
        print(f"映射文件不存在: {mapping_file}")
        return

    # 加载旧格式数据
    with open(mapping_file, 'rb') as f:
        old_data = pickle.load(f)

    print(f"旧格式数据: {old_data}")
    print(f"数据类型: {type(old_data)}")

    # 转换为新格式
    if isinstance(old_data, dict) and len(old_data) > 0:
        # 检查是否已经是新格式
        if 'term_id_to_index' in old_data and 'index_to_term_id' in old_data:
            print("已经是新格式，无需转换")
            return

        # 转换为新格式
        term_id_to_index = old_data
        index_to_term_id = {v: k for k, v in old_data.items()}

        new_data = {
            'term_id_to_index': term_id_to_index,
            'index_to_term_id': index_to_term_id,
            'embedding_dim': 1024
        }

        # 备份原文件
        backup_file = mapping_file + '.backup'
        with open(backup_file, 'wb') as f:
            pickle.dump(old_data, f)
        print(f"原文件已备份到: {backup_file}")

        # 保存新格式
        with open(mapping_file, 'wb') as f:
            pickle.dump(new_data, f)

        print(f"转换完成:")
        print(f"  term_id_to_index: {new_data['term_id_to_index']}")
        print(f"  index_to_term_id: {new_data['index_to_term_id']}")
        print(f"  embedding_dim: {new_data['embedding_dim']}")
    else:
        print("无效的映射文件格式")


if __name__ == "__main__":
    convert_mapping_format()
