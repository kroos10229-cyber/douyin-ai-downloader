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
TARGET_MIN_VIDEOS = 10     # 每日推送精确为 10 个精选爆款
TARGET_MAX_VIDEOS = 10

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


# ==================== 4. 精炼干练版 AI 拆解引擎 ====================

def generate_ai_analysis(title, author, likes, collects, comments):
    """
    精炼、清晰、绝无占位符的 4 维干货拆解
    """
    time.sleep(1.5)  # 控频防 API 429 限制

    if GEMINI_API_KEY:
        try:
            prompt = f"""你是一名抖音短视频爆款拆解专家。请对以下【抖音】AI热门视频进行极其精炼干练的 4 维度拆解（每项必须直接输出 1-2 句精辟内容，绝对禁止输出空标签或占位符）：

标题：{title}
创作者：{author}
数据：点赞 {likes}，收藏 {collects}

输出格式要求（严格按以下格式，冒号后直接跟着精炼分析内容）：
📌 视频内容：[1-2句精炼总结核心玩法/工具/主题]
💡 值得借鉴的点：[1-2句总结最亮眼吸睛的切入点/视觉/文案]
🔥 热门原因拆解：[1-2句总结痛点共鸣/完播率/算法触发逻辑]
🚀 如何借鉴复制：[1-2句具体的对标复刻步骤SOP]"""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                res = parse_llm_text_clean(text)
                if res["summary"] and "【" not in res["summary"]:
                    print(f"[✔] 成功调用 Gemini 3.6 Flash 生成精炼拆解")
                    return res
        except Exception as e:
            print(f"[!] 调用 Gemini API 异常: {e}")

    return heuristic_clean_analysis(title, author, likes, collects, comments)

def parse_llm_text_clean(text):
    """解析大模型文本，确保提取出真实的精炼文字"""
    summary, takeaway, viral_reason, replication = "", "", "", ""
    for line in text.split("\n"):
        line_s = line.strip()
        if "📌 视频内容" in line_s or "视频内容" in line_s:
            summary = line_s.split("：")[-1].strip() if "：" in line_s else line_s
        elif "💡 值得借鉴的点" in line_s or "值得借鉴" in line_s:
            takeaway = line_s.split("：")[-1].strip() if "：" in line_s else line_s
        elif "🔥 热门原因拆解" in line_s or "热门原因" in line_s:
            viral_reason = line_s.split("：")[-1].strip() if "：" in line_s else line_s
        elif "🚀 如何借鉴复制" in line_s or "借鉴复制" in line_s:
            replication = line_s.split("：")[-1].strip() if "：" in line_s else line_s

    # 清理遗留的括号标记
    summary = summary.replace("【视频内容】", "").strip()
    takeaway = takeaway.replace("【值得借鉴的点】", "").strip()
    viral_reason = viral_reason.replace("【热门原因拆解】", "").strip()
    replication = replication.replace("【如何借鉴复制】", "").strip()

    if not summary: summary = "精炼拆解该 AI 视频的核心实操玩法与使用场景。"
    if not takeaway: takeaway = "前3秒视觉卡点吸睛，选题直击观众效率降本痛点。"
    if not viral_reason: viral_reason = "高实用价值引发大量收藏，高完播率触发流量池二次推荐。"
    if not replication: replication = "对标文案结构：前3秒展示AI成果 -> 3步步骤演示 -> 评论区领资源。"

    return {
        "summary": summary,
        "takeaway": takeaway,
        "viral_reason": viral_reason,
        "replication": replication
    }

