// app-motion-system / page-motion.test.ts(vitest + jsdom)
// TODO(adapt): 导入路径;下面的路由样例按项目的 depth / transition 约定改。
import { afterEach, describe, expect, it, vi } from "vitest"
import { pageMotion, resolvePageMotion } from "./page-motion"

type Meta = { depth?: number; transition?: "fade" | "shared-x" | "shared-y" | "none" }
function loc(path: string, meta: Meta = {}, matched = true) {
  return { path, meta, matched: matched ? [{}] : [] } as never
}
const dashboard = loc("/dashboard", { depth: 0, transition: "fade" }) // 含 position:fixed 元素
const list = loc("/items", { depth: 0 })
const detail = loc("/items/detail", { depth: 1 })
const form = loc("/items/new", { depth: 1, transition: "shared-y" })
const settings = loc("/settings", { depth: 0 })
const login = loc("/login")

describe("resolvePageMotion", () => {
  it("skips the first navigation and query-only changes", () => {
    expect(resolvePageMotion(list, loc("/", {}, false)).motion).toBe("none")
    expect(resolvePageMotion(list, null).motion).toBe("none")
    expect(resolvePageMotion(list, list).motion).toBe("none")
  })

  it("fades when either side has no depth", () => {
    expect(resolvePageMotion(login, list).motion).toBe("fade")
    expect(resolvePageMotion(list, login).motion).toBe("fade")
  })

  it("uses fade-through across sections, fade if a side declares fade", () => {
    expect(resolvePageMotion(list, settings).motion).toBe("fade-through")
    expect(resolvePageMotion(detail, settings).motion).toBe("fade-through")
    expect(resolvePageMotion(dashboard, list).motion).toBe("fade")
    expect(resolvePageMotion(list, dashboard).motion).toBe("fade")
  })

  it("slides forward and back inside a section, preset from the deeper route", () => {
    expect(resolvePageMotion(detail, list)).toEqual({ motion: "shared-x", dir: "fwd" })
    expect(resolvePageMotion(list, detail)).toEqual({ motion: "shared-x", dir: "back" })
    expect(resolvePageMotion(form, list)).toEqual({ motion: "shared-y", dir: "fwd" })
    expect(resolvePageMotion(list, form)).toEqual({ motion: "shared-y", dir: "back" })
  })

  it("fades through between siblings of the same depth", () => {
    expect(resolvePageMotion(form, detail).motion).toBe("fade-through")
  })

  it("honors a one-shot override, then applies the level", () => {
    expect(resolvePageMotion(detail, list, "full", "fade").motion).toBe("fade")
    expect(resolvePageMotion(detail, list, "reduced").motion).toBe("fade")
    expect(resolvePageMotion(list, settings, "reduced").motion).toBe("fade")
    expect(resolvePageMotion(detail, list, "off").motion).toBe("none")
    expect(resolvePageMotion(detail, list, "reduced", "none").motion).toBe("none")
  })
})

describe("pageMotion state", () => {
  afterEach(() => {
    pageMotion.setLevel("full")
    pageMotion.leaveDone()
    delete document.documentElement.dataset.pageSettling
  })

  it("persists the level and mirrors the effective level on <html>", () => {
    pageMotion.setLevel("reduced")
    expect(localStorage.getItem("app.motion")).toBe("reduced") // TODO(adapt): 存储键
    expect(document.documentElement.dataset.motion).toBe("reduced")
  })

  it("only allows full motion at the full level", () => {
    expect(pageMotion.allowsFullMotion()).toBe(true)
    pageMotion.setLevel("reduced")
    expect(pageMotion.allowsFullMotion()).toBe(false)
    pageMotion.setLevel("off")
    expect(pageMotion.allowsFullMotion()).toBe(false)
  })

  it("treats the OS reduced-motion setting as off", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query.includes("prefers-reduced-motion"),
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }))
    pageMotion.setLevel("full")
    expect(pageMotion.effective()).toBe("off")
    expect(document.documentElement.dataset.motion).toBe("off")
    expect(pageMotion.prepare(detail, list).motion).toBe("none")
    vi.unstubAllGlobals()
  })

  it("writes the plan; afterLeave waits for leaveDone", async () => {
    pageMotion.prepare(detail, list)
    expect(document.documentElement.dataset.pageMotion).toBe("shared-x")
    expect(document.documentElement.dataset.pageDir).toBe("fwd")
    let done = false
    void pageMotion.afterLeave().then(() => (done = true))
    await Promise.resolve()
    expect(done).toBe(false)
    pageMotion.leaveDone()
    await Promise.resolve()
    expect(done).toBe(true)
  })

  it("keeps the settling window closed while the old page is mounted", () => {
    const root = document.documentElement.dataset
    pageMotion.beginEnter()
    pageMotion.prepare(detail, list) // 换页:旧页面还在 DOM,窗口必须关
    expect("pageSettling" in root).toBe(false)
    pageMotion.beginEnter() // 新页面插入前再开
    expect("pageSettling" in root).toBe(true)
  })

  it("leaves the window alone for query-only changes, opens it on first navigation", () => {
    const root = document.documentElement.dataset
    pageMotion.beginEnter()
    pageMotion.prepare(list, list)
    expect("pageSettling" in root).toBe(true)
    delete root.pageSettling
    pageMotion.prepare(list, loc("/", {}, false))
    expect("pageSettling" in root).toBe(true)
  })
})
