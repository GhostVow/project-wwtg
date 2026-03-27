# 周末去呀 🎉

对话式 AI 周末出行助手。30 秒内根据你的位置、同行人、偏好，生成个性化周末方案。

> **当前状态：** MVP Demo（苏州 92 个真实 POI，数据来源小红书 + 高德验证）

## 🚀 本地 Demo 体验（5 分钟）

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 已安装并运行
- [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 已安装
- Git

### Step 1 — 拉取代码

```bash
git clone https://github.com/GhostVow/project-wwtg.git
cd project-wwtg
git checkout feat/wwtg/dev-m14
```

### Step 2 — 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入：

| 变量 | 说明 | 必填 | 获取方式 |
|------|------|------|----------|
| `LLM_API_KEY` | 通义千问 API Key | ✅ | [DashScope 控制台](https://dashscope.console.aliyun.com/) |
| `LLM_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | ✅ | 固定值 |
| `LLM_MODEL` | `qwen-plus` | ✅ | 固定值 |
| `LLM_TIMEOUT` | `90` | 建议填 | LLM 超时秒数 |
| `AMAP_API_KEY` | 高德地图 Web API Key | 可选 | [高德开放平台](https://console.amap.com) |

> **没有 API Key？** 联系项目成员获取。不要在群聊/公开渠道分享 Key。

### Step 3 — 启动服务

```bash
docker-compose up -d --build
```

等待 1-2 分钟，三个容器启动（api + redis + postgres）。

验证：
```bash
curl http://localhost:8000/health
# 返回 {"status":"ok"} 即成功
```

### Step 4 — 导入 Demo 数据

```bash
./scripts/seed_data.sh
```

3 秒完成，写入 92 个苏州真实 POI 到 Redis。

### Step 5 — 打开小程序

1. 微信开发者工具 → **导入项目** → 选择 `miniprogram/` 目录
2. AppID 选「测试号」即可
3. **设置 → 项目设置 → 勾选「不校验合法域名」**（否则 localhost 请求会被拦截）
4. 在模拟器中输入需求，开始体验！

### 试试这些场景 🎯

| 输入 | 预期效果 |
|------|----------|
| 苏州带小孩周末去哪，预算200以内 | 亲子方案，太湖/博物馆路线 |
| 苏州情侣约会，想安静文艺一点 | 平江路/三山岛等文艺路线 |
| 一个人想在苏州 citywalk | 古巷/园林步行路线 |
| 4个人去苏州，人均预算100 | 多人友好、性价比路线 |
| 苏州下雨天能去哪玩 | 室内为主（博物馆/商圈/咖啡馆）|

每个方案可以点击查看详情：停留点、时间安排、导航链接、贴心提示。

不满意可以说「换一个」或提出新偏好，会重新推荐。

---

## 技术栈

- **后端：** FastAPI + Python 3.11
- **LLM：** Qwen Plus（通义千问，DashScope OpenAI 兼容 API）
- **数据：** PostgreSQL + Redis（AOF 持久化）
- **数据来源：** 小红书笔记 → LLM 提取 POI → 高德 API 验证
- **外部 API：** 高德天气 / 地图 / POI 搜索
- **前端：** 微信小程序
- **部署：** Docker Compose

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/message` | 对话（发送需求，返回方案卡片）|
| GET | `/api/v1/plan/detail/{plan_id}` | 方案详情（停留点、导航、tips）|
| POST | `/api/v1/plan/select` | 选择方案 |
| POST | `/api/v1/plan/reject` | 拒绝并重新推荐 |
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |

## 项目结构

```
project-wwtg/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI 路由（chat, plan, auth）
│   │   ├── models/        # Pydantic 模型
│   │   ├── services/      # 业务逻辑
│   │   │   ├── llm_service.py      # LLM 集成
│   │   │   ├── chat_service.py     # 对话状态机
│   │   │   ├── plan_service.py     # 方案生成
│   │   │   ├── data_service.py     # 数据管线 + POI 提取
│   │   │   ├── weather_service.py  # 高德天气
│   │   │   └── map_service.py      # 高德地图/导航
│   │   ├── pipeline/      # 数据导入脚本
│   │   └── main.py        # FastAPI 入口
│   ├── tests/             # pytest 测试
│   └── .env.example       # 环境变量模板
├── miniprogram/           # 微信小程序前端
│   ├── pages/
│   │   ├── index/         # 对话主页
│   │   └── plan-detail/   # 方案详情页
│   └── components/
│       └── plan-card/     # 方案卡片组件
├── data/seed/             # Demo 种子数据
├── scripts/               # 工具脚本（seed_data.sh 等）
├── docker-compose.yml
└── docs/                  # PRD、技术文档
```

## 数据管线

小红书笔记 → LLM 提取真实 POI → 高德 API 验证 → 写入 Redis

```bash
# 导入笔记并提取 POI（需 LLM API Key）
docker-compose exec api python -m app.pipeline.import_notes /data/seed/suzhou.json --city 苏州

# 快速导入已提取的 POI（无需 LLM，3 秒）
./scripts/seed_data.sh
```

## 运行测试

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `curl http://localhost:8000/health` 无响应 | 检查 Docker 是否运行：`docker-compose ps` |
| 小程序请求失败 | 确认勾选了「不校验合法域名」 |
| 推荐结果为空 | 运行 `./scripts/seed_data.sh` 导入数据 |
| LLM 超时 | 检查 `LLM_API_KEY` 是否正确，网络是否通 |

## 上线 Checklist

- [ ] 微信小程序认证 + 真实 AppID
- [ ] ICP 备案
- [ ] Azure Container Apps 部署
- [ ] 上海 + 杭州数据补全
- [ ] 小红书 Cookie 定时刷新
