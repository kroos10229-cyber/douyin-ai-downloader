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
MAX_AGE_DAYS = 30         # 严格限定发布时间：只抓取近 30 天内发布的新视频 (杜绝老旧视频)
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")      # Gemini API Key (可选)


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
        # 保持最新 2000 条历史 ID，防止文件过大
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


# ==================== 4. AI 三维拆解引擎 ====================

def generate_ai_analysis(title, author, likes):
    """针对抖音 AI 热门视频进行三大维度深度拆解"""
    if DEEPSEEK_API_KEY or GEMINI_API_KEY:
        try:
            prompt = f"""你是一名抖音爆款短视频拆解专家。请针对以下【抖音】AI热门视频进行深度拆解：
标题：{title}
创作者：{author}
数据：点赞 {likes}

请严格按以下格式输出（每部分 2 句）：
【视频讲的啥】：核心主题、展示的 AI 工具或玩法。
【借鉴价值】：爆款亮点分析（痛点切入、视觉冲击、手把手教程等）。
【如何去复制】：具体的对标复刻落地方案（文案结构、画面呈现、切入点）。"""

            if DEEPSEEK_API_KEY:
                resp = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
                    timeout=10
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return parse_llm_response(content)
        except Exception:
            pass

    return heuristic_ai_analysis(title, author, likes)

def heuristic_ai_analysis(title, author, likes):
    """内置抖音爆款拆解引擎"""
    summary = "视频围绕当前最热门的 AI 实操应用、工具高阶玩法或突破性进展展开解析。"
    takeaway = "选题极其紧扣用户痛点与好奇心，用惊艳的效果对比或零门槛教程拉高完播与点赞。"
    replication = "1. 对标文案结构：前3秒展示惊艳AI成果；2. 画面对比呈现；3. 评论区引导领同款提示词。"

    if any(k in title for k in ["DeepSeek", "ChatGPT", "Claude", "千问", "Kimi", "GLM", "Gemini", "Grok"]):
        tool = next((k for k in ["DeepSeek", "ChatGPT", "Claude", "千问", "Kimi", "GLM", "Gemini", "Grok"] if k in title), "大模型")
        summary = f"详细讲解了 {tool} 的隐藏高阶玩法、提示词技巧或效率倍增工作流。"
        takeaway = f"抓住了用户对 {tool} 降本增效的刚需，用具体的场景示范（办公、电商、副业）建立权威感。"
        replication = f"选取 {tool} 在垂直领域的具体案例，制作‘手把手教学+提示词模板’型抖音短视频。"
    elif "agent" in title.lower() or "智能体" in title:
        summary = "深度展示了 AI Agent 自动执行复杂任务、多智能体协同或零代码构建专属智能体的过程。"
        takeaway = "展示了从‘AI对话’跨越到‘AI替我自动干活’的未来感，极大激发观者探索欲望。"
        replication = "录制 Agent 自动跑通流程的实操录屏，配上‘取代人工、几分钟搞定’的惊艳标题切入。"

    return {"summary": summary, "takeaway": takeaway, "replication": replication}

def parse_llm_response(text):
    summary, takeaway, replication = "详细解析视频核心主题。", "选题直击痛点，爆款效果显著。", "建议对标文案与视觉二次创作。"
    for line in text.split("\n"):
        if "视频讲的啥" in line: summary = line.split("：")[-1].strip() if "：" in line else line
        elif "借鉴" in line: takeaway = line.split("：")[-1].strip() if "：" in line else line
        elif "复制" in line or "复刻" in line: replication = line.split("：")[-1].strip() if "：" in line else line
    return {"summary": summary, "takeaway": takeaway, "replication": replication}


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
    max_age_seconds = MAX_AGE_DAYS * 86400  # 30 天秒数

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
                    
                    # 1. 历史去重：跳过往期已推送过的视频
                    if aweme_id in history_set or aweme_id in seen_in_run:
                        continue

                    # 2. 发布时间过滤：必须在 30 天内发布
                    create_time = aweme.get("create_time", 0)
                    if create_time > 0 and (now_ts - create_time > max_age_seconds):
                        print(f"[-] 跳过超过30天的老视频 (ID: {aweme_id})")
                        continue

                    desc = aweme.get("desc", "抖音AI热门视频")
                    author = aweme.get("author", {}).get("nickname", "抖音创作者")
                    stats = aweme.get("statistics", {})
                    digg_count = stats.get("digg_count", 0)
                    collect_count = stats.get("collect_count", 0)
                    comment_count = stats.get("comment_count", 0)

                    # 无水印视频播放地址
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

    # 优先筛选点赞 >= 3000 的高质量热门新视频
    filtered_videos = [v for v in captured_videos if v["likes"] >= MIN_LIKES]
    filtered_videos.sort(key=lambda x: (x["likes"] + x["collects"] * 2), reverse=True)

    if len(filtered_videos) < TARGET_MIN_VIDEOS and captured_videos:
        all_sorted = sorted(captured_videos, key=lambda x: (x["likes"] + x["collects"] * 2), reverse=True)
        final_videos = all_sorted[:TARGET_MAX_VIDEOS]
    else:
        final_videos = filtered_videos[:TARGET_MAX_VIDEOS]

    print(f"\n[+] 筛选完成！已精选出 {len(final_videos)} 个【近 30 天内最新】热门抖音 AI 视频 (已去除历史重复)。")

    if not final_videos:
        print("[-] 提示: 未搜集到符合条件的最新抖音视频，可能 Cookie 需更新。")
        return []

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(DOWNLOAD_DIR, date_str)
    os.makedirs(today_dir, exist_ok=True)

    # 生成 AI 三维拆解与写入历史库
    for idx, item in enumerate(final_videos, 1):
        print(f"[{idx}/{len(final_videos)}] [抖音] {item['title'][:30]} | 📅 {item['pub_date']} | ❤️ 点赞: {format_number(item['likes'])}")
        item["analysis"] = generate_ai_analysis(item["title"], item["author"], item["likes"])
        history_set.add(item["id"])

    save_reports(today_dir, final_videos, date_str)
    send_mobile_notifications(final_videos, date_str)
    save_history_ids(history_set)

    return final_videos


