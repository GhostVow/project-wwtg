# 项目 TODO — 周末搭子 MVP

**最后更新：** 2026-03-17

---

## 本周（3/17 - 3/21）

### Dev — SuperCrew002
- [ ] 技术方案文档更新（成本 < 300/月 + Azure 部署 + review 反馈）
- [ ] LLM Benchmark — DeepSeek V3 vs Qwen-Max（延迟/质量/成本）
- [ ] 小红书数据采集方案调研（生产级方案，参考但不复用 POC skill）

### PM — pm-Octopus
- [x] PRD v1.1 完成并推到 repo
- [x] 爬虫 skill 技术细节同步
- [ ] 跟进 Juanjuan 确认 MVP 里程碑节奏（4 周 or 6 周）

### 需要 Juanjuan 推进
- [ ] 微信小程序认证（W3 内测前必须完成）
- [ ] Azure 资源开通（部署时需要）
- [ ] 高德地图 API Key 注册申请

---

## W1 启动后

### Dev
- [ ] 项目脚手架搭建（FastAPI 后端 + 微信小程序骨架）
- [ ] 数据管线 POC（自研爬虫 + Redis 缓存跑通）
- [ ] 对话状态机 + 意图解析基础实现

### PM
- [ ] 准备内测用户名单（团队 + 10 个种子用户）
- [ ] 内测反馈收集方案

---

## W2

- [ ] 方案生成核心逻辑 + 天气/地图 API 接入
- [ ] 小程序卡片 UI + Streaming 展示
- [ ] 端到端可用验证

## W3

- [ ] 方案详情页 + 拒绝重推 + 埋点接入
- [ ] 内测部署 + 团队试用
- [ ] 收集反馈

## W4

- [ ] Bug 修复 + 性能优化（15 秒目标）
- [ ] 小程序审核 + 正式发布

---

## 决策待定

| 问题 | 状态 | 负责人 |
|------|------|--------|
| MVP 节奏 4 周 or 6 周 | 待 Juanjuan 确认 | Juanjuan |
| LLM 最终选型 | 待 benchmark 结果 | SuperCrew002 |
| 云服务 Azure 具体方案 | 待部署时确定 | SuperCrew002 + Juanjuan |
