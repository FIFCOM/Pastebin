import './assets/mdui-grid.css'
import './style.css'
import 'material-icons/iconfont/material-icons.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { registerMbServiceWorker } from './utils/mbSw'

createApp(App).use(router).mount('#app')

// Register the decrypting service worker (used for video Range + streaming decrypt).
registerMbServiceWorker().catch((e) => console.warn('SW register failed:', e))
