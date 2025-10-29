import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_BACKEND || 'http://localhost:8000'
  
  return {
    base: './',
    server: {
      proxy: {
        '/api': {target, changeOrigin: true},
      }
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    plugins: [
      vue({
        template: {
          compilerOptions: {
            // 所有以 mdui- 开头的标签名都是 mdui 组件
            isCustomElement: (tag) => tag.startsWith('mdui-')
          }
        }
      }),
      // 复制 vditor 静态资源到构建输出目录
      viteStaticCopy({
        targets: [
          {
            src: 'node_modules/vditor/dist',
            dest: 'vditor'
          }
        ]
      })
    ],
    // 配置静态资源处理
    assetsInclude: ['**/*.wasm'],
    // 优化依赖预构建
    optimizeDeps: {
      include: ['vditor']
    }
  }
})
