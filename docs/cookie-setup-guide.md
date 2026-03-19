# 小红书 Cookies 配置指南

## 为什么需要 Cookies？

爬虫需要登录态才能搜索小红书笔记。没有有效 cookies，`daily_runner` 会跳过爬取，方案全靠 LLM 编（Plan B 模式）。

## 获取步骤

### 1. 浏览器登录小红书

1. 用 Chrome 打开 https://www.xiaohongshu.com
2. 登录你的小红书账号
3. 确认能正常浏览笔记

### 2. 导出 Cookies

**方法 A：用浏览器扩展（推荐）**

安装 [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg) 或 [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)：

1. 在小红书页面点击扩展图标
2. 点「Export」→ 选「JSON」格式
3. 复制导出的 JSON

**方法 B：手动从 DevTools 导出**

1. F12 打开开发者工具
2. Application → Cookies → `https://www.xiaohongshu.com`
3. 手动整理成 JSON 数组格式（见下方格式要求）

### 3. 保存文件

创建文件 `backend/data/cookies/cookies.json`，内容格式：

```json
{
  "cookies": [
    {
      "name": "web_session",
      "value": "xxxxxx",
      "domain": ".xiaohongshu.com",
      "path": "/"
    },
    {
      "name": "a1",
      "value": "xxxxxx",
      "domain": ".xiaohongshu.com",
      "path": "/"
    }
  ],
  "saved_at": 1773912000
}
```

**关键 cookies（必须包含）：**
- `web_session` — 登录凭证
- `a1` — 设备标识

其他 cookies 也一并导出即可，格式为 Playwright cookie 格式（包含 `name`, `value`, `domain`, `path`）。

### 4. Docker 环境

`docker-compose.yml` 已经配了 volume mount：

```yaml
volumes:
  - ./backend/data/cookies:/data/cookies
```

所以文件放在 `backend/data/cookies/cookies.json` 就行，容器内会映射到 `/data/cookies/cookies.json`。

## 运行爬虫

Cookies 配好后，手动跑一次数据管道：

```bash
docker-compose exec api python -m app.pipeline.daily_runner
```

正常输出：
```
=== Daily Pipeline Start ===
✅ Redis connected
✅ Cookies loaded (N cookies)
🔍 Crawling 苏州...
🔍 Crawling 上海...
🔍 Crawling 杭州...
✅ Extracted X POIs
✅ Saved to database
=== Daily Pipeline Complete ===
```

如果看到 `⚠️ No XHS cookies found`，检查文件路径和格式。

## 注意事项

- **Cookies 有效期**：通常 7-30 天，过期后需要重新登录导出
- **频率限制**：爬虫内置了随机延迟，一般不会触发风控
- **不要分享 cookies**：包含你的登录信息，不要提交到 git
- `cookies.json` 已经在 `.gitignore` 中
