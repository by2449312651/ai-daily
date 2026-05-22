# AI Daily — AI 热点日报

每日自动聚合 Hacker News、GitHub Trending、Arxiv AI 论文、36氪 AI 快讯，推送至飞书。

## 部署步骤

### 1. 推送代码到 GitHub
```bash
cd ai-daily
git init
git add .
git commit -m "init ai daily"
# 在 GitHub 新建仓库后：
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

### 2. 配置飞书 Webhook
1. 在飞书群聊中添加机器人 → 获取 Webhook URL
2. 在 GitHub 仓库 → Settings → Secrets and variables → Actions
3. 添加仓库 Secret: 名称 `FEISHU_WEBHOOK`，值为 Webhook URL

### 3. 手动触发测试
在 GitHub Actions 页面选择 `AI Daily Push` → Run workflow

### 定时说明
- 默认 `UTC 22:00`（北京时间 `06:00`）执行
- 如需修改，编辑 `.github/workflows/daily.yml` 中的 cron 表达式
