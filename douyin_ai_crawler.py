import os
import sys
import json
import time
import re
import datetime
import urllib.parse
import requests

# ==================== 1. 核心配置项 ====================

# 基础搜索种子关键词（用于动态拓词与保底搜索）
BASE_KEYWORDS = [
    "AI", "AIGC", "agent", "ChatGPT", "DeepSeek", "Claude",
    "千问", "Kimi", "GLM", "Gemini", "Grok", "大模型", "智能体"
]

# 过滤与排序规则
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


# ==================== 4. 动态热搜与联想词拓词模块 ====================

def fetch_douyin_sug_keywords(headers):
    """
    通过抖音联想词与热搜接口，动态拓充当天的热门搜索词库
    """
    print("[+] 正在探测抖音今日 AI 实时热搜词与搜索联想词...")
    sug_keywords = []
    discovered_tags = []

    seed_pool = ["AI", "DeepSeek", "智能体", "ChatGPT", "大模型", "AIGC"]

    for seed in seed_pool:
        sug_url = f"https://www.douyin.com/aweme/v1/web/search/sug/?keyword={urllib.parse.quote(seed)}&aid=6383&device_platform=webapp"
        try:
            r = requests.get(sug_url, headers=headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                sug_list = data.get("sug_list", []) or []
                for item in sug_list[:4]:
                    word = item.get("content", "").strip()
                    if word and word not in sug_keywords and word not in BASE_KEYWORDS:
                        sug_keywords.append(word)
                        discovered_tags.append(word)
        except Exception:
            pass
        time.sleep(0.3)

    combined_keywords = list(dict.fromkeys(BASE_KEYWORDS + sug_keywords))
    print(f"[✔] 动态词库构建完成！基础词 {len(BASE_KEYWORDS)} 个 + 今日飙升热搜词 {len(sug_keywords)} 个。")
    if discovered_tags:
        print(f"    🔥 发现今日热搜关联词: {', '.join(discovered_tags[:8])}")
    
    return combined_keywords, discovered_tags


# ==================== 5. 创作者级 AI 爆款拆解引擎 ====================

def generate_ai_analysis(title, author, likes, collects, comments):
    """
    深度拆解：输出创作者最关心的“爆款属性”、“黄金前3秒钩子”、“四段式复刻脚本”与“引流话术”
    """
    time.sleep(1.2)  # 控频防 API 429 限制

    collect_ratio = (collects / likes * 100) if likes > 0 else 0
    ratio_desc = f"收藏率高达 {collect_ratio:.1f}%（干货实用型）" if collect_ratio >= 25 else f"收藏率 {collect_ratio:.1f}%"

    if GEMINI_API_KEY:
        try:
            prompt = f"""你是一名抖音千万播放短视频编导与爆款拆解专家。请对以下【抖音 AI/大模型】高互动视频进行针对创作者的深度复刻拆解：

【视频数据】
标题：{title}
创作者：{author}
数据：点赞 {likes}，收藏 {collects}（{ratio_desc}），评论 {comments}

请严格按以下 4 项格式输出（每项保持干练，具有直接指导实操拍片价值）：

🎯 爆款属性定位：[1句话指出核心受众画像与内容类型，如：高收藏实操干货 / 职场提效痛点反差 / 认知颠覆]
⏱️ 黄金前3秒钩子：[给出直接可照读的第1句开场台词 + 前3秒视觉画面设计（如痛点提问/展示震惊成果）]
🎬 四段式复刻脚本：
  • 0-5s 痛点/成果：[开篇痛点引发共鸣或惊艳成果展示]
  • 5-25s 工具实操：[核心 AI 工具演示与关键步骤]
  • 25-45s 避坑/提效：[对比传统做法的效率提升或避坑要点]
  • 45-60s 转化收尾：[引导互动、点赞收藏或资料领取]
💬 评论区引流钩子：[建议作者置顶的话术与引导粉丝扣1领取资料/提示词的具体技巧]"""

            model_name = "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            resp = requests.post(url, headers=headers, json=payload, timeout=12)
            if resp.status_code != 200:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
                resp = requests.post(url, headers=headers, json=payload, timeout=12)

            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                res = parse_llm_text_clean(text)
                if res["hook"] and "【" not in res["positioning"]:
                    print(f"[✔] 成功调用 Gemini 生成创作者级爆款复刻拆解！")
                    return res
        except Exception as e:
            print(f"[!] 调用 Gemini API 异常: {e}")

    return heuristic_balanced_analysis(title, author, likes, collects, comments)

def parse_llm_text_clean(text):
    """解析大模型文本，提取创作者 4 维核心字段"""
    positioning, hook, script_sop, cta_hook = "", "", "", ""
    current_section = ""
    script_lines = []

    for line in text.split("\n"):
        line_s = line.strip()
        if not line_s:
            continue
        if "🎯 爆款属性定位" in line_s or "爆款属性" in line_s:
            current_section = "pos"
            positioning = line_s.split("：")[-1].strip() if "：" in line_s else line_s
        elif "⏱️ 黄金前3秒钩子" in line_s or "黄金前3秒" in line_s:
            current_section = "hook"
            hook = line_s.split("：")[-1].strip() if "：" in line_s else line_s
        elif "🎬 四段式复刻脚本" in line_s or "复刻脚本" in line_s:
            current_section = "script"
        elif "💬 评论区引流钩子" in line_s or "评论区" in line_s:
            current_section = "cta"
            cta_hook = line_s.split("：")[-1].strip() if "：" in line_s else line_s
        else:
            if current_section == "script":
                script_lines.append(line_s)
            elif current_section == "pos" and not positioning:
                positioning = line_s
            elif current_section == "hook" and not hook:
                hook = line_s
            elif current_section == "cta" and not cta_hook:
                cta_hook = line_s

    script_sop = "\n".join(script_lines) if script_lines else ""

    # 清理多余标签
    positioning = re.sub(r'^[🎯\s*]+', '', positioning).replace("爆款属性定位：", "").strip()
    hook = re.sub(r'^[⏱️\s*]+', '', hook).replace("黄金前3秒钩子：", "").strip()
    cta_hook = re.sub(r'^[💬\s*]+', '', cta_hook).replace("评论区引流钩子：", "").strip()

    if not positioning: positioning = "面向职场办公与自媒体人群的高实用价值实操教程。"
    if not hook: hook = "台词：‘如果你还在手动做这个，AI 早就能 3 秒搞定了！’ + 画面：展示效率倍增的震撼成果录屏。"
    if not script_sop: 
        script_sop = "• 0-5s 痛点：展示繁琐旧流程与 AI 极速成片对比\n• 5-25s 实操：演示核心 Prompt 与工具操作页面\n• 25-45s 提效：展示最终产出物并标明节省的时间\n• 45-60s 转化：引导去评论区获取同款配置与提示词"
    if not cta_hook: cta_hook = "置顶评论：‘视频里用到的完整提示词和工具链接已经打包，评论区扣【资料】私信发送！’"

    return {
        "positioning": positioning,
        "hook": hook,
        "script_sop": script_sop,
        "cta_hook": cta_hook
    }

def heuristic_balanced_analysis(title, author, likes, collects, comments):
    """内置离线规则库（当无大模型 Key 或 API 异常时保障输出质量）"""
    tool_name = "AI大模型"
    for k in ["DeepSeek", "ChatGPT", "Claude", "千问", "Kimi", "GLM", "Gemini", "Grok", "Sora", "即梦", "Agent"]:
        if k.lower() in title.lower():
            tool_name = k
            break

    collect_ratio = (collects / likes * 100) if likes > 0 else 0

    if "agent" in title.lower() or "智能体" in title:
        positioning = f"聚焦‘AI自动打工’的前沿高价值实操，击中职场人自动化提效刚需（收藏率 {collect_ratio:.1f}%）。"
        hook = f"台词：‘别再自己熬夜加班了，教你用 {tool_name} 搭建专属智能体，全自动跑通业务！’ + 画面：展示 Agent 自动敲代码/产出报告全过程。"
        script_sop = (
            f"• 0-5s 痛点：抛出痛点‘一个人干一个团队的活’\n"
            f"• 5-25s 实操：展示 {tool_name} 的工作流搭建关键节点\n"
            f"• 25-45s 提效：运行 Agent 并输出成品，直观呈现 10 倍效率\n"
            f"• 45-60s 转化：提示词/工作流配置文件引导评论区自取"
        )
        cta_hook = f"置顶评论：‘搭建智能体的完整配置文件和 Prompt 模板已整理好，评论区扣【666】发你！’"
    elif "提示词" in title or "prompt" in title.lower() or "教程" in title:
        positioning = f"保姆级指令/技巧教学，极强利他属性引发观众高收藏（收藏率 {collect_ratio:.1f}%）。"
        hook = f"台词：‘90% 的人都不知道，{tool_name} 只要加上这 3 句提示词，输出质量直接翻倍！’ + 画面：前后输出效果强烈对比。"
        script_sop = (
            f"• 0-5s 痛点：展示普通提问的平庸回答 vs 高阶 Prompt 的惊艳回答\n"
            f"• 5-25s 实操：逐句拆解这套万能公式的底层逻辑\n"
            f"• 25-45s 提效：套用到真实业务场景（写文案/做方案/分析数据）\n"
            f"• 45-60s 转化：点赞收藏防止找不到，引导评论区领完整指令库"
        )
        cta_hook = f"置顶评论：‘高清版提示词思维导图已放在后台，评论区回复【学习】免费获取！’"
    else:
        positioning = f"结合当下 {tool_name} 热门话题的降本增效解决方案，适合快速复刻跟进流量。"
        hook = f"台词：‘看完这个视频，彻底颠覆你对 {tool_name} 的认知！’ + 画面：快节奏卡点演示神器核心界面。"
        script_sop = (
            f"• 0-5s 痛点：提出当下行业/职场普遍痛点\n"
            f"• 5-25s 实操：演示核心功能与 3 步操作步骤\n"
            f"• 25-45s 提效：输出成品效果展示，强化实用性\n"
            f"• 45-60s 转化：号召点赞关注，下期分享更硬核技巧"
        )
        cta_hook = f"置顶评论：‘你平时用 {tool_name} 最多的场景是什么？欢迎在评论区交流避坑！’"

    return {
        "positioning": positioning,
        "hook": hook,
        "script_sop": script_sop,
        "cta_hook": cta_hook
    }


# ==================== 6. 抖音搜索与综合爆款价值排序 ====================

def fetch_douyin_ai_videos():
    """
    检索并筛选 30 天内发布、点赞 >= 3000、综合爆款指数最高的 10 个抖音 AI 视频
    """
    print("==========================================")
    print("🎯 开始抓取 抖音 (Douyin) 今日高价值 AI 爆款视频与搜索趋势...")
    print("==========================================")

    history_set = load_history_ids()
    print(f"[+] 已加载历史数据库，已去重 {len(history_set)} 个历史已推送视频。")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Cookie": DOUYIN_COOKIE
    }
    
    # 1. 动态拓充今日热搜词库
    search_keywords, discovered_tags = fetch_douyin_sug_keywords(headers)

    captured_videos = []
    seen_in_run = set()

    now_ts = int(time.time())
    max_age_seconds = MAX_AGE_DAYS * 86400

    print(f"\n[+] 开始全网扫描 {len(search_keywords)} 个 AI 核心关键词及热搜词...")

    for kw in search_keywords:
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

                        # 计算收藏率与综合爆款得分 (加权高收藏干货)
                        collect_rate = (collect_count / digg_count * 100) if digg_count > 0 else 0
                        comment_rate = (comment_count / digg_count * 100) if digg_count > 0 else 0
                        viral_score = int(digg_count * 1.0 + collect_count * 3.5 + comment_count * 2.5)

                        # 标签分类
                        tags = []
                        if collect_rate >= 25:
                            tags.append("⭐高收藏干货")
                        if comment_rate >= 4:
                            tags.append("💬高互动热议")
                        if digg_count >= 50000:
                            tags.append("💥超级大爆款")
                        if not tags:
                            tags.append("💡高潜选题")

                        seen_in_run.add(aweme_id)
                        captured_videos.append({
                            "id": aweme_id,
                            "title": desc,
                            "author": author,
                            "likes": digg_count,
                            "collects": collect_count,
                            "comments": comment_count,
                            "collect_rate": collect_rate,
                            "comment_rate": comment_rate,
                            "viral_score": viral_score,
                            "tag": " | ".join(tags),
                            "matched_keyword": kw,
                            "pub_date": pub_date,
                            "platform": "抖音",
                            "video_url": video_url,
                            "share_url": f"https://www.douyin.com/video/{aweme_id}"
                        })
        except Exception as e:
            print(f"[-] 抖音 API 搜索 '{kw}' 发生异常: {e}")

    # 按爆款综合得分排序（高收藏权重更高）
    filtered_videos = [v for v in captured_videos if v["likes"] >= MIN_LIKES]
    filtered_videos.sort(key=lambda x: x["viral_score"], reverse=True)

    if len(filtered_videos) < TARGET_MIN_VIDEOS and captured_videos:
        all_sorted = sorted(captured_videos, key=lambda x: x["viral_score"], reverse=True)
        final_videos = all_sorted[:TARGET_MAX_VIDEOS]
    else:
        final_videos = filtered_videos[:TARGET_MAX_VIDEOS]

    print(f"\n[+] 筛选完成！已精选出 {len(final_videos)} 个【综合价值最高】的抖音 AI 爆款视频。")

    if not final_videos:
        print("[-] 提示: 未搜集到符合条件的最新抖音视频，请检查 Cookie 有效性。")
        return []

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(DOWNLOAD_DIR, date_str)
    os.makedirs(today_dir, exist_ok=True)

    for idx, item in enumerate(final_videos, 1):
        print(f"[{idx}/{len(final_videos)}] [{item['tag']}] {item['title'][:28]}... | ❤️ {format_number(item['likes'])} | ⭐ 收藏率: {item['collect_rate']:.1f}%")
        item["analysis"] = generate_ai_analysis(item["title"], item["author"], item["likes"], item["collects"], item["comments"])
        history_set.add(item["id"])

    save_reports(today_dir, final_videos, date_str, discovered_tags)
    send_mobile_notifications(final_videos, date_str, discovered_tags)
    save_history_ids(history_set)

    return final_videos


