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

// 必须在 mount 之前:把动画档位写到 <html data-motion>
pageMotion.init()

createApp(App).use(router).mount('#app')

// Register the decrypting service worker (used for video Range + streaming decrypt).
registerMbServiceWorker().catch((e) => console.warn('SW register failed:', e))
