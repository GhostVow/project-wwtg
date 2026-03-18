# 周末搭子 — 小程序前端

WeChat Mini Program for 周末搭子.

## Structure

- `pages/index` — 主聊天页面
- `pages/plan-detail` — 方案详情
- `pages/profile` — 个人中心
- `components/plan-card` — 方案卡片组件
- `utils/api.js` — API 客户端（W1 含 mock 模式）

## Development

1. 使用微信开发者工具导入本目录
2. `project.config.json` 中 appid 为占位符，需替换为真实 appid
3. W1 默认 mock 模式，不需要后端

## W1 Mock Mode

`app.js` 中 `globalData.mockMode = true` 时，所有 API 调用返回本地 mock 数据。
