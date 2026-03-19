# 技术方案：周末搭子 MVP

**版本：** v1.0  
**作者：** SuperCrew002  
**日期：** 2026-03-17  
**基于：** PRD v1.1  
**状态：** Approved - LLM 默认 DeepSeek V3，benchmark 出来做 delta 调整

---

## 一、架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    微信小程序（前端）                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ 对话界面  │  │ 方案卡片  │  │ 路线详情  │  │ 分享页面 │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
└───────┼──────────────┼──────────────┼──────────────┼─────┘
        │              │              │              │
        └──────────────┴──────┬───────┴──────────────┘
                              │ HTTPS / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────┐
│                   API Gateway (Nginx)                    │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│              后端服务 (FastAPI / Python 3.11+)            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Chat Service  │  │ Plan Service │  │ Data Service  │  │
│  │ (对话管理)    │  │ (方案生成)    │  │ (数据管线)    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│  ┌──────┴─────────────────┴───────────────────┴───────┐  │
│  │              Orchestrator (编排层)                   │  │
│  │  并行调度：LLM + 天气 + POI 缓存 + 地理编码           │  │
│  └────────────────────────┬───────────────────────────┘  │
└───────────────────────────┼──────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │  Redis        │ │  PostgreSQL  │ │  外部 API     │
   │  (缓存/会话)  │ │  (持久化)    │ │  (天气/地图)  │
   └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 二、技术选型

| 层次 | 选型 | 理由 |
|------|------|------|
| **前端** | 微信小程序 (WXML + WXSS + JS/TS) | PRD 决议，微信生态获客容易 |
| **后端框架** | FastAPI (Python 3.11+) | 原生 async，适合 I/O 密集型并行调用 |
| **LLM** | DeepSeek V3 / Qwen-Max（待 benchmark） | 国内延迟低，成本友好；GPT-4 做 fallback |
| **缓存** | Redis 7.x | 会话状态 + POI 缓存 + 限流 |
| **数据库** | PostgreSQL 16 | 用户数据 + 埋点 + 方案历史 |
| **消息队列** | Redis Stream（MVP 够用） | 异步任务（数据管线、推送），MVP 不上 Kafka |
| **部署** | Azure Container Apps + Docker | 按用量计费，低流量成本低；Juanjuan 有 Azure 账号 |
| **CI/CD** | GitHub Actions | 与 repo 一体化 |

---

## 三、核心模块设计

### 3.1 Chat Service（对话管理）

**职责：** 管理对话状态，解析用户意图，决定下一步动作

```python
# 对话状态机
class ConversationState(Enum):
    INIT = "init"              # 用户刚发起
    COLLECTING = "collecting"  # 收集信息中
    GENERATING = "generating"  # 生成方案中
    PRESENTING = "presenting"  # 展示方案
    DETAIL = "detail"          # 查看详情
    REJECTING = "rejecting"    # 用户拒绝，收集原因
    IDLE = "idle"              # 闲聊/非出行意图

# 用户上下文
class UserContext:
    city: str | None           # 城市（必须）
    people_count: int = 2      # 人数，默认2
    companion_type: str | None # 同行人类型（独自/情侣/亲子/朋友）
    energy_level: str = "medium"  # 精力（high/medium/low）
    constraints: list[str] = []   # 特殊限制（孕妇/轮椅/老人）
    preferences: list[str] = []   # 偏好关键词
    rejection_reasons: list[str] = []  # 历史拒绝原因
```

**意图解析：** 用 LLM 从用户一句话中提取多个字段，减少提问轮次

```
输入: "苏州，和老公，我是孕妇不能去人太多的地方"
输出: {city: "苏州", people_count: 2, companion_type: "情侣", 
       constraints: ["孕妇"], preferences: ["人少"]}
→ 全部字段已知，跳过提问，直接生成
```

### 3.2 Plan Service（方案生成）

**职责：** 编排多个数据源，并行生成 2 个方案

**15 秒时序设计：**

