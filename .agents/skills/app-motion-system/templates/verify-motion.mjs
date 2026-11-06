// app-motion-system / verify-motion.mjs
// 真实浏览器验证:三档(full / reduced / off)下切页时的活动动画采样。
// 用法:先启动 dev server,再 `node verify-motion.mjs`。需要 @playwright/test 和本机 Chrome。
// TODO(adapt): 下面 CONFIG 整块按项目改。
import { createRequire } from "node:module"

const CONFIG = {
  base: "http://localhost:5173", // 用 localhost,不要用 127.0.0.1(Vite 可能只监听 IPv6)
  projectPackageJson: "C:/path/to/frontend/package.json", // 用来解析 @playwright/test
  storageKey: "app.motion", // 与 page-motion.ts 的 STORAGE_KEY 一致
  startPath: "/settings", // 起点页
  pageRoot: ".page-container > *", // 页面根元素,等它出现再开始采样
  gotoClick: 'a[href="/items"]', // 触发切页的元素选择器(会在页面里 .click())
  apiGlob: "**/api/v1/**", // 只拦后端接口,别写成 **/api/**(会拦掉 /src/api/*.ts 模块)
  cookies: [{ name: "csrf_token", value: "x" }], // 让应用认为已登录;按项目的会话机制改
  mock: (url) => ({ data: [], meta: { count: 0, limit: 50, next_cursor: null, has_more: false } }),
}

const require = createRequire(CONFIG.projectPackageJson)
const { chromium } = require("@playwright/test")

// 页面内采样:每帧统计时长 > 1ms 的活动动画(含 shadow DOM),并区分是否带位移 / 缩放
const SAMPLER = () => {
  const still = /^(none|translate(X|Y)?\(0(px)?\)|translate\(0(px)?, 0(px)?\)|scale\(1\)|matrix\(1, 0, 0, 1, 0, 0\))$/
  const movesBox = (a) =>
    a.effect.getKeyframes().some((k) => k.transform && !still.test(String(k.transform).trim()))
  window.__peak = 0
  window.__moving = new Set()
  const names = new Map()
  const tick = () => {
    const live = document.getAnimations().filter((a) => {
      const t = a.effect?.getComputedTiming?.()
      return t && (Number(t.duration) > 1 || Number(t.delay) > 1) && a.playState !== "finished"
    })
    window.__peak = Math.max(window.__peak, live.length)
    for (const a of live) {
      const n = a.animationName ?? a.transitionProperty ?? "waapi"
      names.set(n, (names.get(n) ?? 0) + 1)
      if (movesBox(a)) window.__moving.add(n)
    }
    window.__names = names
    window.__raf = requestAnimationFrame(tick)
  }
  window.__raf = requestAnimationFrame(tick)
}

const browser = await chromium.launch({ channel: "chrome" })

async function run(label, level, osReduce = false) {
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    reducedMotion: osReduce ? "reduce" : "no-preference",
  })
  await ctx.addCookies(CONFIG.cookies.map((c) => ({ ...c, url: CONFIG.base })))
  await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v), [CONFIG.storageKey, level])
  await ctx.route(CONFIG.apiGlob, (route) => {
    const body = CONFIG.mock(route.request().url())
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })
  })
  const page = await ctx.newPage()
  page.on("pageerror", (e) => console.log("  pageerror:", e.message))
  await page.goto(CONFIG.base + CONFIG.startPath)
  await page.waitForSelector(CONFIG.pageRoot)
  await page.waitForTimeout(1600) // 等首屏动画和错峰窗口结束
  const attr = await page.evaluate(() => document.documentElement.dataset.motion)
  await page.evaluate(SAMPLER)
  await page.evaluate((s) => document.querySelector(s).click(), CONFIG.gotoClick)
  await page.waitForTimeout(1500)
  const r = await page.evaluate(() => {
    cancelAnimationFrame(window.__raf)
    return {
      peak: window.__peak,
      moving: [...window.__moving],
      names: [...(window.__names ?? new Map()).entries()].sort((a, b) => b[1] - a[1]).slice(0, 6),
    }
  })
  console.log(`\n[${label}] data-motion=${attr}  peak=${r.peak}  moving=${r.moving.join(",") || "-"}`)
  for (const [n, c] of r.names) console.log(`   ${String(c).padStart(4)} frames  ${n}`)
  await ctx.close()
}

await run("full", "full")
await run("reduced", "reduced")
await run("off", "off")
await run("full + OS reduce", "full", true)
await browser.close()
// 预期:full 有 moving 动画;reduced 的 moving 为空(只剩淡入淡出);off 和 OS reduce 的 peak 为 0。
