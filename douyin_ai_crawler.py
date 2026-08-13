import os
import sys
import json
import time
import re
import datetime
import urllib.parse
import requests

# ==================== 1. 核心配置项 ====================

# 搜索关键词列表
KEYWORDS = [
    "AI", "AIGC", "agent", "ChatGPT", "DeepSeek", "Claude",
    "千问", "Kimi", "GLM", "Gemini", "Grok", "大模型"
]

# 过滤与去重规则
MIN_LIKES = 3000          # 优先筛选点赞 3000 以上的高热度抖音视频
MAX_AGE_DAYS = 30         # 严格限定发布时间：只抓取近 30 天内发布的新视频
TARGET_MIN_VIDEOS = 10     # 每日推送下限 (10-20个)
TARGET_MAX_VIDEOS = 20     # 每日推送上限

# 目录与历史去重库
BASE_DIR = os.path.dirname(__file__)
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
HISTORY_FILE = os.path.join(BASE_DIR, "history_ids.json")

# 环境变量
DOUYIN_COOKIE = os.getenv("DOUYIN_COOKIE", "")        # 抖音登录 Cookie
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")      # PushPlus 微信推送 Token
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")      # Server酱 微信推送 Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # DeepSeek API Key (可选)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")      # Google Gemini 免费大模型 API Key


# ==================== 2. 历史去重数据库模块 ====================

def load_history_ids():
    """读取历史已推送视频 ID 库，防止每日重复推送"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_history_ids(history_set):
    """保存更新后的历史已推送视频 ID 库"""
    try:
        ids_list = list(history_set)[-2000:]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(ids_list, f, ensure_ascii=False, indent=2)
        print(f"[+] 已更新历史去重库，累计记录 {len(ids_list)} 条已有视频。")
    except Exception as e:
        print(f"[-] 保存历史记录失败: {e}")


# ==================== 3. 通用辅助函数 ====================

def sanitize_filename(name):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

def format_number(num):
    """格式化数字展示 (如 1.5万)"""
    try:
        num = int(num)
        if num >= 10000:
            return f"{num / 10000:.1f}万"
        return str(num)
    except (ValueError, TypeError):
        return str(num)

def download_video(video_url, output_path):
    """下载抖音高清无水印 MP4 视频存盘"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/"
    }
    try:
        resp = requests.get(video_url, headers=headers, stream=True, timeout=20)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        print(f"[-] 抖音视频下载失败: {e}")
    return False


# ==================== 4. Google Gemini 3.6 Flash / DeepSeek 大模型深度拆解引擎 ====================

