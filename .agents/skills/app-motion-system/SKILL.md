---
name: app-motion-system
description: Build or unify an app-wide animation system for a web frontend. Covers route/page transitions with direction-aware presets, staggered content entrance, one user-facing motion level (full / reduced / off) that every CSS, JS and component-library animation obeys, OS prefers-reduced-motion handling, and browser verification with document.getAnimations(). Reference implementation is Vue 3 + vue-router 4. Use when the user wants page-switch animations, consistent animations across all pages, an animation on/off setting, or when some animations ignore the reduced-motion/off setting. 页面切换动画、入场动画、动画开关、减少动态效果统一。
---

# App Motion System

给整个前端应用建立一套统一的动画体系:页面切换、内容入场、用户可调的动画档位,并保证所有动画(自写 CSS、JS、组件库内部)都服从同一个开关。

**验证范围**:参考实现在 Vue 3.5 + vue-router 4.6 + Vite + MDUI 2 上做过浏览器验证。CSS 和 `page-motion.ts` 的纯逻辑与框架无关。`<Transition>` 和路由守卫这层胶水在其它框架里没有测过,移植时对照 `reference/vue-wiring.md` 自己验证。

## 何时使用

- 用户要页面切换动画,或要“所有页面动画统一”。
- 用户要在设置里加动画开关(完整/精简/关闭),或反馈“关了动画还有动画”。
- 项目里 `@media (prefers-reduced-motion)`、`matchMedia`、写死的 `transition` / `@keyframes` 散落各处。

不适用:只给单个组件加悬停效果、原生移动端、canvas / WebGL 动效。

## 核心设计(五条,改动时不要破坏)

1. **单一来源**:`<html data-motion="full|reduced|off">` 写的是“生效档位”(系统开启减少动态效果时为 `off`)。CSS 只读这个属性,JS 只调 `allowsFullMotion()`。任何地方都不要自己写 `prefers-reduced-motion` 或 `matchMedia`。
2. **三层**:A 页面过渡(路由级 `<Transition>`);B 内容错峰入场(`[data-stagger]`,纯 CSS);C 局部微动效(列表增删、骨架屏、对话框,各组件自己的,保留)。A 与 B 通过 CSS 变量 `--stagger-y` 衔接,避免两层动作叠加。
3. **档位语义**:`full` 完整。`reduced` 只剩淡入淡出,位移和缩放量乘 `--m-shift`(=0),高度补间、数字滚动、平滑滚动由 JS 关闭。`off` 是总开关,所有 CSS 动画和过渡压到 0.01ms,组件库时长令牌归零。
4. **预设由数据决定**:路由 `meta.depth`(层级)和 `meta.transition`(预设)加纯函数 `resolvePageMotion()` 选出预设,在 `router.beforeResolve` 里**同步**写到 `<html data-page-motion / data-page-dir>`。不要用动态 `<Transition :name>`。
5. **错峰有生效窗口**:`html[data-page-settling]` 只在新页面插入前(`before-enter`)打开 1.2 秒。不要在旧页面还在 DOM 时打开,否则旧页面会闪两次。

## 预设

| 预设 | 用途 | 位移 | 时长(出/入) |
|---|---|---|---|
| `fade-through` | 同级页面(侧栏 / 底栏的各一级页) | 入场缩放 .96 | 90 / 210ms |
| `shared-x` | 同一板块内进入或返回子页面 | 横向 ±24px | 100 / 280ms |
| `shared-y` | 新建、编辑类表单页(“创建”语义) | 纵向 ±28px | 100 / 300ms |
| `fade` | 登录与主界面互切、404、含 `position:fixed` 的页面 | 无,只改 opacity | 80 / 160ms |
| `none` | 首次导航、只改 query、off 档 | 无 | 0 |

### 预设选择规则(`resolvePageMotion`,按优先级)

1. 档位 `off` → `none`。一次性覆盖 `pageMotion.next(x)` 优先于下面所有规则。
2. 没有旧页面(首次导航)或路径相同(只改 query)→ `none`。
3. 任一端没有 `meta.depth`(登录、404)→ `fade`。
4. 一级路径段不同 → `fade-through`;任一端声明 `fade` 则用 `fade`。
5. 同板块内 `depth` 变大 → 方向 `fwd`,预设取目标页 `meta.transition ?? "shared-x"`。
6. 同板块内 `depth` 变小 → 方向 `back`,预设取来源页 `meta.transition ?? "shared-x"`。
7. 同板块内 `depth` 相同 → 同第 4 条的同级预设。
8. 档位 `reduced`:除 `none` 外一律降为 `fade`。

