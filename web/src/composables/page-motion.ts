import { ref } from "vue"
import type { RouteLocationNormalized } from "vue-router"

/** 页面过渡预设,对应 motion.css 里的 html[data-page-motion]。 */
export type PageMotion = "none" | "fade" | "fade-through" | "shared-x" | "shared-y"
/** 方向:fwd 为进入更深一层,back 为返回上一层。 */
export type PageDir = "fwd" | "back"
/** 用户的动画档位:full 完整、reduced 精简(仅淡入淡出)、off 关闭。 */
export type MotionLevel = "full" | "reduced" | "off"
export type PageMotionPlan = Readonly<{ motion: PageMotion; dir: PageDir }>

declare module "vue-router" {
  interface RouteMeta {
    /** 层级深度:同一板块内由浅入深用 shared 轴动画;缺省表示不参与(登录、404),走 fade。 */
    depth?: number
    /** 进入该页(或从该页返回)时使用的预设,缺省 shared-x。含 position:fixed 元素的页面设 "fade"。 */
    transition?: PageMotion
  }
}

// 与 useTheme 的 theme / theme_color 命名保持一致
const STORAGE_KEY = "motion_level"
/** 离场动画的兜底等待:after-leave 没触发时也不能卡住滚动复位。 */
const LEAVE_FALLBACK_MS = 400
/** 导航后 data-page-settling 的保持时长:大于 stagger 最大延迟加时长(约 560ms),并留出数据加载时间。 */
const SETTLING_MS = 1200

type Loc = Pick<RouteLocationNormalized, "path" | "meta" | "matched">

// “板块”按路径第一段划分。编辑器(/ 与 /join)和查看页(/p)属于同一个“粘贴”板块,
// 这样从编辑器进入查看页走横向 shared-x,而不是同级的 fade-through。
function section(path: string): string {
  const first = path.split("/")[1] ?? ""
  return first === "" || first === "join" || first === "p" ? "paste" : first
}

/** 纯函数:根据来去路由和档位决定过渡预设。规则优先级见 SKILL.md“预设选择规则”。 */
export function resolvePageMotion(
  to: Loc,
  from: Loc | null,
  level: MotionLevel = "full",
  override?: PageMotion,
): PageMotionPlan {
  const none: PageMotionPlan = { motion: "none", dir: "fwd" }
  if (level === "off") return none
  const limit = (plan: PageMotionPlan): PageMotionPlan =>
    level === "reduced" && plan.motion !== "none" ? { motion: "fade", dir: plan.dir } : plan
  if (override) return limit({ motion: override, dir: "fwd" })
  if (!from || from.matched.length === 0) return none // 首次导航没有旧页面
  if (to.path === from.path) return none // 只改 query
  const toDepth = to.meta.depth
  const fromDepth = from.meta.depth
  if (toDepth === undefined || fromDepth === undefined) return limit({ motion: "fade", dir: "fwd" })
  // 同级切换:任一端声明了 fade(含 position:fixed 的页面)就只用 opacity 动画
  const peer: PageMotion =
    to.meta.transition === "fade" || from.meta.transition === "fade" ? "fade" : "fade-through"
  if (section(to.path) !== section(from.path)) return limit({ motion: peer, dir: "fwd" })
  if (toDepth > fromDepth) return limit({ motion: to.meta.transition ?? "shared-x", dir: "fwd" })
  if (toDepth < fromDepth) return limit({ motion: from.meta.transition ?? "shared-x", dir: "back" })
  return limit({ motion: peer, dir: "fwd" })
}

function isMotionLevel(value: string | null): value is MotionLevel {
  return value === "full" || value === "reduced" || value === "off"
}

function readLevel(): MotionLevel {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isMotionLevel(stored) ? stored : "full"
  } catch {
    return "full"
  }
}