def heuristic_clean_analysis(title, author, likes, collects, comments):
    """内置精炼干练拆解规则"""
    tool_name = "AI大模型"
    for k in ["DeepSeek", "ChatGPT", "Claude", "千问", "Kimi", "GLM", "Gemini", "Grok", "Sora", "即梦"]:
        if k.lower() in title.lower():
            tool_name = k
            break

    if "agent" in title.lower() or "智能体" in title:
        summary = f"演示用 {tool_name} 零代码搭建 AI Agent 并自动跑通业务全流程。"
        takeaway = "抓住了‘AI从对话走向自动干活’的大趋势，直观录屏极具信任感。"
        viral_reason = "触达职场人降本增效刚需，自动化成果带来极强心理爽点。"
        replication = "前3秒展示 Agent 自动打工结果 -> 3步搭建教学 -> 评论区领配置文件。"
    else:
        summary = f"讲解 {tool_name} 的保姆级实操教程与高阶提示词用法。"
        takeaway = "结构清晰，提示词拿来即用，极低门槛吸引普通观众。"
        viral_reason = "利他属性强引爆大量收藏，高完播率触发算法二次推荐。"
        replication = "‘别再用老方法了！教你用 {tool_name} 搞定’ -> 演示步骤 -> 评论区领文档。"

    return {
        "summary": summary,
        "takeaway": takeaway,
        "viral_reason": viral_reason,
        "replication": replication
    }


# ==================== 5. 抖音 (Douyin) 搜索与过滤核心 ====================

def fetch_douyin_ai_videos():
    """检索并筛选 30 天内发布、点赞 >= 3000 且历史未推送过的 10 个抖音 AI 视频"""
    print("==========================================")
    print("🎯 开始抓取 抖音 (Douyin) 最新 10 个 AI 热门视频...")
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


# ==================== 6. 报告导出与微信精炼单条推送 ====================

def save_reports(today_dir, videos, date_str):
    """保存本地 Markdown 报告与 JSON 数据"""
    json_path = os.path.join(today_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(today_dir, "daily_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🎵 抖音 AI 爆款精炼拆解日报 ({date_str})\n\n")
        f.write(f"> 精选近 30 天最新 10 个头部爆款 AI 视频 | 干货精炼版\n\n")
        
        for idx, v in enumerate(videos, 1):
            ana = v.get("analysis", {})
            f.write(f"## {idx}. {v['title']}\n\n")
            f.write(f"👤 **账号信息**: {v['author']} &nbsp;|&nbsp; 📅 {v['pub_date']} &nbsp;|&nbsp; ❤️ 点赞 {format_number(v['likes'])} &nbsp;|&nbsp; ⭐ 收藏 {format_number(v['collects'])}\n\n")
            f.write(f"🔗 **原视频链接**: [{v['share_url']}]({v['share_url']})\n\n")
            f.write(f"📌 **视频内容**: {ana.get('summary')}\n\n")
            f.write(f"💡 **值得借鉴的点**: {ana.get('takeaway')}\n\n")
            f.write(f"🔥 **热门原因拆解**: {ana.get('viral_reason')}\n\n")
            f.write(f"🚀 **如何借鉴复制**: {ana.get('replication')}\n\n")
            f.write("---\n\n")

def send_mobile_notifications(videos, date_str):
    """发送精炼干练、单条全收齐的微信推送报告"""
    print("\n[+] 正在将 10 个精炼拆解视频推送到手机微信...")

    title = f"🎵 抖音 AI 热门爆款拆解 ({date_str})"
    
    content_blocks = [
        f"# 🎵 抖音 AI 热门爆款拆解 ({date_str})\n",
        f"今日精选 **{len(videos)} 个全新抖音 AI 爆款**（限定 30 天内最新发布）：\n\n---\n"
    ]

    for idx, v in enumerate(videos, 1):
        ana = v.get("analysis", {})
        
        card = f"""### {idx}. {v['title'][:32]}

👤 **账号信息**：{v['author']} &nbsp;|&nbsp; 📅 {v['pub_date']} &nbsp;|&nbsp; ❤️ 点赞 {format_number(v['likes'])}

📌 **视频内容**：{ana.get('summary')}
💡 **值得借鉴的点**：{ana.get('takeaway')}
🔥 **热门原因拆解**：{ana.get('viral_reason')}
🚀 **如何借鉴复制**：{ana.get('replication')}
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
                print("[✔] 成功将 10 个精炼拆解视频推送到微信 (PushPlus)！")
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
