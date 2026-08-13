# 抖音 AI / 大模型热门爆款全自动分析与手机推送系统

本系统专注于**每日自动搜集抖音上的 AI / 大模型热门爆款视频**，利用 AI 深度拆解内容，并将【总结分析报告】实时推送到你的手机微信上。同时视频文件将在云端暂存打包，方便你有需要时随时去云端下载。

---

## 🔥 升级特性

1. **全网覆盖关键词**：
   - 搜集关键词：`AI`、`AIGC`、`agent`、`ChatGPT`、`DeepSeek`、`Claude`、`千问`、`Kimi`、`GLM`、`Gemini`、`Grok`、`大模型` 等。
2. **严格筛选质量标准**：
   - 优先提取**点赞量 >= 3000** 以上的高爆款视频。
   - 每日精选控制在 **10 - 20 个** 最具代表性的头部内容。
3. **AI 深度三大维度拆解**：
   对于每一个精选视频，自动生成三大核心指标：
   - 📌 **视频讲的啥**（核心主题与玩法解析）
   - 💡 **对我有什么借鉴**（爆款逻辑与痛点分析）
   - 🚀 **如何去复制**（对标复刻落地方案）
4. **实时手机端微信推送**：
   - 抓取分析完成后，**总结报告自动推送到手机微信**，躺着就能看今日 AI 爆款趋势。
   - 视频文件在 GitHub 云端保存（保留 7 天），不占用手机内存，有需要随时在 GitHub 网页上一键下载 Zip。

---

## 📱 如何开启手机微信推送？（1分钟搞定）

系统支持 **PushPlus（推荐，完全免费）** 或 **Server酱** 进行微信公众号消息一对一实时推送：

### 推荐方案：使用 PushPlus（微信扫码即用）
1. 微信搜索关注公众号 **PushPlus (推送加)**，登录后在个人中心复制你的 **Token**。
2. 打开 GitHub 仓库：`https://github.com/kroos10229-cyber/douyin-ai-downloader`
3. 进入 `Settings` -> `Secrets and variables` -> `Actions` -> 点击 `New repository secret`。
4. **Name** 填 `PUSHPLUS_TOKEN`，**Secret** 粘贴刚才复制的 Token，点击保存。
5. 完成！之后每天早上 08:00 AM，总结报告就会自动推送到你的微信上！

---

## ⚙️ 核心源码结构

- [douyin_ai_crawler.py](file:///Users/kroos/Documents/Gemini/AI工作区/自动化任务/douyin_ai_crawler.py)：包含多关键词抓取、高点赞筛选、AI 3维拆解引擎与手机端推送逻辑。
- [.github/workflows/daily_douyin_ai.yml](file:///Users/kroos/Documents/Gemini/AI工作区/自动化任务/.github/workflows/daily_douyin_ai.yml)：GitHub Actions 云端定时器与密钥联动。
