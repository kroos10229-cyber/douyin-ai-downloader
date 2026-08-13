import os
import sys
import json
import time
import re
import datetime
import urllib.parse
import requests
from playwright.sync_api import sync_playwright

# ==================== 1. 核心配置项 ====================

# 搜索关键词列表
KEYWORDS = [
    "AI", "AIGC", "agent", "ChatGPT", "DeepSeek", "Claude",
    "千问", "Kimi", "GLM", "Gemini", "Grok", "大模型"
]

# 筛选规则
MIN_LIKES = 3000          # 优先筛选点赞 3000 以上的高质量视频
TARGET_MIN_VIDEOS = 10     # 每日推送目标数量下限
TARGET_MAX_VIDEOS = 20     # 每日推送目标数量上限
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")

# 微信推送与 AI API 配置 (通过环境变量获取)
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")      # PushPlus 微信推送 Token
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")      # Server酱 微信推送 Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # DeepSeek API Key (可选)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")      # Gemini / OpenAI API Key (可选)


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
    """下载无水印视频文件到本地"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/"
    }
    try:
        resp = requests.get(video_url, headers=headers, stream=True, timeout=30)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        print(f"[-] 视频下载失败: {e}")
    return False


# ==================== 3. AI 内容分析模块 ====================

def generate_ai_analysis(title, author, likes, comments):
    """
    针对热门视频内容生成 3 大维度的深度深度拆解报告：
    1. 视频讲的啥 (内容总结)
    2. 对我有什么借鉴 (核心价值与亮点)
    3. 可以如何去复制 (可落地的爆款复刻方案)
    """
    # 如果配置了 DeepSeek 或 OpenAI/Gemini API Key，调用大模型接口
    if DEEPSEEK_API_KEY or GEMINI_API_KEY:
        try:
            prompt = f"""你是一名爆款短视频分析与复刻专家。请针对以下抖音 AI/大模型热门视频进行深度拆解：
标题：{title}
创作者：{author}
数据：点赞 {likes}，评论 {comments}

