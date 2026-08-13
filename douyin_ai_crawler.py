import os
import sys
import json
import time
import re
import datetime
import urllib.parse
import requests
from playwright.sync_api import sync_playwright

# 配置项
KEYWORDS = ["AI热门", "AIGC", "ChatGPT", "AI视频"]
MAX_VIDEOS_PER_KEYWORD = 3  # 每个关键词抓取的前N名热门视频
TOTAL_MAX_VIDEOS = 5       # 每日汇总下载的最高限制数量
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
NOTIFY_WEBHOOK = os.getenv("NOTIFY_WEBHOOK", "")  # 可选：飞书/钉钉/微信推送 Webhook URL

def sanitize_filename(name):
    """清理非法的文件名字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

def format_number(num):
    """格式化点赞数/播放数"""
    try:
        num = int(num)
        if num >= 10000:
            return f"{num / 10000:.1f}万"
        return str(num)
    except (ValueError, TypeError):
        return str(num)

def download_video(video_url, output_path):
    """下载视频文件到本地"""
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
        else:
            print(f"[-] 下载失败, HTTP状态码: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[-] 下载出错: {e}")
        return False

def search_douyin_videos(keywords, max_per_keyword=3):
    """使用 Playwright 搜索抖音 AI 热门视频"""
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(DOWNLOAD_DIR, date_str)
    os.makedirs(today_dir, exist_ok=True)

    captured_videos = []
    seen_ids = set()

    with sync_playwright() as p:
        # 启动 Chromium 无头浏览器
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        page = context.new_page()

        # 监听 API 响应获取高清视频数据
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

                        # 提取视频元数据
                        desc = aweme.get("desc", "无标题")
                        author = aweme.get("author", {}).get("nickname", "未知创作者")
                        stats = aweme.get("statistics", {})
                        digg_count = stats.get("digg_count", 0)
                        comment_count = stats.get("comment_count", 0)
                        share_count = stats.get("share_count", 0)
                        create_time = aweme.get("create_time", 0)

                        # 提取无水印视频播放链接
                        video_data = aweme.get("video", {})
                        play_addr = video_data.get("play_addr", {}).get("url_list", [])
                        bitrate_list = video_data.get("bit_rate", [])

                        video_url = ""
                        if bitrate_list:
                            # 选择最高清晰度
                            sorted_bitrate = sorted(bitrate_list, key=lambda x: x.get("quality_type", 0), reverse=True)
                            for b in sorted_bitrate:
                                urls = b.get("play_addr", {}).get("url_list", [])
                                if urls:
                                    video_url = urls[0]
                                    break
                        if not video_url and play_addr:
                            video_url = play_addr[0]

                        if video_url:
                            # 转换为无水印/原画 https
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
                                "shares": share_count,
                                "create_time": create_time,
                                "video_url": video_url,
                                "share_url": f"https://www.douyin.com/video/{aweme_id}"
                            })
                except Exception as e:
                    pass

        page.on("response", handle_response)

        for kw in keywords:
            print(f"[+] 正在抖音搜索关键词: '{kw}'...")
            encoded_kw = urllib.parse.quote(kw)
            search_url = f"https://www.douyin.com/search/{encoded_kw}?type=video"
            
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(4)  # 等待数据加载与 API 响应
                
                # 模拟滚动页面以加载更多热门视频
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(2)
            except Exception as e:
                print(f"[-] 搜索 '{kw}' 发生异常: {e}")

        browser.close()

    # 按点赞数排序，取前 N 个最热门视频
    captured_videos.sort(key=lambda x: x["likes"], reverse=True)
    top_videos = captured_videos[:TOTAL_MAX_VIDEOS]

    print(f"\n[+] 共检索并筛选出 {len(top_videos)} 个 AI 热门视频：")

    downloaded_results = []
    for idx, item in enumerate(top_videos, 1):
        safe_title = sanitize_filename(item["title"])[:30]
        filename = f"{idx:02d}_{safe_title}_{item['id']}.mp4"
        file_path = os.path.join(today_dir, filename)

        print(f"\n[{idx}/{len(top_videos)}] 标题: {item['title']}")
        print(f"    作者: {item['author']} | 点赞: {format_number(item['likes'])} | 评论: {format_number(item['comments'])}")
        print(f"    正在下载至: {filename}...")

        success = download_video(item["video_url"], file_path)
        if success:
            item["file_path"] = file_path
            item["download_status"] = "SUCCESS"
            print(f"    [✔] 下载完成！")
        else:
            item["download_status"] = "FAILED"

        downloaded_results.append(item)

    # 导出 JSON 报告与 Markdown 日报
    save_reports(today_dir, downloaded_results, date_str)
    
    # 发送通知 (如果配置了 Webhook)
    if NOTIFY_WEBHOOK:
        send_webhook_notification(NOTIFY_WEBHOOK, downloaded_results, date_str)

    return downloaded_results

def save_reports(today_dir, videos, date_str):
    """保存下载元数据 JSON 与 Markdown 统计日报"""
    json_path = os.path.join(today_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(today_dir, "daily_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 抖音 AI 热门视频每日汇总报告 ({date_str})\n\n")
        f.write(f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**成功下载视频数**: {sum(1 for v in videos if v.get('download_status') == 'SUCCESS')}/{len(videos)}\n\n")
        f.write("| 序号 | 视频标题 | 创作者 | 点赞数 | 评论数 | 链接 |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for idx, item in enumerate(videos, 1):
            title = item['title'].replace('\n', ' ')
            likes = format_number(item['likes'])
            comments = format_number(item['comments'])
            f.write(f"| {idx} | {title} | {item['author']} | {likes} | {comments} | [观看链接]({item['share_url']}) |\n")
    
    print(f"\n[+] 统计报告已生成:\n    - JSON: {json_path}\n    - Markdown: {md_path}")

def send_webhook_notification(webhook_url, videos, date_str):
    """推送每日热门视频日报到飞书/钉钉/企业微信/Webhooks"""
    msg_lines = [f"🤖 抖音 AI 热门视频日报 ({date_str})", "------------------------------"]
    for idx, item in enumerate(videos[:5], 1):
        msg_lines.append(f"{idx}. {item['title'][:25]}")
        msg_lines.append(f"   👤 {item['author']} | ❤️ 点赞: {format_number(item['likes'])}")
        msg_lines.append(f"   🔗 {item['share_url']}")
    
    payload = {
        "msg_type": "text",
        "content": {"text": "\n".join(msg_lines)}
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
        print("[+] Webhook 消息通知已发送！")
    except Exception as e:
        print(f"[-] 发送 Webhook 通知失败: {e}")

if __name__ == "__main__":
    search_douyin_videos(KEYWORDS, MAX_VIDEOS_PER_KEYWORD)
