"""
调试发送给 API 的消息格式
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.config import _load_env_file
from pg_semantic_operators.client import _split_prompt

_load_env_file()

# 模拟 ai_filter 的 prompt
system_prompt = """你是一个智能过滤器。根据用户提供的过滤条件，判断每一行数据是否符合条件。

规则：
1. 只返回 "true" 或 "false"，不要其他任何内容
2. 严格根据语义判断
3. 如果条件模糊，倾向于返回 "false"
4. 数值比较要精确（如"大于100"表示 > 100，不包括100本身）
5. 仔细执行数值比较，不要只看示例中的数字模式

示例：
条件: "金额大于1000"
数据: {"金额": 500, "状态": "已完成"}
输出: false

条件: "金额大于1000"
数据: {"金额": 1500, "状态": "已完成"}
输出: true

条件: "金额大于1000"
数据: {"金额": 1000, "状态": "已完成"}
输出: false

条件: "状态是已完成"
数据: {"状态": "已完成", "金额": 2000}
输出: true

条件: "状态是已完成"
数据: {"状态": "进行中", "金额": 2000}
输出: false

现在请判断："""

condition = "金额大于1000"
row_data = {"金额": 1500}

user_prompt = f"""条件: {condition}
数据: {json.dumps(row_data, ensure_ascii=False)}"""

full_prompt = f"{system_prompt}\n\n{user_prompt}"

print("=" * 80)
print("原始 prompt:")
print("=" * 80)
print(full_prompt)
print("\n" + "=" * 80)
print("分割后的 messages:")
print("=" * 80)

messages = _split_prompt(full_prompt)
for i, msg in enumerate(messages):
    print(f"\n消息 {i+1} (role: {msg['role']}):")
    print("-" * 40)
    content = msg['content']
    if len(content) > 200:
        print(content[:200] + "...")
    else:
        print(content)
