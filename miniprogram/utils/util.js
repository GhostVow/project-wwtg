// utils/util.js — 通用工具函数

/**
 * 格式化时间
 */
function formatTime(date) {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hour = date.getHours();
  const minute = date.getMinutes();
  return `${year}-${pad(month)}-${pad(day)} ${pad(hour)}:${pad(minute)}`;
}

function pad(n) {
  return n < 10 ? '0' + n : '' + n;
}

/**
 * 生成简单 UUID
 */
function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

module.exports = { formatTime, uuid };