```
T+0s ──── 收到生成请求
  │
  ├── 并行发起 ─────────────────────────────────
  │   ├── [1] Redis 查 POI 缓存（城市+标签）   ~50ms
  │   ├── [2] 天气 API 查询                     ~1-2s
  │   └── [3] 地理编码（如需）                   ~500ms
  │
T+2s ──── 数据就绪，组装 Prompt
  │
  ├── 并行生成 ─────────────────────────────────
  │   ├── [4] LLM 生成方案 A（streaming）       ~5-8s
  │   └── [5] LLM 生成方案 B（streaming）       ~5-8s
  │
T+10s ─── 方案生成完毕
  │
  ├── [6] 结构化解析 + 导航链接拼接              ~500ms
  │
T+11s ─── 返回前端（streaming 可更早展示）
```

**Prompt 设计要点：**
- 输出限制 500 token/方案，控制生成时间
- 要求 JSON 格式输出，便于结构化解析
- 注入天气信息、用户约束、已拒绝方案（避免重复推荐）
- 两个方案差异化：一动一静 / 一远一近 / 一免费一消费

### 3.3 Data Service（数据管线）

**职责：** 管理小红书 POI 数据的采集和缓存

**每日数据管线：**

```
┌──────────────────────────────────────────────────┐
│             定时任务（每日凌晨 3:00）              │
│                                                   │
│  for city in [苏州, 上海, 杭州]:                   │
│    for keyword in [周末去哪玩, 周末一日游, ...]:    │
│      1. Playwright 抓取 Top 20 帖子               │
│      2. 提取：标题、正文、点赞数、评论精选          │
│      3. LLM 结构化提取 POI 信息：                  │
│         - 地点名称、地址、特色                      │
│         - 适合人群标签                             │
│         - 花费区间                                 │
│         - 路线组合建议                             │
│      4. 写入 Redis 缓存 + PostgreSQL 持久化        │
│                                                   │
│  缓存结构：                                       │
│    key: poi:{city}:{tag}                           │
│    value: [POI 列表, 按热度排序]                   │
│    TTL: 48h（允许隔天仍可用）                      │
└──────────────────────────────────────────────────┘
```

**反爬策略：**
- 多账号轮换（3-5 个号）
- 请求间隔随机 5-15 秒
- 每日每城市控制总请求量 < 200
- Playwright 指纹随机化（UA、viewport、语言）
- **Plan B：** 爬虫完全失败时，使用 LLM 通用知识生成推荐（标记为"AI 推荐"而非"小红书热门"）

---

## 四、API 设计

### 4.1 核心接口

```
POST   /api/v1/chat/message        # 发送消息（SSE streaming 响应）
GET    /api/v1/chat/history/{sid}   # 获取对话历史
POST   /api/v1/plan/select          # 用户选择方案
POST   /api/v1/plan/reject          # 用户拒绝方案
GET    /api/v1/plan/detail/{pid}    # 获取方案详情
POST   /api/v1/auth/wx-login        # 微信登录
```

### 4.2 消息接口详细设计

**请求：**
```json
POST /api/v1/chat/message
{
  "session_id": "uuid",
  "message": "苏州，和老公，我是孕妇",
  "wx_user_id": "openid"
}
```

**SSE 响应（streaming）：**
```
event: thinking
data: {"status": "querying_weather"}

event: thinking  
data: {"status": "generating_plans"}

event: plan_card
data: {
  "plan_id": "uuid",
  "title": "双塔市集赏花散步",
  "description": "玉兰花季，吃喝逛一条线",
  "emoji": "🌸",
  "duration": "半天（3-4小时）",
  "cost_range": "50元以内",
  "transport": "地铁+步行",
  "tags": ["孕妇友好", "人少", "免费", "有餐饮"],
  "stops_count": 4,
  "source_count": 3
}

event: plan_card
data: { ... 方案B ... }

event: actions
data: {"options": ["select_a", "select_b", "reject"]}

event: done
data: {}
```

### 4.3 方案详情接口

**响应：**
```json
GET /api/v1/plan/detail/{plan_id}
{
  "plan_id": "uuid",
  "title": "双塔市集赏花散步",
  "stops": [
    {
      "name": "双塔市集",
      "arrive_at": "10:00",
      "stay_duration": "30-45分钟",
      "recommendation": "老客满蛋饼 + 冰豆浆",
      "nav_link": "https://uri.amap.com/marker?...",
      "walk_to_next": "240m, 约3分钟"
    }
  ],
  "tips": [
    "明天 7-15°C 多云，建议穿薄外套",
    "全程步行约 1.6km，平路为主"
  ],
  "sources": [
    {"title": "苏州赏花路线", "likes": 2340, "url": "https://..."}
  ]
}
```