# ==================== 6. 报告导出与手机端微信推送 ====================

def save_reports(today_dir, videos, date_str):
    """保存本地 Markdown 报告与 JSON 数据"""
    json_path = os.path.join(today_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(today_dir, "daily_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🎵 抖音 AI 最新热门爆款总结日报 ({date_str})\n\n")
        f.write(f"> 规则：近 30 天内最新发布 | 精选 {len(videos)} 个爆款 | 历史自动去重无重复\n\n")
        
        for idx, v in enumerate(videos, 1):
            ana = v.get("analysis", {})
            f.write(f"### {idx}. [抖音] {v['title']}\n")
            f.write(f"- **创作者**: {v['author']} | 📅 **发布时间**: {v['pub_date']} | ❤️ **点赞**: {format_number(v['likes'])} | ⭐ **收藏**: {format_number(v['collects'])}\n")
            f.write(f"- 🔗 **抖音原视频直达**: [{v['share_url']}]({v['share_url']})\n")
            f.write(f"- 📌 **视频讲的啥**: {ana.get('summary')}\n")
            f.write(f"- 💡 **对我借鉴**: {ana.get('takeaway')}\n")
            f.write(f"- 🚀 **如何去复制**: {ana.get('replication')}\n\n")
            f.write("---\n\n")

def send_mobile_notifications(videos, date_str):
    """发送【全新 抖音 AI 爆款拆解总结】至手机微信"""
    print("\n[+] 正在将 抖音 AI 爆款拆解报告推送到手机微信...")

    title = f"🎵 抖音 AI 最新爆款拆解日报 ({date_str})"
    
    content_lines = [
        f"# 🎵 抖音 AI 最新爆款拆解日报 ({date_str})",
        f"已为你精选今日 **{len(videos)} 个全新抖音 AI 爆款**（限定近 30 天最新发布、历史不重样）：\n"
    ]

    for idx, v in enumerate(videos, 1):
        ana = v.get("analysis", {})
        content_lines.append(f"### {idx}. [抖音] {v['title'][:32]}")
        content_lines.append(f"👤 **{v['author']}** | 📅 {v['pub_date']} | ❤️ 点赞 {format_number(v['likes'])}")
        content_lines.append(f"📌 **视频讲的啥**: {ana.get('summary')}")
        content_lines.append(f"💡 **借鉴价值**: {ana.get('takeaway')}")
        content_lines.append(f"🚀 **如何去复制**: {ana.get('replication')}")
        content_lines.append(f"🔗 [点击在抖音打开观看]({v['share_url']})\n")

    full_markdown = "\n".join(content_lines)

    if PUSHPLUS_TOKEN:
        try:
            url = "http://www.pushplus.plus/send"
            payload = {"token": PUSHPLUS_TOKEN, "title": title, "content": full_markdown, "template": "markdown"}
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200 and res.json().get("code") == 200:
                print("[✔] 成功将全新 抖音 AI 爆款拆解报告推送到微信 (PushPlus)！")
        except Exception as e:
            print(f"[-] PushPlus 推送失败: {e}")

    if SERVERCHAN_KEY:
        try:
            url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
            payload = {"title": title, "desp": full_markdown}
            requests.post(url, data=payload, timeout=10)
            print("[✔] 成功发送至 Server酱！")
        except Exception as e:
            pass

if __name__ == "__main__":
    fetch_douyin_ai_videos()