const level = ref<MotionLevel>(readLevel())
let override: PageMotion | undefined
let pending: Promise<void> | null = null
let release: (() => void) | null = null
let timer: ReturnType<typeof setTimeout> | undefined
let settlingTimer: ReturnType<typeof setTimeout> | undefined

function prefersReducedMotion(): boolean {
  return typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches
}

/** 生效档位:系统开启“减少动态效果”时一律视为 off,否则取用户在设置里选的档位。 */
function effectiveLevel(): MotionLevel {
  return prefersReducedMotion() ? "off" : level.value
}

/** <html data-motion> 写的是生效档位,motion.css 只认这一个来源。 */
function writeLevel(): void {
  if (typeof document === "undefined") return
  document.documentElement.dataset.motion = effectiveLevel()
}

/** 开启“页面刚进入”窗口:motion.css 的内容错峰只在这个窗口内生效。
    必须在新页面插入之前调用;旧页面还在 DOM 时开启,旧页面的 [data-stagger] 子元素会重播入场动画(闪烁)。 */
function markSettling(): void {
  if (typeof document === "undefined") return
  const root = document.documentElement
  root.dataset.pageSettling = ""
  clearTimeout(settlingTimer)
  settlingTimer = setTimeout(() => delete root.dataset.pageSettling, SETTLING_MS)
}

/** 关闭窗口:新导航一开始就关,旧页面不会再匹配错峰规则。 */
function endSettling(): void {
  if (typeof document === "undefined") return
  clearTimeout(settlingTimer)
  delete document.documentElement.dataset.pageSettling
}

function settle(): void {
  clearTimeout(timer)
  release?.()
  pending = null
  release = null
}

export const pageMotion = {
  level,
  setLevel(next: MotionLevel): void {
    level.value = next
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* 存储不可用时仅本次会话生效 */
    }
    writeLevel()
  },
  /** 启动时调用(挂载前):把档位写到 <html data-motion>,并监听系统设置的运行中变化。 */
  init(): void {
    writeLevel()
    if (typeof matchMedia === "function")
      matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", writeLevel)
  },
  /** 当前生效档位(含系统设置)。JS 里的动画一律用它或 allowsFullMotion() 判断。 */
  effective: effectiveLevel,
  /** 只有 full 档才允许位移、缩放、高度补间、数字滚动、平滑滚动这类“有运动感”的效果。 */
  allowsFullMotion(): boolean {
    return effectiveLevel() === "full"
  },
  /** 新页面(或登录页 / 主界面)即将插入时调用,开启内容错峰的生效窗口。 */
  beginEnter(): void {
    markSettling()
  },
  /** 为下一次导航指定一次性预设,用完即清除。 */
  next(motion: PageMotion): void {
    override = motion
  },
  /** 在 router.beforeResolve 里调用:解析并同步写到 <html>,使离场动画也能读到。 */
  prepare(to: Loc, from: Loc | null): PageMotionPlan {
    const plan = resolvePageMotion(to, from, effectiveLevel(), override)
    override = undefined
    if (typeof document !== "undefined") {
      document.documentElement.dataset.pageMotion = plan.motion
      document.documentElement.dataset.pageDir = plan.dir
    }
    // 换页时先关错峰窗口,之后由 beginEnter() 在新页面插入前再开。
    // 首次导航没有旧页面,可以直接开;只改 query(同路径)保持原状,不重播。
    if (to.path !== from?.path) {
      endSettling()
      if (!from || from.matched.length === 0) markSettling()
    }
    settle()
    if (plan.motion !== "none") {
      pending = new Promise<void>((resolve) => {
        release = resolve
      })
      timer = setTimeout(settle, LEAVE_FALLBACK_MS)
    }
    return plan
  },
  /** PageTransition 在离场结束(或取消)时调用。 */
  leaveDone(): void {
    settle()
  },
  /** 供 scrollBehavior 等待离场结束;没有离场动画时立即完成。 */
  afterLeave(): Promise<void> {
    return pending ?? Promise.resolve()
  },
}
