# AI Daily — AI 热点日报

每日自动聚合 Hacker News、GitHub Trending、Arxiv AI 论文、36氪 AI 快讯，推送至钉钉群。

## 部署步骤

### 1. 获取钉钉机器人 Webhook
1. 在钉钉群 → 群设置 → 智能群助手 → 添加机器人
2. 选择 **自定义** 机器人，设置名称和头像
3. 复制 Webhook URL

### 2. 配置 GitHub Secret
在 GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret
- **Name**: `DINGTALK_WEBHOOK`
- **Value**: 钉钉机器人 Webhook URL

### 3. 手动触发测试
在 GitHub Actions 页面选择 `AI Daily Push` → Run workflow

### 定时说明
- 默认 `UTC 22:00`（北京时间 `06:00`）执行
- 如需修改，编辑 `.github/workflows/daily.yml` 中的 cron 表达式
