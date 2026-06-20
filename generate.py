"""
每天自动生成 5-10 条认知突破，推送到 PushDeer（手机通知栏）
触发：GitHub Actions 定时（北京时间 8:07）
"""
import os
import json
import requests
from datetime import datetime

DEEPSEEK_KEY = os.environ["DEEPSEEK_API_KEY"]
PUSHDEER_KEY = os.environ["PUSHDEER_KEY"]

SYSTEM_PROMPT = """你是纳瓦尔。你每天给一个22岁年轻人写5-10条"认知突破"——不是鸡汤，不是知识点，是一把手术刀。

每一条必须从以下角度之一切入（轮换使用，不要重复）：
- 反常识真相（公认正确但实际错误）
- 隐藏假设挖掘（你以为做X，底层假设Y是错的）
- 第一性原理重算（从零推导，发现"常识"是错的）
- 二阶效应（人人看到A→B，你看到A→B→C→D，D恰是A的反面）
- 内部→外部视角切换（换个坐标系看同一问题）
- 缺席追问（"为什么没人做X？"揭示隐藏约束）
- 边际vs平均陷阱（人们用平均值思考，决策永远在边际上）
- 可选性/非对称回报
- 历史/生物类比（自然界或历史已有答案）
- 逆向思维（反过来想）

用户背景：AI方向，用纳瓦尔框架+阿德勒心理学指导人生，戒了十年烟，冲雅思8.0，学自媒体。

输出格式——严格JSON数组：
```json
[
  {
    "title": "一句扎穿的话（≤10字）",
    "body": "核心逻辑（3-5句，像纳瓦尔说话。不废话，不鸡汤。）",
    "action": "今天能做的具体一件事（≤30字）",
    "question": "一个可以反问自己的问题（≤25字）"
  }
]
```

绝对禁止：鸡汤、正确的废话、"坚持""努力"类说教、泛泛而谈。每条的body不超过5句话。总共生成6-8条。"""


def call_deepseek():
    """调用 DeepSeek API 生成今日认知突破"""
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"今天是{datetime.now().strftime('%Y年%m月%d日')}。给我今天的认知突破。"},
            ],
            "temperature": 0.9,
            "max_tokens": 4096,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    return raw


def parse_breakthroughs(raw: str) -> list[dict]:
    """解析 DeepSeek 返回的 JSON"""
    # 去掉可能的 markdown 代码块标记
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # 去掉第一行 ```json 和最后一行 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return json.loads(raw)


def format_message(items: list[dict]) -> str:
    """将认知突破格式化为 PushDeer 消息"""
    today = datetime.now().strftime("%m/%d")
    lines = [f"🧠 认知突破 · {today}\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"【{i}. {item['title']}】")
        lines.append(item["body"])
        lines.append(f"▶ {item['action']}")
        lines.append(f"❓ {item['question']}")
        lines.append("")  # 空行
    return "\n".join(lines)


def push_to_phone(text: str):
    """通过 PushDeer 推送到手机通知栏"""
    # 拆分长消息：每条认知突破单独推送，避免消息过长
    resp = requests.post(
        "https://api2.pushdeer.com/message/push",
        data={
            "pushkey": PUSHDEER_KEY,
            "text": text,
            "type": "text",
        },
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise RuntimeError(f"PushDeer error: {result}")
    print(f"PushDeer OK: {result}")


def main():
    try:
        print("Calling DeepSeek...")
        raw = call_deepseek()
        print(f"Raw response ({len(raw)} chars)")

        items = parse_breakthroughs(raw)
        print(f"Parsed {len(items)} breakthroughs")

        msg = format_message(items)
        print(f"Formatted message ({len(msg)} chars)")
        print("---")
        print(msg)
        print("---")

        print("Pushing to PushDeer...")
        push_to_phone(msg)
        print("Done!")

    except Exception as e:
        # 出错也推一条通知
        error_msg = f"❌ 今日认知突破生成失败\n{type(e).__name__}: {e}"
        try:
            push_to_phone(error_msg)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
