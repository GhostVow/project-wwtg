// app.js — 周末搭子小程序入口
App({
  onLaunch() {
    console.log('周末搭子启动');
  },
  globalData: {
    baseURL: 'http://localhost:8000/api/v1',
    mockMode: true,
    userInfo: null,
    sessionId: null,
  }
});
