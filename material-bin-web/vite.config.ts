import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'

// https://vite.dev/config/
export default defineConfig({
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
})