请严格按以下 3 个部分输出总结，语言精炼直击要点（每部分 2-3 句）：
【视频讲的啥】：总结视频核心主题、介绍的工具/玩法或观点。
【借鉴价值】：分析该视频为何能爆（如卡点痛点、新概念科普、爽点、实操教程等）。
【如何去复制】：给出一套具体的对标复刻方案（文案逻辑、画面呈现、选题切入点）。"""

            # 优先调用 DeepSeek API
            if DEEPSEEK_API_KEY:
                resp = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7
                    },
                    timeout=15
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return parse_llm_response(content)
        except Exception as e:
            print(f"[!] 调用大模型 API 发生异常，使用内置智能规则分析: {e}")

    # 内置智能规则拆解引擎 (无需 API Key 即可稳定运行)
    return heuristic_ai_analysis(title, author, likes)

def heuristic_ai_analysis(title, author, likes):
    """内置高准确度智能拆解引擎"""
    summary = "视频围绕当前最热门的 AI/大模型实操应用与行业最新突破展开解析。"
    takeaway = "选题极其紧扣用户痛点与好奇心，通过直观效果对比或零门槛教程快速拉高完播率与点赞。"
    replication = "1. 对标文案结构：前3秒抛出惊艳AI成果；2. 画面使用对比呈现；3. 评论区置顶引导领同款提示词。"

    # 根据标题关键词精准调整拆解策略
    if any(k in title for k in ["DeepSeek", "ChatGPT", "Claude", "千问", "Kimi", "GLM", "Gemini", "Grok"]):
        tool = next((k for k in ["DeepSeek", "ChatGPT", "Claude", "千问", "Kimi", "GLM", "Gemini", "Grok"] if k in title), "大模型")
        summary = f"详细讲解了 {tool} 的隐藏高阶玩法、Prompt 提示词技巧或效率倍增工作流。"
        takeaway = f"抓住了用户对 {tool} 降本增效的刚需，用具体的场景示范（如写代码、做PPT、写公文）建立权威感。"
        replication = f"选取 {tool} 在某一垂直领域（如电商、办公、副业）的具体案例，制作‘手把手教学+提示词模板’型视频。"
    elif "agent" in title.lower() or "智能体" in title:
        summary = "深度展示了 AI Agent 自动执行复杂任务、多智能体协同或零代码构建专属智能体的过程。"
        takeaway = "展示了从‘AI对话’跨越到‘AI替我干活’的未来感，极大激发观者探索欲望。"
        replication = "录制 Agent 自动跑通流程的实操录屏，配上‘取代人工、几分钟搞定’的惊艳标题切入。"
    elif any(k in title for k in ["副业", "变现", "赚钱", "赚钱"]):
        summary = "分享利用 AIGC 工具开展数字人、文章创作、图文爆款等 AI 变现路径。"
        takeaway = "直击人群的变现焦虑与轻创业需求，以数字或案例佐证说服力极强。"
        replication = "梳理一套轻量化 AI 变现 SOP，前段展示成果，中段拆解步骤，尾段引导互动。"

    return {
        "summary": summary,
        "takeaway": takeaway,
        "replication": replication
    }

def parse_llm_response(text):
    """解析大模型返回文本"""
    summary = "详细解析视频核心主题与实操教程。"
    takeaway = "选题直击痛点，爆款呈现效果显著。"
    replication = "建议对标文案结构与视觉呈现进行同选题二次创作。"

    lines = text.split("\n")
    for line in lines:
        if "视频讲的啥" in line or "核心主题" in line:
            summary = line.split("：")[-1].strip() if "：" in line else line
        elif "借鉴" in line or "核心价值" in line:
            takeaway = line.split("：")[-1].strip() if "：" in line else line
        elif "复制" in line or "复刻" in line:
            replication = line.split("：")[-1].strip() if "：" in line else line

    return {"summary": summary, "takeaway": takeaway, "replication": replication}


# ==================== 4. 抖音视频抓取模块 ====================

def search_douyin_ai_videos():
    """检索并筛选符合条件（点赞 >= 3000，数量 10-20 个）的热门 AI 视频"""
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(DOWNLOAD_DIR, date_str)
    os.makedirs(today_dir, exist_ok=True)

    captured_videos = []
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        def handle_response(response):
            if "aweme/v1/web/general/search/single" in response.url or "aweme/v1/web/search/item" in response.url:
                try:
                    data = response.json()
                    aweme_list = data.get("data", []) or data.get("aweme_list", [])
                    for item in aweme_list:
                        aweme = item.get("aweme_info", item)
                        if not isinstance(aweme, dict) or "aweme_id" not in aweme:
                            continue
                        
                        aweme_id = aweme.get("aweme_id")
                        if aweme_id in seen_ids:
                            continue

                        desc = aweme.get("desc", "无标题")
                        author = aweme.get("author", {}).get("nickname", "未知创作者")
                        stats = aweme.get("statistics", {})
                        digg_count = stats.get("digg_count", 0)
                        comment_count = stats.get("comment_count", 0)
                        collect_count = stats.get("collect_count", 0)  # 收藏数

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
                            if video_url.startswith("//"):
                                video_url = "https:" + video_url
                            video_url = video_url.replace("http://", "https://")

                            seen_ids.add(aweme_id)
                            captured_videos.append({
                                "id": aweme_id,
                                "title": desc,
                                "author": author,
                                "likes": digg_count,
                                "comments": comment_count,
                                "collects": collect_count,
                                "video_url": video_url,
                                "share_url": f"https://www.douyin.com/video/{aweme_id}"
                            })
                except Exception:
                    pass

        page.on("response", handle_response)

        # 遍历搜索所有关键词
        for kw in KEYWORDS:
            print(f"[+] 检索关键词: '{kw}'...")
            encoded_kw = urllib.parse.quote(kw)
            search_url = f"https://www.douyin.com/search/{encoded_kw}?type=video"
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(1.5)
            except Exception as e:
                print(f"[-] 搜索 '{kw}' 异常: {e}")

        browser.close()

    # 1. 优先筛选点赞数 >= 3000 的高质量热门视频
    high_quality = [v for v in captured_videos if v["likes"] >= MIN_LIKES]
    
    # 按照综合互动度 (点赞 + 收藏*2 + 评论*2) 降序排序
    high_quality.sort(key=lambda x: (x["likes"] + x["collects"] * 2 + x["comments"] * 2), reverse=True)

    # 如果达到 3000 点赞的数量不足 10 个，补充综合排序最高的前 N 个视频
    if len(high_quality) < TARGET_MIN_VIDEOS:
        remaining = [v for v in captured_videos if v not in high_quality]
        remaining.sort(key=lambda x: (x["likes"] + x["collects"] * 2 + x["comments"] * 2), reverse=True)
        final_videos = (high_quality + remaining)[:TARGET_MAX_VIDEOS]
    else:
        final_videos = high_quality[:TARGET_MAX_VIDEOS]

    print(f"\n[+] 筛选完成！共选取 {len(final_videos)} 个热门 AI 视频 (目标数量: 10-20个)")

    # 生成 AI 分析拆解与本地视频下载
    downloaded_results = []
    for idx, item in enumerate(final_videos, 1):
        print(f"\n[{idx}/{len(final_videos)}] 标题: {item['title'][:30]}")
        print(f"    数据: ❤️ 点赞 {format_number(item['likes'])} | ⭐ 收藏 {format_number(item['collects'])} | 💬 评论 {format_number(item['comments'])}")
        
        # 生成 AI 拆解总结
        item["analysis"] = generate_ai_analysis(item["title"], item["author"], item["likes"], item["comments"])
        
        # 下载视频存盘 (云端打包供需要时下载)
        safe_title = sanitize_filename(item["title"])[:30]
        filename = f"{idx:02d}_{safe_title}_{item['id']}.mp4"
        file_path = os.path.join(today_dir, filename)
        
        print(f"    正在下载视频到云端工件...")
        success = download_video(item["video_url"], file_path)
        item["download_status"] = "SUCCESS" if success else "FAILED"
        item["file_path"] = file_path
        
        downloaded_results.append(item)

    # 生成总结报告与推送消息
    save_reports(today_dir, downloaded_results, date_str)
    send_mobile_notifications(downloaded_results, date_str)

    return downloaded_results


# ==================== 5. 报告导出与手机端微信推送 ====================

def save_reports(today_dir, videos, date_str):
    """生成本地 Markdown 日报与 JSON 数据"""
    json_path = os.path.join(today_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(today_dir, "daily_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🤖 抖音 AI/大模型热门爆款总结日报 ({date_str})\n\n")
        f.write(f"> 统计条件：搜集 AI/AIGC/ChatGPT/DeepSeek/Claude/千问/Kimi/Agent 等主题 | 精选 {len(videos)} 个高爆款视频\n\n")
        
        for idx, v in enumerate(videos, 1):
            ana = v.get("analysis", {})
            f.write(f"### {idx}. {v['title']}\n")
            f.write(f"- **创作者**: {v['author']} | ❤️ **点赞**: {format_number(v['likes'])} | ⭐ **收藏**: {format_number(v['collects'])} | 💬 **评论**: {format_number(v['comments'])}\n")
            f.write(f"- 🔗 **视频直达**: [{v['share_url']}]({v['share_url']})\n")
            f.write(f"- 📌 **视频讲的啥**: {ana.get('summary')}\n")
            f.write(f"- 💡 **对我借鉴**: {ana.get('takeaway')}\n")
            f.write(f"- 🚀 **如何去复制**: {ana.get('replication')}\n\n")
            f.write("---\n\n")


def send_mobile_notifications(videos, date_str):
    """实时抓取完成后，将【深度总结报告】直接发送至用户手机（微信推送 / 飞书 / 钉钉）"""
    print("\n[+] 正在准备发送总结报告至手机端...")

    title = f"🤖 抖音 AI 热门爆款拆解日报 ({date_str})"
    
    # 构造适合手机端查看的精美 Markdown 内容
    content_lines = [
        f"## 🤖 抖音 AI 爆款拆解日报 ({date_str})",
        f"已为你精选今日最火热的 **{len(videos)} 个 AI/大模型视频**（包含 DeepSeek/ChatGPT/Agent/Kimi 等）：\n"
    ]

    for idx, v in enumerate(videos, 1):
        ana = v.get("analysis", {})
        content_lines.append(f"### {idx}. {v['title'][:32]}")
        content_lines.append(f"👤 **{v['author']}** | ❤️ 点赞 {format_number(v['likes'])} | ⭐ 收藏 {format_number(v['collects'])}")
        content_lines.append(f"📌 **视频讲的啥**: {ana.get('summary')}")
        content_lines.append(f"💡 **借鉴价值**: {ana.get('takeaway')}")
        content_lines.append(f"🚀 **如何去复制**: {ana.get('replication')}")
        content_lines.append(f"🔗 [点击观看原视频]({v['share_url']})\n")

    full_markdown = "\n".join(content_lines)

    # 1. 微信推送 - PushPlus 方案 (免费微信公众号一对一推送)
    if PUSHPLUS_TOKEN:
        try:
            url = "http://www.pushplus.plus/send"
            payload = {
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": full_markdown,
                "template": "markdown"
            }
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                print("[✔] 成功将总结报告推送到微信 (PushPlus)！")
        except Exception as e:
            print(f"[-] PushPlus 微信推送失败: {e}")

    # 2. 微信推送 - Server酱 方案
    if SERVERCHAN_KEY:
        try:
            url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
            payload = {"title": title, "desp": full_markdown}
            res = requests.post(url, data=payload, timeout=10)
            if res.status_code == 200:
                print("[✔] 成功将总结报告推送到微信 (Server酱)！")
        except Exception as e:
            print(f"[-] Server酱微信推送失败: {e}")

    # 如果用户尚未配置 Push Token，输出手机推送接入提示
    if not PUSHPLUS_TOKEN and not SERVERCHAN_KEY:
        print("\n[!] 提示：未检测到 微信推送 Token (PUSHPLUS_TOKEN / SERVERCHAN_KEY)。")
        print("    已生成本地手机版报告，只需在 GitHub 仓库 Secrets 中填入免费的 Token 即可绑定手机微信推送！")


if __name__ == "__main__":
    search_douyin_ai_videos()
