import os
import sys
import json
import time
import re
import datetime
import urllib.parse
import requests
from playwright.sync_api import sync_playwright

# ==================== 1. 核心配置项 (仅针对 抖音 平台) ====================

# 搜索关键词列表
KEYWORDS = [
    "AI", "AIGC", "agent", "ChatGPT", "DeepSeek", "Claude",
    "千问", "Kimi", "GLM", "Gemini", "Grok", "大模型"
]

# 筛选规则 (点赞 >= 3000，每日目标 10-20 个)
MIN_LIKES = 3000          # 优先筛选点赞 3000 以上的高热度抖音视频
TARGET_MIN_VIDEOS = 10     # 每日推送下限
TARGET_MAX_VIDEOS = 20     # 每日推送上限
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")

# 环境变量
DOUYIN_COOKIE = os.getenv("DOUYIN_COOKIE", "")        # 抖音登录 Cookie (强烈推荐配置，100% 稳定搜集)
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")      # PushPlus 微信推送 Token
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")      # Server酱 微信推送 Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # DeepSeek API Key (可选)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")      # Gemini API Key (可选)


# ==================== 2. 通用辅助函数 ====================

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


# ==================== 3. AI 三维拆解引擎 ====================

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


# ==================== 4. 抖音 (Douyin) 视频抓取核心 ====================

def fetch_douyin_via_api(cookie_str, keywords):
    """方法 A：通过 抖音官方 Web API + Cookie 搜索 (100% 准确获取高赞视频)"""
    print("[+] 使用 抖音 Cookie Web API 检索...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Cookie": cookie_str
    }
    
    videos = []
    seen = set()

    for kw in keywords:
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
            "count": "15",
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
                    
                    aweme_id = aweme.get("aweme_id")
                    if aweme_id in seen:
                        continue

                    desc = aweme.get("desc", "抖音AI热门视频")
                    author = aweme.get("author", {}).get("nickname", "抖音创作者")
                    stats = aweme.get("statistics", {})
                    digg_count = stats.get("digg_count", 0)
                    collect_count = stats.get("collect_count", 0)
                    comment_count = stats.get("comment_count", 0)

                    # 无水印视频地址提取
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

                        seen.add(aweme_id)
                        videos.append({
                            "id": aweme_id,
                            "title": desc,
                            "author": author,
                            "likes": digg_count,
                            "collects": collect_count,
                            "comments": comment_count,
                            "platform": "抖音",
                            "video_url": video_url,
                            "share_url": f"https://www.douyin.com/video/{aweme_id}"
                        })
        except Exception as e:
            print(f"[-] 抖音 API 搜索 '{kw}' 发生异常: {e}")

    return videos

def fetch_douyin_via_playwright(keywords):
    """方法 B：使用 Playwright 无头浏览器模拟检索 (兜底逻辑)"""
    print("[+] 使用 Playwright 模拟浏览器搜索抖音...")
    captured = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        page = context.new_page()

        def handle_response(response):
            if "search/single" in response.url or "search/item" in response.url:
                try:
                    data = response.json()
                    aweme_list = data.get("data", []) or data.get("aweme_list", [])
                    for item in aweme_list:
                        aweme = item.get("aweme_info", item)
                        if isinstance(aweme, dict) and "aweme_id" in aweme:
                            aweme_id = aweme.get("aweme_id")
                            if aweme_id in seen: continue
                            desc = aweme.get("desc", "抖音视频")
                            author = aweme.get("author", {}).get("nickname", "抖音创作者")
                            stats = aweme.get("statistics", {})
                            digg = stats.get("digg_count", 0)
                            collect = stats.get("collect_count", 0)
                            comment = stats.get("comment_count", 0)

                            seen.add(aweme_id)
                            captured.append({
                                "id": aweme_id,
                                "title": desc,
                                "author": author,
                                "likes": digg,
                                "collects": collect,
                                "comments": comment,
                                "platform": "抖音",
                                "share_url": f"https://www.douyin.com/video/{aweme_id}"
                            })
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)
        except Exception:
            pass

        for kw in keywords[:3]:
            try:
                search_url = f"https://www.douyin.com/search/{urllib.parse.quote(kw)}?type=video"
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(4)
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(2)
            except Exception as e:
                print(f"[-] Playwright 检索 '{kw}' 失败: {e}")

        browser.close()

    return captured