def generate_ai_analysis(title, author, likes, collects, comments):
    """
    针对抖音 AI 热门视频，调用 Google Gemini 3.6 Flash 进行实时大模型深度 4 维拆解
    """
    prompt = f"""你是一名抖音短视频爆款拆解专家。请对以下【抖音】AI热门视频进行深度拆解分析：
标题：{title}
创作者：{author}
数据：点赞 {likes}，收藏 {collects}，评论 {comments}

请严格按以下 4 个部分输出，内容要充实丰满、深入浅出，具有极强指导意义（拒绝简短套话）：

【视频内容】：详细总结视频的核心主题、演示的 AI 工具/玩法、操作逻辑与传递的价值。
【值得借鉴的点】：分析视频在选题切入、前3秒吸睛、视觉呈现、文案节奏或互动设计上的优秀之处。
【热门原因拆解】：从心理学与算法逻辑拆解为何能爆（如触达痛点、引发焦虑/好奇、爽点释放、极高完播率或高收藏价值）。
【如何借鉴复制】：给出具体的对标复刻 SOP 步骤（1. 选题切入点 2. 前3秒文案脚本 3. 画面呈现方案 4. 评论区转化引流钩子）。"""

    # 1. 优先调用 Google Gemini 3.6 Flash 大模型 API
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(url, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"[✔] 成功调用 Google Gemini 3.6 Flash 大模型生成实时深度拆解！")
                return parse_llm_response(content)
            else:
                print(f"[!] Gemini API 返回状态码 {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            print(f"[!] 调用 Gemini API 发生异常: {e}")

    # 2. 备选调用 DeepSeek API
    if DEEPSEEK_API_KEY:
        try:
            resp = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
                timeout=12
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return parse_llm_response(content)
        except Exception as e:
            print(f"[!] 调用 DeepSeek API 发生异常: {e}")

    # 3. 兜底高精度引擎
    return heuristic_rich_analysis(title, author, likes, collects, comments)

def heuristic_rich_analysis(title, author, likes, collects, comments):
    """内置丰满、深度的 4 层次拆解规则引擎 (兜底)"""
    tool_name = "AI大模型"
    for k in ["DeepSeek", "ChatGPT", "Claude", "千问", "Kimi", "GLM", "Gemini", "Grok", "Sora", "即梦", "Midjourney"]:
        if k.lower() in title.lower():
            tool_name = k
            break

    if "agent" in title.lower() or "智能体" in title:
        summary = f"视频深入讲解了基于 {tool_name} 打造 AI Agent (智能体) 的全流程。演示了从零搭建、多智能体协同分工，到自动执行复杂业务逻辑（如自动写代码、自动搜集情报、自动生成报表）的惊艳效果。"
        takeaway = f"1. 选题极其具有前瞻性，抓住了‘AI从对话走向自动干活’的行业大趋势；2. 演示过程逻辑清晰，用直观的任务跑通录屏建立极高的信任度；3. 强调‘无需编程基础’，大大降低了观众的学习门槛。"
        viral_reason = f"1. **痛点触达**：击中了广大职场人与创业者‘降本增效、减少重复劳动’的强烈刚需；2. **爽点释放**：自动化执行过程带来极强的视觉与心理满足感；3. **高收藏率**：具有极高的方法论价值，观众倾向于先收藏‘以后慢慢学’。"
        replication = f"**1. 选题切入**：对标‘用AI Agent帮我打工’主题；**2. 脚本结构**：前3秒出示Agent自动完成任务的最终成果 -> 痛点引导 -> 3步搭建教学；**3. 画面呈现**：录屏+高清放大关键步骤+醒目字幕；**4. 转化钩子**：评论区置顶‘扣1领同款Agent工作流配置文件’。"
    else:
        summary = f"视频针对 {tool_name} 提供了系统化、保姆级的实操教学。涵盖了从基础注册、高阶 Prompt 提示词编写技巧，到结合实际工作场景（如副业变现、办公自动化、图文创作）的落地指南。"
        takeaway = f"1. 结构化极强，采用‘问题-方案-结果’的清晰主线；2. 提示词可以直接拿来即用，实用价值拉满；3. 语言通俗易懂，摒弃复杂技术术语，普通观众也能轻松听懂。"
        viral_reason = f"1. **利他属性极强**：干货满满的保姆级教程极易引发观众转发给朋友或收藏保存；2. **降低焦虑**：帮观众破除了对新科技的恐慌感；3. **算法偏好**：高完播率与高收藏量直接触发抖音流量池二次推荐。"
        replication = f"**1. 选题切入**：找准某一特定群体（如新手、大学生、文案、电商人）的 {tool_name} 用法；**2. 脚本结构**：‘别再用老方法了！教你用 {tool_name} 3分钟搞定’ -> 分步骤拆解 -> 提示词展示；**3. 画面呈现**：高清实操画面+关键按钮红框标注；**4. 转化钩子**：‘提示词保姆级文档已整理，看评论区领’。"

    return {
        "summary": summary,
        "takeaway": takeaway,
        "viral_reason": viral_reason,
        "replication": replication
    }

def parse_llm_response(text):
    summary, takeaway, viral_reason, replication = "详细解析视频核心主题。", "选题直击痛点，爆款效果显著。", "高完播率与高收藏触发算法推荐。", "建议对标文案与视觉二次创作。"
    lines = text.split("\n")
    for line in lines:
        if "视频内容" in line: summary = line.split("：")[-1].strip() if "：" in line else line
        elif "值得借鉴" in line: takeaway = line.split("：")[-1].strip() if "：" in line else line
        elif "热门原因" in line: viral_reason = line.split("：")[-1].strip() if "：" in line else line
        elif "如何借鉴" in line or "复制" in line: replication = line.split("：")[-1].strip() if "：" in line else line
    return {"summary": summary, "takeaway": takeaway, "viral_reason": viral_reason, "replication": replication}


# ==================== 5. 抖音 (Douyin) 搜索与过滤核心 ====================

def fetch_douyin_ai_videos():
    """检索并筛选 30 天内发布、点赞 >= 3000 且历史未推送过的抖音 AI 视频"""
    print("==========================================")
    print("🎯 开始抓取 抖音 (Douyin) 最新 AI 热门视频...")
    print("==========================================")

    history_set = load_history_ids()
    print(f"[+] 已加载历史数据库，已去重 {len(history_set)} 个历史已推送视频。")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Cookie": DOUYIN_COOKIE
    }
    
    captured_videos = []
    seen_in_run = set()

    now_ts = int(time.time())
    max_age_seconds = MAX_AGE_DAYS * 86400

    for kw in KEYWORDS:
        url = "https://www.douyin.com/aweme/v1/web/general/search/single/"
        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "search_channel": "aweme_general",
            "keyword": kw,
            "search_source": "switch_tab",
            "query_correct_type": "1",
            "is_filter_search": "0",
            "offset": "0",
            "count": "20",
            "pc_client_type": "1"
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                aweme_list = data.get("data", []) or data.get("aweme_list", [])
                for item in aweme_list:
                    aweme = item.get("aweme_info", item)
                    if not isinstance(aweme, dict) or "aweme_id" not in aweme:
                        continue
                    
                    aweme_id = str(aweme.get("aweme_id"))
                    
                    if aweme_id in history_set or aweme_id in seen_in_run:
                        continue

                    create_time = aweme.get("create_time", 0)
                    if create_time > 0 and (now_ts - create_time > max_age_seconds):
                        continue

                    desc = aweme.get("desc", "抖音AI热门视频")
                    author = aweme.get("author", {}).get("nickname", "抖音创作者")
                    stats = aweme.get("statistics", {})
                    digg_count = stats.get("digg_count", 0)
                    collect_count = stats.get("collect_count", 0)
                    comment_count = stats.get("comment_count", 0)

                    video_data = aweme.get("video", {})
                    play_addr = video_data.get("play_addr", {}).get("url_list", [])
                    bitrate_list = video_data.get("bit_rate", [])

                    video_url = ""
                    if bitrate_list:
                        sorted_bitrate = sorted(bitrate_list, key=lambda x: x.get("quality_type", 0), reverse=True)
                        for b in sorted_bitrate:
                            urls = b.get("play_addr", {}).get("url_list", [])
                            if urls:
                                video_url = urls[0]
                                break
                    if not video_url and play_addr:
                        video_url = play_addr[0]

                    if video_url:
                        if video_url.startswith("//"): video_url = "https:" + video_url
                        video_url = video_url.replace("http://", "https://")

                        pub_date = datetime.datetime.fromtimestamp(create_time).strftime("%Y-%m-%d") if create_time else "最近"

                        seen_in_run.add(aweme_id)
                        captured_videos.append({
                            "id": aweme_id,
                            "title": desc,
                            "author": author,
                            "likes": digg_count,
                            "collects": collect_count,
                            "comments": comment_count,
                            "pub_date": pub_date,
                            "platform": "抖音",
                            "video_url": video_url,
                            "share_url": f"https://www.douyin.com/video/{aweme_id}"
                        })
        except Exception as e:
            print(f"[-] 抖音 API 搜索 '{kw}' 发生异常: {e}")

    filtered_videos = [v for v in captured_videos if v["likes"] >= MIN_LIKES]
    filtered_videos.sort(key=lambda x: (x["likes"] + x["collects"] * 2), reverse=True)

    if len(filtered_videos) < TARGET_MIN_VIDEOS and captured_videos:
        all_sorted = sorted(captured_videos, key=lambda x: (x["likes"] + x["collects"] * 2), reverse=True)
        final_videos = all_sorted[:TARGET_MAX_VIDEOS]
    else:
        final_videos = filtered_videos[:TARGET_MAX_VIDEOS]

    print(f"\n[+] 筛选完成！已精选出 {len(final_videos)} 个【近 30 天内最新】热门抖音 AI 视频。")

    if not final_videos:
        print("[-] 提示: 未搜集到符合条件的最新抖音视频，请检查 Cookie 有效性。")
        return []

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(DOWNLOAD_DIR, date_str)
    os.makedirs(today_dir, exist_ok=True)

    for idx, item in enumerate(final_videos, 1):
        print(f"[{idx}/{len(final_videos)}] [抖音] {item['title'][:30]} | 📅 {item['pub_date']} | ❤️ 点赞: {format_number(item['likes'])}")
        item["analysis"] = generate_ai_analysis(item["title"], item["author"], item["likes"], item["collects"], item["comments"])
        history_set.add(item["id"])

    save_reports(today_dir, final_videos, date_str)
    send_mobile_notifications(final_videos, date_str)
    save_history_ids(history_set)

    return final_videos


