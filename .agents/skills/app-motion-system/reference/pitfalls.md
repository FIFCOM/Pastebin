# 已踩过的坑

每条:症状 → 原因 → 做法。

## 切页时旧页面闪两下

- **原因**:在 `beforeResolve` 里就打开了 `data-page-settling`,此刻旧页面还在 DOM 里,它的 `[data-stagger]` 子元素重新匹配错峰规则,先变透明再淡入,叠加根元素的离场淡出。
- **做法**:`prepare()` 换页时关窗口,`before-enter` 里再开。首次导航没有旧页面,可以在 `prepare()` 里开。
- **怎么确认**:`verify.md` 的 A/B 对照。点击前手动写入 `data-page-settling` 模拟旧行为,旧页面子元素在根不透明时掉到 0 再回升。

## 切页后页面区域一片空白

- **原因**:外壳里还有一层 `<RouterView>`,而外层写成了 `<RouterView v-slot>` 包住外壳。外层会给 slot 内容提供 `viewDepth + 1`,里面那层变成第 1 层,匹配不到路由。
- **做法**:外层不用 `RouterView`。登录页用函数式组件 `() => h(RouterView)` 作为 `<Transition>` 的直接子节点。
- **相关警告**:`<router-view> can no longer be used directly inside <transition>`。这是同一个坑的另一面,不要为消除警告而选前一种写法。

## 动态 `<Transition :name>` 让离场动画用错预设

- **原因**:离场中的节点沿用旧的 transition props,name 变化时它拿到的还是旧值。
- **做法**:name 固定为 `page`,预设通过 `<html data-page-motion>` 切换,在 `beforeResolve` 同步写入。

## 含 `position: fixed` 的页面,动画结束时元素跳一下

- **原因**:页面根元素上的 `transform` / `scale` 动画让它成为 fixed 后代的包含块,动画期间 fixed 元素相对页面定位,结束时跳回视口。`opacity` 动画不会。
- **做法**:这类页面设 `meta.transition: "fade"`。`fade` 预设用只改 opacity 的 keyframes。解析规则里任一端声明 `fade`,同级切换也用 `fade`,所以进出这类页面都安全。
- **进场用 `backwards` 不用 `both`**:结束后不保留 transform。

## 横向位移时出现横向滚动条

- **做法**:动画期间给容器加 `overflow-x: clip`。不要用 `hidden`,它会创建滚动容器并破坏 `position: sticky`。

## 关闭动画后还有动画

见 `audit-and-migrate.md`。五类原因,先审计再改。

## 总开关盖不住某些过渡

- **原因**:组件里带 `!important` 且选择器更长的过渡声明,优先级高于总开关的 (0,2,1)。
- **做法**:不要写无档位限定的 `!important` 过渡。需要在 `reduced` 保留的写成 `:root[data-motion="reduced"] …`。
- **附**:总开关用 0.01ms 而不是 `animation: none`,是为了让 `transitionend` / `animationend` 仍触发。

## 错峰动画盖掉对话框、snackbar、FAB 自己的定位

- **原因**:`[data-stagger] > *` 给它们加了 `animation` 和 `transform`。
- **做法**:选择器里用 `:not()` 排除浮层。条件渲染的子元素在窗口外出现时也不应重播,所以窗口只开 1.2 秒。

## 只改 query 的导航触发页面过渡

- **做法**:`<component :key="route.path">`,不要用 `fullPath`。`resolvePageMotion` 里路径相同返回 `none`,`scrollBehavior` 里路径相同返回 `false`。

## 同一组件服务两条路由(新建 / 编辑)

- 用 `route.path` 作 key,这两条路由之间切换会重建组件,可以接受。如果不想重建,把 key 换成路由 name 或组件。

## 验证脚本拿不到页面

- 脚本里拦截 API 的 glob 写成 `**/api/**` 会同时拦下 Vite 的 `/src/api/client.ts` 模块,页面空白。要写成后端真实前缀,如 `**/api/v1/**`。
- Vite 只监听 IPv6 `localhost` 时,`127.0.0.1` 连不上。统一用 `localhost`。
- mock 响应要符合应用自己的信封格式(如 `{ data, meta }`),否则解析失败被重定向到登录页。

## 改文件时

- 仓库是 CRLF 时,用 shell 做多行字符串替换会静默不匹配,还可能错改。用编辑工具,或逐行按行号替换并校验原文。
- shell 命令里带中文引号可能被转码导致解析失败,整段不执行。命令里只放 ASCII,注释之后用编辑工具补。
