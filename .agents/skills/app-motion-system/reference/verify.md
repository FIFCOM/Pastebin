# 浏览器验证

jsdom 没有 CSS 引擎,看不到动画。单元测试通过只说明选择逻辑对,不说明动画对。必须在真实 Chrome 里验证。

## 1. 三档采样

`templates/verify-motion.mjs` 在 full / reduced / off / 系统减少动态效果四种情况下,从起点页点击切到目标页,每帧统计 `document.getAnimations()` 里时长大于 1ms 的活动动画(含 shadow DOM),并标出哪些带位移或缩放。先改脚本顶部的 `CONFIG`,再运行:

```
node verify-motion.mjs
```

预期:

| 情况 | `data-motion` | peak | moving |
|---|---|---|---|
| full | `full` | 大于 0 | 含 `pm-in` 等 |
| reduced | `reduced` | 大于 0 | 空(只剩淡入淡出、透明度脉冲) |
| off | `off` | 0 | 空 |
| full + 系统减少动态效果 | `off` | 0 | 空 |

判读:

- `reduced` 的 moving 不为空:有位移量没乘 `--m-shift`,回到 `audit-and-migrate.md` 的命令 3。
- `off` 的 peak 不为 0:有带 `!important` 的组件过渡盖过总开关,或组件库在 shadow DOM 里用 JS 动画且时长令牌没归零。看脚本输出里的动画名定位。
- `reduced` 下 `st-in` 仍会出现,但位移为 0,不算 moving。这是预期。

## 2. 真实操作流

采样用 `localStorage` 预置档位,没有走设置页。再手动走一遍真实路径:在设置页点“关闭”,检查 `data-motion` 立即变 `off`、组件库时长令牌变 `0ms`,连续切 4 到 5 个页面 peak 为 0,刷新后档位保持。

## 3. 旧页面闪烁的 A/B 对照

不要只验证“修好了”,要先复现问题。在点击前手动写入 `document.documentElement.dataset.pageSettling = ""`,模拟旧行为;逐帧记录旧页面根元素和各子元素的 opacity。旧行为下会看到子元素在根不透明时掉到 0 再回升;正常行为下旧页面只单调淡出。

## 4. 验证夹具的坑

- 拦截 API 的 glob 必须是后端真实前缀(如 `**/api/v1/**`)。写成 `**/api/**` 会拦下 Vite 的源码模块,页面空白。
- mock 响应的信封格式要和应用的解析一致,否则解析失败、被重定向到登录页。
- 用 `localhost`,不要用 `127.0.0.1`。
- mock 数据不完整时页面会抛 pageerror(读取 undefined)。这是夹具问题,先确认与动画无关再忽略。
- 脚本要放在项目外的临时目录,用 `createRequire(项目 package.json)` 解析 `@playwright/test`。

## 5. 汇报时要写清楚的未验证项

没有逐个测过的页面、对话框、移动端宽度、真实后端,都要在汇报里列出来。例如:只采样了 A 页到 B 页的切换,对话框的动画没有打开测过。