---

## 五、数据库设计

### 5.1 核心表

```sql
-- 用户表
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wx_openid   VARCHAR(64) UNIQUE NOT NULL,
    wx_nickname VARCHAR(64),
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- 会话表
CREATE TABLE sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    city        VARCHAR(32),
    context     JSONB,          -- UserContext 完整快照
    state       VARCHAR(32) DEFAULT 'init',
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- 消息表
CREATE TABLE messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES sessions(id),
    role        VARCHAR(16) NOT NULL,  -- user / assistant
    content     TEXT NOT NULL,
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 方案表
CREATE TABLE plans (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES sessions(id),
    title       VARCHAR(128) NOT NULL,
    description TEXT,
    card_data   JSONB NOT NULL,   -- 完整方案卡片结构化数据
    status      VARCHAR(16) DEFAULT 'presented',  -- presented / selected / rejected
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- POI 缓存表（持久化备份）
CREATE TABLE poi_cache (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city        VARCHAR(32) NOT NULL,
    tags        TEXT[] NOT NULL,
    poi_data    JSONB NOT NULL,
    source_url  VARCHAR(512),
    source_likes INT,
    fetched_at  TIMESTAMPTZ DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL
);

-- 埋点事件表
CREATE TABLE events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    session_id  UUID REFERENCES sessions(id),
    event_type  VARCHAR(64) NOT NULL,  -- card_impression / select / expand / timeout_leave / reject
    event_data  JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 索引
CREATE INDEX idx_sessions_user ON sessions(user_id, created_at DESC);
CREATE INDEX idx_poi_city_tags ON poi_cache(city, tags) WHERE expires_at > now();
CREATE INDEX idx_events_type ON events(event_type, created_at DESC);
```

---

## 六、小程序前端设计

### 6.1 页面结构

```
pages/
├── index/          # 首页（对话界面）
├── plan-detail/    # 方案详情页（路线 + 站点 + Tips）
├── share-card/     # 分享卡片生成页（P1）
└── profile/        # 个人页（历史方案）
```

### 6.2 关键交互

- **对话气泡 + 卡片混排：** 消息流中嵌入方案卡片组件
- **Streaming 展示：** 通过 SSE 逐步渲染"正在查天气…""正在生成方案…"
- **卡片动画：** 方案卡片从底部滑入，点击展开详情
- **导航跳转：** 调用 `wx.openLocation()` 或跳转高德/百度地图小程序
- **分享：** 调用 `wx.shareAppMessage()` 生成带方案摘要的分享卡片

---

## 七、部署架构（MVP）

```
┌─────────────────────────────────────┐
│      Azure Container Apps            │
│                                      │
│   ├── api (FastAPI × 2 replicas)     │
│   ├── data-pipeline (定时任务)       │
│                                      │
│   外部托管服务：                      │
│   ├── Azure Cache for Redis          │
│   ├── Azure Database for PostgreSQL  │
│   └── Nginx (或 Azure 内置 Ingress)  │
└─────────────────────────────────────┘
```

**MVP 成本估算（目标 < 300 元/月）：**

| 项目 | 方案 | 预估费用 |
|------|------|---------|
| 云服务器 | Azure Container Apps（按用量计费，低流量接近零成本）| ~60 元/月 |
| LLM API | DeepSeek V3（成本约 GPT 的 1/10），严格控制 500 token/方案 | ~100-200 元/月 |
| 地图 API | 高德（每日 5000 次免费额度，MVP 日活 100 人足够）| 免费 |
| 天气 API | wttr.in 免费 / 和风天气免费额度 | 免费 |
| 域名 + SSL | Azure 提供免费 SSL | ~50 元/年 |
| **合计** | | **< 300 元/月** |

**省钱关键：**
1. 热门方案缓存复用（减少 LLM 调用，提高缓存命中率）
2. DeepSeek V3 低成本 + 500 token 上限控制
3. Azure 免费额度 / 按用量计费

---

## 八、排期计划

