# 周末去呀 🎉

对话式 AI 周末出行助手微信小程序。30 秒内根据你的位置、同行人、偏好，生成个性化周末方案。

## 技术栈

- **后端：** FastAPI + Python 3.11
- **LLM：** DeepSeek V3（OpenAI 兼容 API）
- **数据：** PostgreSQL + Redis
- **外部 API：** 高德天气 / 地图、小红书数据采集
- **前端：** 微信小程序
- **部署：** Docker Compose

## 快速开始

### 1. 克隆项目

```bash
git clone git@github.com:steins-z/project-wwtg.git
cd project-wwtg
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入以下 API Key：

| 变量 | 说明 | 必填 | 获取方式 |
|------|------|------|----------|
| `LLM_API_KEY` | DeepSeek API Key | ⚠️ 留空用 mock | [platform.deepseek.com](https://platform.deepseek.com) |
| `WX_APP_ID` | 微信小程序 AppID | 内测可留空 | 微信公众平台 → 开发管理 |
| `WX_APP_SECRET` | 微信小程序 Secret | 内测可留空 | 微信公众平台 → 开发管理 |
| `AMAP_API_KEY` | 高德地图 Web API Key | ⚠️ 留空用 mock | [console.amap.com](https://console.amap.com) |
| `DATABASE_URL` | PostgreSQL 连接串 | Docker 默认值即可 | — |
| `REDIS_URL` | Redis 连接串 | Docker 默认值即可 | — |

> **注意：** 所有 API Key 留空时项目仍可启动，会使用 mock 数据。适合本地开发调试。

### 3. Docker Compose 启动（推荐）

```bash
docker-compose up -d
```

服务启动后：
- 后端 API：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

查看日志：
```bash
docker-compose logs -f backend
```

停止服务：
```bash
docker-compose down
```

### 4. 本地开发（不用 Docker）

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

需要本地运行 PostgreSQL 和 Redis，或修改 `.env` 中的连接串。

### 5. 微信小程序

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 导入 `miniprogram/` 目录
3. 在 `miniprogram/utils/api.js` 或 `app.js` 中配置后端地址
4. 预览 / 真机调试

## 运行测试

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

当前 59 个测试全部通过。

## 项目结构

```
project-wwtg/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI 路由（chat, plan, auth, analytics）
│   │   ├── models/        # Pydantic 模型（schemas）
│   │   ├── services/      # 业务逻辑
│   │   │   ├── crawler/   # 小红书爬虫模块
│   │   │   ├── llm_service.py      # DeepSeek LLM 集成
│   │   │   ├── weather_service.py  # 高德天气
│   │   │   ├── map_service.py      # 高德地图/导航
│   │   │   ├── chat_service.py     # 对话状态机
│   │   │   ├── plan_service.py     # 方案生成
│   │   │   ├── data_service.py     # 数据管线
│   │   │   └── analytics.py        # 埋点服务
│   │   ├── pipeline/      # 每日数据采集任务
│   │   ├── middleware.py   # 请求日志 + 错误处理
│   │   ├── config.py      # 配置（pydantic-settings）
│   │   └── main.py        # FastAPI 入口
│   ├── scripts/
│   │   └── start.sh       # Docker 启动脚本
│   ├── tests/             # pytest 测试
│   ├── .env.example       # 环境变量模板
│   └── requirements.txt
├── miniprogram/           # 微信小程序
│   ├── pages/
│   │   ├── index/         # 对话主页
│   │   └── plan-detail/   # 方案详情页
│   ├── components/
│   │   └── plan-card/     # 方案卡片组件
│   └── utils/
│       └── api.js         # API 客户端
├── docker-compose.yml
└── docs/                  # PRD、技术设计、部署指南
```

## 每日数据采集

小红书 POI 数据定时采集（需配置 Cookie）：

```bash
cd backend
python -m app.pipeline.daily_runner
```

⚠️ 首次运行前需要手动获取小红书 Cookie（扫码登录），Cookie 过期时会有 WARNING 日志提示。

## 上线前 Checklist

- [ ] 填入所有真实 API Key
- [ ] 接入微信真实登录（当前为 stub）
- [ ] ICP 备案
- [ ] 小红书 Cookie 配置 + 过期告警通知渠道
- [ ] Azure Container Apps 部署（参考 `docs/azure-setup-guide.md`）