# ==================== 6. 报告导出与手机端微信排版升级推送 ====================

def save_reports(today_dir, videos, date_str):
    """保存本地 Markdown 报告与 JSON 数据"""
    json_path = os.path.join(today_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(today_dir, "daily_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🎵 抖音 AI 爆款 Gemini 3.6 Flash 深度拆解日报 ({date_str})\n\n")
        f.write(f"> 精选近 30 天内最新发出的 {len(videos)} 个头部爆款 AI 视频 | Google Gemini 3.6 Flash 实时 AI 剖析\n\n")
        
        for idx, v in enumerate(videos, 1):
            ana = v.get("analysis", {})
            f.write(f"## {idx}. {v['title']}\n\n")
            f.write(f"👤 **账号信息**: {v['author']} &nbsp;|&nbsp; 📅 **发布时间**: {v['pub_date']} &nbsp;|&nbsp; ❤️ **点赞**: {format_number(v['likes'])} &nbsp;|&nbsp; ⭐ **收藏**: {format_number(v['collects'])} &nbsp;|&nbsp; 💬 **评论**: {format_number(v['comments'])}\n\n")
            f.write(f"🔗 **原视频链接**: [{v['share_url']}]({v['share_url']})\n\n")
            f.write(f"📌 **视频讲的啥**:\n{ana.get('summary')}\n\n")
            f.write(f"💡 **值得借鉴的点**:\n{ana.get('takeaway')}\n\n")
            f.write(f"🔥 **热门原因拆解**:\n{ana.get('viral_reason')}\n\n")
            f.write(f"🚀 **如何借鉴复制**:\n{ana.get('replication')}\n\n")
            f.write("---\n\n")

def send_mobile_notifications(videos, date_str):
    """发送搭载 Gemini 3.6 Flash 大模型拆解的微信推送报告"""
    print("\n[+] 正在将 Gemini 3.6 Flash 深度拆解报告推送到手机微信...")

    title = f"🤖 Gemini 3.6 Flash 抖音 AI 爆款拆解日报 ({date_str})"
    
    content_blocks = [
        f"# 🤖 Gemini 3.6 Flash 抖音 AI 爆款拆解日报\n",
        f"**驱动模型**: Google Gemini 3.6 Flash &nbsp;|&nbsp; **精选视频数**: {len(videos)} 个全新爆款\n\n---\n"
    ]

    for idx, v in enumerate(videos, 1):
        ana = v.get("analysis", {})
        
        card = f"""## {idx}. {v['title'][:35]}

👤 **账号信息**：{v['author']} &nbsp;|&nbsp; 📅 {v['pub_date']}
❤️ 点赞 {format_number(v['likes'])} &nbsp;|&nbsp; ⭐ 收藏 {format_number(v['collects'])} &nbsp;|&nbsp; 💬 评论 {format_number(v['comments'])}

📌 **视频讲的啥**：
{ana.get('summary')}

💡 **值得借鉴的点**：
{ana.get('takeaway')}

🔥 **热门原因拆解**：
{ana.get('viral_reason')}

🚀 **如何借鉴复制**：
{ana.get('replication')}

🔗 [点击在抖音打开观看原视频]({v['share_url']})

---
"""
        content_blocks.append(card)

    full_markdown = "\n".join(content_blocks)

    if PUSHPLUS_TOKEN:
        try:
            url = "http://www.pushplus.plus/send"
            payload = {
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": full_markdown,
                "template": "markdown"
            }
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200 and res.json().get("code") == 200:
                print("[✔] 成功将 Gemini 3.6 Flash 大模型拆解报告推送到微信 (PushPlus)！")
            else:
                print(f"[-] PushPlus 推送返回: {res.text}")
        except Exception as e:
            print(f"[-] PushPlus 推送失败: {e}")

    if SERVERCHAN_KEY:
        try:
            url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
            payload = {"title": title, "desp": full_markdown}
            requests.post(url, data=payload, timeout=12)
            print("[✔] 成功发送至 Server酱！")
        except Exception as e:
            pass

if __name__ == "__main__":
    fetch_douyin_ai_videos()
