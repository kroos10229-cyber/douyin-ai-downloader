# 🎵 抖音 AI 热门爆款全自动分析与手机微信推送系统

本系统专注于**100% 只搜集抖音 (Douyin) 平台上的 AI / 大模型热门爆款视频**，利用 AI 深度拆解内容，并将【总结分析报告】实时推送到你的手机微信上。

---

## 🌟 核心特性

1. **纯抖音 (Douyin) 目标平台**：所有搜索、筛选与下载完全聚焦于抖音短视频平台。
2. **全网覆盖关键词**：`AI`、`AIGC`、`agent`、`ChatGPT`、`DeepSeek`、`Claude`、`千问`、`Kimi`、`GLM`、`Gemini`、`Grok`、`大模型`。
3. **点赞门槛与数量控制**：优先提取**点赞 >= 3000** 以上的高爆款视频，每日精选 **10 - 20 个** 头部内容。
4. **AI 三维爆款拆解**：
   - 📌 **视频讲的啥**（核心主题与玩法）
   - 💡 **对我有什么借鉴**（爆款亮点与痛点分析）
   - 🚀 **如何去复制**（对标复刻落地方案）
5. **实时微信推送 + 视频云端打包**：报告直接发手机微信，视频存 GitHub 云端随用随取。

---

## 🔐 核心配置：添加 DOUYIN_COOKIE Secrets (10秒搞定)

由于抖音（Douyin）Web 端限制未经登录的海外服务器请求，为了确保 **100% 稳定成功抓取抖音 AI 视频**，只需在 GitHub 添加一次你的 `DOUYIN_COOKIE`：

### 获取 Cookie 步骤：
1. 电脑浏览器打开 [douyin.com](https://www.douyin.com) 并登录你的抖音账号。
2. 按 `F12` 键打开开发者工具，点击 **网络 (Network)** 标签页，按 `F5` 刷新一下页面。
3. 点击左侧列表中任意一个请求（如 `web` 或 `self`），在右侧 **请求头 (Request Headers)** 中找到 `Cookie:`。
4. 复制 `Cookie:` 后面整串长文本。
5. 打开 GitHub 仓库：[https://github.com/kroos10229-cyber/douyin-ai-downloader](https://github.com/kroos10229-cyber/douyin-ai-downloader)
6. 进入 `Settings` -> `Secrets and variables` -> `Actions` -> 点击 `New repository secret`：
   - **Name** 填：`DOUYIN_COOKIE`
   - **Secret** 粘贴刚才复制的 Cookie 文本。
7. 保存即可！
