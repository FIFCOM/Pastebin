# 审计与迁移

**先审计再动手。** 只给新写的 CSS 接档位,项目里原有的动画就会绕过它。真实案例里绕过档位的有五类,下面的 grep 能全部找到。

## 审计命令

在前端源码根目录运行(ripgrep;没有 `rg` 就用编辑器的全文搜索):

```
# 1. 只认系统设置、不认应用档位的判断
rg -n "prefers-reduced-motion|matchMedia\(" src
# 2. 写死时长的 CSS 动画和过渡
rg -n "(animation|transition)(-duration|-delay)?\s*:|@keyframes|@starting-style" src
# 3. 写死的位移、缩放入场量
rg -n "translate[XY]?\(|scale\(" src --glob "*.{css,vue}"
# 4. 平滑滚动
rg -n "scroll-behavior|behavior:|scrollIntoView|scrollTo\(" src
# 5. JS 驱动的动画
rg -n "requestAnimationFrame|\.animate\(|transitionend|animationend" src
# 6. 和动画时长耦合的定时器(防抖、冷却、轮询这类功能性定时器不算)
rg -n "setTimeout|EXIT_MS|FALLBACK" src
# 7. 组件库在 shadow DOM 里取时长的方式
rg -n "motion-duration|getDuration" node_modules/<库名>
```

把结果按下表分类,每一类的处理方式固定。

## 五类绕过与处理

| 类别 | 症状 | 处理 |
|---|---|---|
| 写死的 CSS 动画 | 关闭后仍有位移或缩放动画 | `off` 由总开关压到 0.01ms。位移量改成 `calc(Npx * var(--m-shift))`,缩放量改成 `scale(calc(1 - 0.04 * var(--m-shift)))`,这样 `reduced` 档只剩淡入淡出。 |
| 自己读系统设置的 JS | 设置里选了关闭,系统没开减少动态效果时仍有动画 | 全部换成 `pageMotion.allowsFullMotion()`(高度补间、数字滚动、平滑滚动)。删掉各处的 `matchMedia`。 |
| 全局平滑滚动 | 切页后回顶部变成滚动动画 | `scroll-behavior: smooth` 保留在 `html`,`reduced` / `off` 档由 motion.css 改回 `auto`。`scrollBehavior` 和 `scrollIntoView` 的 `behavior` 按 `allowsFullMotion()` 取值。 |
| 组件库 shadow DOM 动画 | 对话框、导航栏等关不掉 | 组件库用 `getComputedStyle` 读 CSS 变量取时长,全局选择器管不到。把它的时长令牌在 `off` 档归零(motion.css 里已有 MDUI 2 的写法)。先用第 7 条 grep 确认库是怎么取时长的。 |
| 只认系统设置的媒体查询 | 同上 | 删除。系统设置已被映射成 `off`。需要在 `reduced` 档保留的短淡入,选择器改成 `:root[data-motion="reduced"] …`。 |

## 迁移规则

- **旧令牌别名**:项目已有 `--xx-fast` / `--xx-med` / `--xx-ease` 之类的令牌且被大量引用时,在 motion.css 里把它们指向新令牌,不要全局重命名。
- **悬停和按压反馈**:不用改。`off` 档的总开关会让它们瞬时,`reduced` 档保留。
- **持续循环的加载动画**(骨架屏微光、旋转指示):`reduced` 档仍可保留 opacity 脉冲;位移型微光改成 `:root[data-motion="reduced"] … { animation: none }`。
- **功能性定时器**(防抖、冷却、重试):不是动画,不改。
- **依赖 `transitionend` 的代码**:总开关用 0.01ms 而非 `none`,事件仍会触发。组件自己的兜底定时器保留。
- **Vue `<Transition>` 的进场首帧**:`enter-from` 状态会在 0.01ms 下停留约一两帧,肉眼不可见,不需要处理。

## 完成标准

- 审计命令 1 的结果里只剩 `page-motion.ts` 一处。
- 审计命令 3 找到的每个入场位移量都带 `--m-shift`,或属于悬停 / 按压 / 定位类用途。
- `reference/verify.md` 的三档采样全部符合预期。