# ==================== 7. 报告导出与微信全景推送 ====================

def save_reports(today_dir, videos, date_str, discovered_tags):
    """保存本地 Markdown 报告与 JSON 数据"""
    json_path = os.path.join(today_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(today_dir, "daily_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🎵 抖音 AI 热门爆款与创作者复刻日报 ({date_str})\n\n")
        
        if discovered_tags:
            tags_str = " &nbsp;|&nbsp; ".join([f"`{t}`" for t in discovered_tags[:8]])
            f.write(f"> 🔥 **今日抖音 AI 热搜飙升词**: {tags_str}\n\n")
        else:
            f.write(f"> 精选近 30 天高收藏/高互动 AI 爆款视频 | 创作者 1:1 分镜头脚本复刻指南\n\n")
        
        for idx, v in enumerate(videos, 1):
            ana = v.get("analysis", {})
            f.write(f"## {idx}. 【{v['tag']}】{v['title']}\n\n")
            f.write(f"👤 **创作者**: {v['author']} &nbsp;|&nbsp; 📅 {v['pub_date']} &nbsp;|&nbsp; 🏆 爆款指数: **{format_number(v['viral_score'])}**\n")
            f.write(f"❤️ **点赞**: {format_number(v['likes'])} &nbsp;|&nbsp; ⭐ **收藏**: {format_number(v['collects'])} (**{v['collect_rate']:.1f}%**) &nbsp;|&nbsp; 💬 **评论**: {format_number(v['comments'])}\n\n")
            f.write(f"🔗 **原视频链接**: [{v['share_url']}]({v['share_url']})\n\n")
            f.write(f"🎯 **爆款定位**: {ana.get('positioning')}\n\n")
            f.write(f"⏱️ **黄金前 3 秒钩子**:\n{ana.get('hook')}\n\n")
            f.write(f"🎬 **四段式复刻脚本**:\n```text\n{ana.get('script_sop')}\n```\n\n")
            f.write(f"💬 **评论区引流钩子**:\n{ana.get('cta_hook')}\n\n")
            f.write("---\n\n")

    print(f"[✔] 已生成本地完整报告: {md_path}")

def send_mobile_notifications(videos, date_str, discovered_tags):
    """发送创作者实战复刻版微信推送"""
    print("\n[+] 正在将 10 个创作者爆款复刻指南推送到手机微信...")

    title = f"🎵 抖音 AI 爆款与复刻指南 ({date_str})"
    
    tags_line = ""
    if discovered_tags:
        tags_line = f"🔥 **今日热搜词**：{'、'.join(discovered_tags[:6])}\n\n"

    content_blocks = [
        f"# 🎵 抖音 AI 热门爆款复刻指南 ({date_str})\n",
        tags_line,
        f"今日精选 **{len(videos)} 个高收藏/高互动 AI 爆款**（近 30 天内发布）：\n\n---\n"
    ]

    for idx, v in enumerate(videos, 1):
        ana = v.get("analysis", {})
        
        card = f"""### {idx}. 【{v['tag']}】{v['title'][:32]}

👤 **创作者**：{v['author']} &nbsp;|&nbsp; 📅 {v['pub_date']}
❤️ 点赞 {format_number(v['likes'])} &nbsp;|&nbsp; ⭐ 收藏 {format_number(v['collects'])} (**{v['collect_rate']:.1f}%**) &nbsp;|&nbsp; 💬 评论 {format_number(v['comments'])}

🎯 **爆款定位**：
{ana.get('positioning')}

⏱️ **黄金前 3 秒钩子**：
{ana.get('hook')}

🎬 **四段式复刻脚本**：
{ana.get('script_sop')}

💬 **评论区引流钩子**：
{ana.get('cta_hook')}

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
                print("[✔] 成功将 10 个创作者爆款拆解推送到微信 (PushPlus)！")
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
