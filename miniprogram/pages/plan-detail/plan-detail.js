// pages/plan-detail/plan-detail.js — 方案详情页
const api = require('../../utils/api');

Page({
  data: {
    plan: null,
    loading: true,
  },

  onLoad(options) {
    const planId = options.id;
    if (planId) {
      this.loadPlanDetail(planId);
    }
  },

  async loadPlanDetail(planId) {
    try {
      const plan = await api.getPlanDetail(planId);
      this.setData({ plan, loading: false });
    } catch (err) {
      console.error('Failed to load plan:', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  /**
   * Track a navigation button tap via the analytics endpoint.
   * Sends event=navigation_clicked with plan_id and stop_name in properties.
   */
  trackNavClick(stopName) {
    const plan = this.data.plan;
    api.trackEvent('navigation_clicked', {
      plan_id: plan ? plan.plan_id : '',
      stop_name: stopName || '',
    });
  },

  onNavigate(e) {
    const { name, navLink } = e.currentTarget.dataset;

    // Track navigation click
    this.trackNavClick(name);

    // Try to parse lat/lng from nav_link
    if (navLink) {
      const match = navLink.match(/position=([\d.]+),([\d.]+)/);
      if (match) {
        const lng = parseFloat(match[1]);
        const lat = parseFloat(match[2]);
        wx.openLocation({
          latitude: lat,
          longitude: lng,
          name: name,
          scale: 16,
        });
        return;
      }
    }

    // Fallback: try to open AMAP mini program
    wx.showToast({ title: '暂无导航信息', icon: 'none' });
  },
});