## 工作流程

按顺序做。**第 1 步不能跳**:最常见的失败是只给新写的 CSS 接了档位,项目里原有的动画绕过它(“关了动画还有动画”)。

1. **审计现有动画**。按 `reference/audit-and-migrate.md` 的 grep 清单找出所有动画来源,分类后再动手。
2. **和用户确认**(只问影响设计的):哪些页面是同级、哪些是子页面(决定 `depth`);哪些页面含 `position:fixed` 元素(FAB、悬浮栏);是否需要设置页入口;是否用了会在 shadow DOM 里自己做动画的组件库。
3. **拷贝模板**到项目:`templates/motion.css`、`templates/page-motion.ts`、`templates/PageTransition.vue`。处理所有 `TODO(adapt)`(存储键、板块划分、组件库令牌、导入路径、裁剪溢出的容器选择器、错峰排除的浮层选择器)。
4. **接入**。按 `reference/vue-wiring.md`:入口 import 样式并调用 `pageMotion.init()`;路由加 `scrollBehavior` 和 `beforeResolve`;外壳用 `PageTransition`;登录与主界面互切用 `shell-fade`。
5. **给路由加 meta**:`depth`(一级页 0,子页 1,依此类推)和 `transition`(表单页 `shared-y`,含固定元素的页面 `fade`)。
6. **标记错峰容器**:只给结构容器(页面里的卡片列、section 列表)加 `data-stagger`。不要加在随筛选、分页变化的数据列表上。
7. **迁移原有动画**。按审计结果逐类处理:写死的位移量改成 `calc(Npx * var(--m-shift))`;删掉只认系统设置的 `@media (prefers-reduced-motion)`;JS 里的 `matchMedia` 全换成 `pageMotion.allowsFullMotion()`。
8. **设置页入口**(可选):三档单选,调用 `pageMotion.setLevel()`。
9. **验证**。单元测试覆盖 `resolvePageMotion` 和状态;**必须在真实浏览器里**按 `reference/verify.md` 跑 full / reduced / off 三档的 `getAnimations()` 采样和一次旧页面闪烁的 A/B 对照。jsdom 看不到 CSS,单元测试通过不代表动画对。

## 文件清单

| 文件 | 作用 |
|---|---|
| `templates/motion.css` | 令牌、档位、总开关、页面过渡预设、错峰规则 |
| `templates/page-motion.ts` | `resolvePageMotion()` 纯函数 + `pageMotion` 状态(档位、写属性、等待离场、错峰窗口) |
| `templates/PageTransition.vue` | 路由级 `<Transition mode="out-in">` |
| `templates/page-motion.test.ts` | 选择规则与状态的单元测试 |
| `templates/verify-motion.mjs` | Playwright 三档采样脚本(改顶部 `CONFIG` 后运行) |
| `reference/vue-wiring.md` | 入口、路由、外壳、登录切换、设置页、JS 调用点的接入代码 |
| `reference/pitfalls.md` | 已踩过的坑:症状、原因、做法 |
| `reference/audit-and-migrate.md` | 审计 grep 清单、五类绕过档位的动画及迁移做法 |
| `reference/verify.md` | 真实浏览器验证脚本与预期结果 |

## 必须遵守

- 不要在任何地方单独写 `@media (prefers-reduced-motion)` 或调用 `matchMedia("(prefers-reduced-motion…")`。系统设置只通过 `page-motion.ts` 进入。
- 不要在组件里写无档位限定的 `!important` 过渡声明。总开关的优先级是 (0,2,1),组件里选择器更长的 `!important` 仍会盖过它,导致 `off` 档关不掉。需要在 `reduced` 档保留的短淡入,选择器写成 `:root[data-motion="reduced"] …`,这样 `off` 档不会命中。
- 错峰选择器排除浮层元素(`dialog`、snackbar、FAB)。它们有自己的定位和过渡,`transform` 动画会覆盖。
- `prepare()`(`beforeResolve`)里不要开错峰窗口,只能在 `before-enter` 开。例外是首次导航,那时没有旧页面。
- 不要把 `<RouterView>` 直接放进 `<Transition>`,也不要用 `<RouterView v-slot>` 包住含另一层 `<RouterView>` 的外壳。见 `reference/pitfalls.md`。
- 模板里的 `TODO(adapt)` 必须全部处理,处理完用 grep 确认没有残留。
- 汇报时要区分“已在浏览器里验证”和“只通过了单元测试”,没有跑过的路径(移动端宽度、对话框、特定页面)直接写出来。
