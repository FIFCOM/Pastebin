import './assets/mdui-grid.css'
import './style.css'
import './assets/motion.css'
import 'material-icons/iconfont/material-icons.css'
import 'material-dynamic-colors'

import { createApp } from 'vue'
import App from './App.vue'
import { pageMotion } from './composables/page-motion'
import router from './router'
import { registerMbServiceWorker } from './utils/mbSw'

// 版本徽标:由 Vite define 在构建时注入 __APP_VERSION__
console.info(
  '%c MaterialBin %c v' + __APP_VERSION__ + ' ',
  'background:#6750a4;color:#fff;font-weight:600;padding:2px 6px;border-radius:4px 0 0 4px',
  'background:#eaddff;color:#21005d;font-weight:600;padding:2px 6px;border-radius:0 4px 4px 0'
)

// 必须在 mount 之前:把动画档位写到 <html data-motion>
pageMotion.init()

createApp(App).use(router).mount('#app')

// Register the decrypting service worker (used for video Range + streaming decrypt).
registerMbServiceWorker().catch((e) => console.warn('SW register failed:', e))
