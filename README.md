# 🎵 抖音 AI 热门爆款调研与创作者 1:1 复刻系统

本系统专注于**抖音 (Douyin) 平台上的 AI / 大模型热门爆款视频与搜索趋势调研**，通过动态捕获实时热搜词、筛选高收藏高互动干货视频，并利用 AI 深度输出【创作者 1:1 分镜头脚本复刻指南】，每日自动将决策报告推送到你的手机微信。

---

## 🌟 核心升级与特性

1. **🔥 今日 AI 实时热搜词动态发现**：
   - 自动探测抖音当下搜索联想与飙升词（如：`DeepSeek本地部署`、`AI一键生成PPT`、`智能体副业`），精准掌握用户每天在搜什么。
2. **📊 爆款价值综合指数（加权高收藏干货）**：
   - 采用 `爆款得分 = 点赞 * 1.0 + 收藏 * 3.5 + 评论 * 2.5` 智能排序。
   - 自动标记 **⭐ 高收藏干货（收藏率 > 25%）** 与 **💬 高互动热议**，告别虚高流量，专抓高变现高实用选题。
3. **🎬 创作者实战 1:1 拆解（直接照着拍）**：
   - 🎯 **爆款属性定位**：受众画像与痛点切入。
   - ⏱️ **黄金前 3 秒钩子**：直接给出开场第 1 句台词 + 视觉冲击卡点设计。
   - 🎬 **四段式复刻脚本**：`0-5s 痛点/成果` $\rightarrow$ `5-25s 工具实操` $\rightarrow$ `25-45s 效率避坑` $\rightarrow$ `45-60s 转化引导`。
   - 💬 **评论区引流话术**：置顶话术与引导粉丝扣 1 留资转化技巧。
4. **📱 手机微信单条全景推送 + 本地 Markdown 报告**：
   - 每天早晨自动整理为全景排版卡片推送到微信（支持 PushPlus / Server酱），并归档高清 Markdown 与 JSON 元数据。

---

## 🔐 核心配置：添加 DOUYIN_COOKIE Secrets (10秒搞定)

由于抖音 Web 端限制海外服务器未登录请求，为了确保 **100% 稳定成功抓取抖音数据**，只需在 GitHub 添加一次你的 `DOUYIN_COOKIE`：

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