| 阶段 | 时间 | 任务 | 产出 |
|------|------|------|------|
| **W1** | 第1周 | 项目脚手架搭建 + 对话流基础实现 | FastAPI 骨架 + 小程序对话页 + 意图解析 |
| **W1** | 第1周 | 数据管线 POC | Playwright 爬虫验证 + Redis 缓存跑通 |
| **W2** | 第2周 | 方案生成核心逻辑 + 天气/地图接入 | 端到端可用：输入 → 2个方案卡片 |
| **W2** | 第2周 | 小程序卡片 UI + Streaming 展示 | 方案卡片渲染 + 加载动画 |
| **W3** | 第3周 | 方案详情页 + 拒绝重推 + 埋点 | 完整闭环可用 |
| **W3** | 第3周 | 内测部署 + 团队试用 | Docker Compose 上线 |
| **W4** | 第4周 | Bug 修复 + 性能优化 + 正式发布 | 15秒目标达成 + 小程序审核上线 |

---

## 九、风险与技术对策

| 风险 | 对策 |
|------|------|
| LLM 生成超时（>10s） | streaming 输出 + 超时降级为更短的方案 |
| LLM 输出格式不稳定 | JSON Schema 约束 + 解析重试（最多 2 次） |
| 小红书反爬升级 | 多层缓存（Redis 48h + PG 永久）确保有数据可用 |
| 微信小程序审核不通过 | 内容安全过滤（LLM 输出前检查敏感词） |
| 并发量超预期 | FastAPI 2 worker + Redis 限流，初期够用 |
| 方案质量差 | 人工标注种子方案作为 few-shot 示例 |

---

## 十、已确认决策 & 开放问题

### ✅ 已确认
| 决策 | 结论 | 日期 |
|------|------|------|
| 云服务 | Azure（Juanjuan 有账号） | 2026-03-17 |
| 地图 API | 高德地图（免费额度，文档友好） | 2026-03-17 |
| 成本目标 | < 300 元/月 | 2026-03-17 |
| 数据管线方案 | 自研生产级爬虫（参考 POC skill 思路，不直接复用） | 2026-03-17 |
| 埋点 event_type | 改用 PG ENUM 类型，防止脏数据 | 2026-03-17 |
| 方案数据来源标记 | 前端卡片区分 "📕 小红书热门" vs "🤖 AI 推荐"（Plan B 场景）| 2026-03-17 |
| 拒绝历史排除 | Prompt 注入 rejection_reasons 反向排除已拒绝方案 | 2026-03-17 |

### ⏳ 待确认
1. **LLM Benchmark 结果：** DeepSeek V3 vs Qwen-Max 对比（延迟 + 输出质量 + 成本），本周出结果
2. **微信小程序认证：** 需要 Juanjuan 启动申请流程，W3 内测前必须完成
3. **MVP 里程碑节奏：** 4 周 or 6 周，待 Juanjuan 确认

---

**下一步：** 评审通过后，W1 开始动工 🚀

---

## Implementation Status (as of M11)

| Module | Status | Notes |
|--------|--------|-------|
| FastAPI backend scaffold | ✅ Done | Project structure, config, routing |
| Conversation state machine | ✅ Done | Intent extraction, multi-field parsing |
| Data pipeline POC | ✅ Done | Playwright scraper + Redis cache |
| Plan generation (LLM orchestrator) | ✅ Done | Parallel weather/POI fetch + dual-plan generation |
| Weather & map API integration | ✅ Done | wttr.in + 高德 geocoding |
| Mini program chat UI | ✅ Done | Message bubbles + plan card components |
| Plan card rendering | ✅ Done | Sync JSON response + loading animation (no SSE) |
| Plan detail page | ✅ Done | Route stops, tips, navigation links |
| Reject / re-push flow | ✅ Done | Backend reject API + frontend handler (M11 fix) |
| Analytics event tracking | ✅ Done | select, reject, card_impression events |
| CI/CD pipeline | ✅ Done | GitHub Actions: test + lint (M11) |
| SSE streaming | ⏸ Deferred | MVP uses sync JSON + loading animation; SSE deferred post-MVP |
| Share card generation | ❌ Pending | P1 feature, not in MVP scope |
| Production deployment (Azure) | ❌ Pending | Awaiting Azure resource provisioning |
| 小红书 production scraper | ❌ Pending | POC done; production anti-ban strategy TBD |
| Performance optimization (15s target) | ❌ Pending | W4 task |
