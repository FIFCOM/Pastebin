import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_BACKEND || 'http://localhost:8000'
  
  return {
    base: env.VITE_BASE_PATH || '/',
    server: {
      proxy: {
        '/api': {target, changeOrigin: true, ws: true},
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
    },
    build: {
      // Markdown 预览中的 KaTeX / Mermaid 已经按需拆到异步 chunk。
      // 这两个功能包自身略高于 Vite 默认 500 KiB 阈值，放宽告警避免构建噪声。
      chunkSizeWarningLimit: 700,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return

            if (id.includes('katex')) {
              return 'viewer-katex'
            }

            if (id.includes('highlight.js')) {
              return 'viewer-highlight'
            }

            if (id.includes('markdown-it')) {
              return 'viewer-markdown'
            }

            if (id.includes('/mdui/')) {
              return 'ui-mdui'
            }

            if (id.includes('/vue/') || id.includes('/vue-router/')) {
              return 'framework'
            }
          }
        }
      }
    }
  }
})