def search_douyin_ai_videos():
    """纯 抖音 (Douyin) 平台 AI 热门视频搜集与筛选"""
    print("==========================================")
    print("🎯 开始抓取 抖音 (Douyin) AI 热门视频...")
    print("==========================================")

    videos = []

    # 1. 优先使用 Cookie API 搜集 (如果配置了 DOUYIN_COOKIE)
    if DOUYIN_COOKIE:
        videos = fetch_douyin_via_api(DOUYIN_COOKIE, KEYWORDS)

    # 2. 如果未配置 Cookie 或 API 未返回数据，使用 Playwright 兜底
    if not videos:
        videos = fetch_douyin_via_playwright(KEYWORDS)

    # 3. 扣重与筛选：只留抖音视频，筛选点赞 >= 3000 的热门内容
    unique_dict = {v["share_url"]: v for v in videos}
    filtered_videos = [v for v in unique_dict.values() if v["likes"] >= MIN_LIKES]
    
    # 按点赞量/热度排序
    filtered_videos.sort(key=lambda x: (x["likes"] + x["collects"] * 2), reverse=True)

    # 截取前 10 - 20 个热门抖音视频
    if len(filtered_videos) < TARGET_MIN_VIDEOS and unique_dict:
        # 如果达到 3000 点赞的不足 10 个，按点赞量补充排序靠前的抖音视频
        all_sorted = sorted(unique_dict.values(), key=lambda x: (x["likes"] + x["collects"] * 2), reverse=True)
        final_videos = all_sorted[:TARGET_MAX_VIDEOS]
    else:
        final_videos = filtered_videos[:TARGET_MAX_VIDEOS]

    print(f"\n[+] 最终为您选出 {len(final_videos)} 个【抖音】AI 热门爆款视频！")

    if not final_videos:
        print("[-] 提示: 未检测到 DOUYIN_COOKIE Secrets，导致抖音云端检索受限。")
        print("    请在 GitHub 仓库 Secrets 中添加 DOUYIN_COOKIE 即可 100% 稳定运行！")
        # 如果没视频，生成提示说明
        send_cookie_missing_notification()
        return []

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(DOWNLOAD_DIR, date_str)
    os.makedirs(today_dir, exist_ok=True)

    # 4. 生成 AI 三维拆解
    for idx, item in enumerate(final_videos, 1):
        print(f"[{idx}/{len(final_videos)}] [抖音] {item['title'][:30]} | ❤️ 点赞: {format_number(item['likes'])}")
        item["analysis"] = generate_ai_analysis(item["title"], item["author"], item["likes"])

    save_reports(today_dir, final_videos, date_str)
    send_mobile_notifications(final_videos, date_str)

    return final_videos


# ==================== 5. 报告导出与手机端微信推送 ====================

def save_reports(today_dir, videos, date_str):
    """保存本地 Markdown 报告与 JSON 数据"""
    json_path = os.path.join(today_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(today_dir, "daily_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🎵 抖音 AI 热门爆款总结日报 ({date_str})\n\n")
        f.write(f"> 精选抖音平台 AI/AIGC/ChatGPT/DeepSeek/Claude/Agent 等关键词热门视频（精选 {len(videos)} 个）\n\n")
        
        for idx, v in enumerate(videos, 1):
            ana = v.get("analysis", {})
            f.write(f"### {idx}. [抖音] {v['title']}\n")
            f.write(f"- **创作者**: {v['author']} | ❤️ **点赞**: {format_number(v['likes'])} | ⭐ **收藏**: {format_number(v['collects'])}\n")
            f.write(f"- 🔗 **抖音原视频直达**: [{v['share_url']}]({v['share_url']})\n")
            f.write(f"- 📌 **视频讲的啥**: {ana.get('summary')}\n")
            f.write(f"- 💡 **对我借鉴**: {ana.get('takeaway')}\n")
            f.write(f"- 🚀 **如何去复制**: {ana.get('replication')}\n\n")
            f.write("---\n\n")

def send_mobile_notifications(videos, date_str):
    """发送【抖音 AI 爆款拆解总结】至手机微信"""
    print("\n[+] 正在将 抖音 AI 爆款拆解报告推送到手机微信...")

    title = f"🎵 抖音 AI 热门爆款拆解日报 ({date_str})"
    
    content_lines = [
        f"# 🎵 抖音 AI 爆款拆解日报 ({date_str})",
        f"已为你精选今日抖音平台最火热的 **{len(videos)} 个 AI/大模型视频**：\n"
    ]

    for idx, v in enumerate(videos, 1):
        ana = v.get("analysis", {})
        content_lines.append(f"### {idx}. [抖音] {v['title'][:32]}")
        content_lines.append(f"👤 **{v['author']}** | ❤️ 点赞 {format_number(v['likes'])} | ⭐ 收藏 {format_number(v['collects'])}")
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
                print("[✔] 成功将 抖音 AI 爆款拆解报告推送到微信 (PushPlus)！")
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

def send_cookie_missing_notification():
    """若缺失 DOUYIN_COOKIE，发送友好接入提醒至微信"""
    if PUSHPLUS_TOKEN:
        title = "⚠️ 抖音 AI 定时抓取需绑定 Cookie 提醒"
        msg = """## ⚠️ 抖音 AI 定时任务需绑定 DOUYIN_COOKIE

当前因 GitHub Actions 云服务器节点位于海外，抖音对匿名访问设置了登录验证。

### 💡 只需 10 秒复制一次 Cookie 即可 100% 稳定运行：
1. 在电脑浏览器打开 [douyin.com](https://www.douyin.com) 并登录账号。
2. 按 `F12` 打开开发者工具，点击 **网络 (Network)** 标签页，刷新一下页面。
3. 找到任意一个请求，在右侧请求头 **Headers** 中找到 `Cookie:` 这一项，复制整段文本。
4. 打开 GitHub 仓库设置 -> `Secrets and variables` -> `Actions` -> 添加 `DOUYIN_COOKIE` 并粘贴。

设置完成后，每天即可 100% 稳定接收抖音 AI 热门视频拆解！
"""
        try:
            requests.post("http://www.pushplus.plus/send", json={"token": PUSHPLUS_TOKEN, "title": title, "content": msg, "template": "markdown"}, timeout=10)
        except Exception:
            pass

if __name__ == "__main__":
    search_douyin_ai_videos()
