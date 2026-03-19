// pages/index/index.js — 主聊天页面
const api = require('../../utils/api');

Page({
  data: {
    messages: [],
    inputValue: '',
    scrollToView: '',
    loading: false,
    loadingText: '思考中...',
    sessionId: null,
  },

  onLoad() {
    this.addMessage('assistant', '你好！我是周末搭子 🎉\n告诉我你想在哪个城市玩？和谁一起？有什么特殊需求吗？');
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value });
  },

  /**
   * Unified send: all messages go through this single path.
   * @param {string} message - user message text
   */
  async sendMessage(message) {
    if (!message || this.data.loading) return;

    this.setData({ loading: true, loadingText: '正在了解你的需求…' });

    // Staged loading text (pure frontend timer, no backend dependency)
    this._loadingTimer1 = setTimeout(() => {
      if (this.data.loading) this.setData({ loadingText: '查看天气和热门玩法…' });
    }, 3000);
    this._loadingTimer2 = setTimeout(() => {
      if (this.data.loading) this.setData({ loadingText: '方案生成中，马上好…' });
    }, 8000);

    try {
      const res = await api.sendChatMessage(message);
      const app = getApp();

      if (res.session_id) {
        this.setData({ sessionId: res.session_id });
        app.globalData.sessionId = res.session_id;
      }

      this._handleResponse(res);
    } catch (err) {
      this.addMessage('assistant', '网络出了点问题，请稍后重试 😅');
      console.error('Chat error:', err);
    }

    clearTimeout(this._loadingTimer1);
    clearTimeout(this._loadingTimer2);
    this.setData({ loading: false });
  },

  /** Called from input box send button. */
  onSend() {
    const message = this.data.inputValue.trim();
    if (!message) return;

    this.addMessage('user', message);
    this.setData({ inputValue: '' });
    this.sendMessage(message);
  },

  _handleResponse(res) {
    if (res.plans && res.plans.length > 0) {
      this.addMessage('assistant', res.reply || '为您找到以下方案：');
      res.plans.forEach((plan) => {
        this.addMessage('plan_card', plan);
      });
      this.addMessage('actions', {
        options: [
          { key: 'select_a', label: '就选A' },
          { key: 'select_b', label: '就选B' },
          { key: 'reject', label: '都不喜欢，换一批' },
        ]
      });
    } else if (res.reply) {
      this.addMessage('assistant', res.reply);
    }
  },

  addMessage(role, content) {
    const messages = this.data.messages;
    const id = 'msg-' + messages.length;
    messages.push({ id, role, content, time: new Date().toLocaleTimeString() });
    this.setData({ messages, scrollToView: id });
  },

  onPlanTap(e) {
    const planId = e.currentTarget.dataset.planId || (e.detail && e.detail.planId);
    if (planId) {
      wx.navigateTo({
        url: '/pages/plan-detail/plan-detail?id=' + planId,
      });
    }
  },

  async onActionTap(e) {
    const action = e.currentTarget.dataset.action;
    if (action === 'select_a' || action === 'select_b') {
      const label = action === 'select_a' ? '就选A' : '就选B';
      this.addMessage('user', label);

      // Find the selected plan from messages
      const planMessages = this.data.messages.filter(m => m.role === 'plan_card');
      const planIndex = action === 'select_a' ? 0 : 1;
      const plan = planMessages.length > planIndex ? planMessages[planMessages.length - (2 - planIndex)] : null;
      const planId = plan ? plan.content.plan_id : null;
      const sessionId = this.data.sessionId;

      if (planId && sessionId) {
        api.selectPlan(planId, sessionId).catch(err => console.error('selectPlan failed:', err));
        api.trackEvent('plan_selected', { plan_id: planId });
      }

      this.addMessage('assistant', '好的，方案已选择！祝你周末愉快 🎉');
    } else if (action === 'reject') {
      this.addMessage('user', '都不喜欢，换一批');

      // Find the most recent plan cards and reject them via API
      const planMessages = this.data.messages.filter(m => m.role === 'plan_card');
      const sessionId = this.data.sessionId;
      if (planMessages.length > 0 && sessionId) {
        const latestPlan = planMessages[planMessages.length - 1];
        const planId = latestPlan.content.plan_id;
        if (planId) {
          api.rejectPlan(planId, sessionId).catch(err => console.error('rejectPlan failed:', err));
          api.trackEvent('plan_rejected', { plan_id: planId });
        }
      }

      this.sendMessage('都不喜欢，换一批');
    }
  },
});
