# 抖音 AI 热门视频每日自动搜索与下载系统

本自动化任务系统专注于**每日定时抓取抖音平台上的 AI 热门视频**，筛选高点赞高热度内容，自动下载无水印高清视频，并生成每日统计报告。

---

## 🌟 功能特性

1. **自动搜索热门 AI 视频**：支持针对 `AI热门`、`AIGC`、`ChatGPT`、`AI视频` 等关键词进行动态全网检索。
2. **智能筛选与排序**：按点赞量、评论量自动排序，提炼出每日最火热的前 N 个视频。
3. **高清无水印下载**：提取原画/高清无水印视频播放链接并自动下载存盘。
4. **自动导出日报**：同步生成 `metadata.json` 与可读性极强的 `daily_report.md` Markdown 日报。
5. **线上云端全自动触发（无需电脑开机）**：基于 **GitHub Actions Cron** 每天定时在云端运行，自动打包视频文件供随时下载，并支持推送微信/飞书通知。

---

## 🚀 线上免开机定时方案 (GitHub Actions)

> 💡 **无需保持个人电脑开机**，每天早上 8 点由 GitHub 云服务器全自动执行，执行完成后可直接在网页或手机上下载视频 Zip 包。

### 部署步骤：
1. **创建 GitHub 仓库**：
   在 GitHub 上新建一个仓库（例如：`douyin-ai-downloader`）。

2. **推送到 GitHub**：
   在当前项目目录下执行：
   ```bash
   git init
   git add .
   git commit -m "feat: initial commit for douyin ai crawler"
   git remote add origin https://github.com/你的用户名/douyin-ai-downloader.git
   git push -u origin main
   ```

3. **云端运行效果**：
   - 每天北京时间 **08:00 AM** 云端将自动触发运行。
   - 运行完成后，在 GitHub 仓库的 **Actions** 页签点击最新的运行记录，即可在 `Artifacts` 区域直接**一键下载包含视频和报告的 Zip 压缩包**。
   - *(可选)* 若需要在微信/飞书/钉钉接收每日提醒，可在仓库 `Settings -> Secrets and variables -> Actions` 中配置 `NOTIFY_WEBHOOK` 密钥。

---

## 💻 本地运行与测试

如果你想在本地手动运行或测试代码：

1. **安装依赖项**：
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **运行脚本**：
   ```bash
   python douyin_ai_crawler.py
   ```

3. **查看结果**：
   下载的视频与每日报告将保存在 `downloads/YYYY-MM-DD/` 目录下。

---

## ⚙️ 核心文件说明

- `douyin_ai_crawler.py`: 核心 Python 爬虫与视频下载逻辑。
- `.github/workflows/daily_douyin_ai.yml`: GitHub Actions 线上定时调度配置文件。
- `requirements.txt`: Python 依赖清单。
