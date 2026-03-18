// components/plan-card/plan-card.js — 方案卡片组件
Component({
  properties: {
    plan: {
      type: Object,
      value: {},
    },
  },

  data: {
    animateIn: false,
  },

  lifetimes: {
    attached() {
      // Slide-up animation on attach
      setTimeout(() => {
        this.setData({ animateIn: true });
      }, 50);
    },
  },

  methods: {
    onTap() {
      this.triggerEvent('plantap', { planId: this.data.plan.plan_id });
    },
  },
});
