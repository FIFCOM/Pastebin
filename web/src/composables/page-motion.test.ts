// 运行:npm test(Node 内置 test runner,Node 24 直接执行 TS,不引入额外依赖)
// 只覆盖纯逻辑和 <html> 属性。CSS 与 <Transition> 的真实表现要在浏览器里验证,见 SKILL.md 第 9 步。
import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it } from 'node:test'
import { pageMotion, resolvePageMotion } from './page-motion.ts'

type Meta = { depth?: number; transition?: 'fade' | 'shared-x' | 'shared-y' | 'none' }
function loc(path: string, meta: Meta = {}, matched = true) {
  return { path, meta, matched: matched ? [{}] : [] } as never
}

const home = loc('/', { depth: 0 })
const join = loc('/join/123456', { depth: 0 })
const viewer = loc('/p/abc', { depth: 1 })
const download = loc('/p/abc/download/f1', { depth: 2 })
const history = loc('/history', { depth: 0 })
const users = loc('/users', { depth: 0 })
const docs = loc('/docs/overview', { depth: 0, transition: 'fade' })
const login = loc('/login')

describe('resolvePageMotion', () => {
  it('skips the first navigation and query-only changes', () => {
    assert.equal(resolvePageMotion(home, loc('/', {}, false)).motion, 'none')
    assert.equal(resolvePageMotion(home, null).motion, 'none')
    assert.equal(resolvePageMotion(users, users).motion, 'none')
  })

  it('fades when either side has no depth (login, register, install)', () => {
    assert.equal(resolvePageMotion(login, home).motion, 'fade')
    assert.equal(resolvePageMotion(home, login).motion, 'fade')
  })

  it('uses fade-through across sections, fade if a side declares fade', () => {
    assert.equal(resolvePageMotion(history, users).motion, 'fade-through')
    assert.equal(resolvePageMotion(viewer, history).motion, 'fade-through')
    assert.equal(resolvePageMotion(docs, users).motion, 'fade')
    assert.equal(resolvePageMotion(users, docs).motion, 'fade')
  })

  it('treats /, /join and /p as one section: editor -> viewer -> download slides', () => {
    assert.deepEqual(resolvePageMotion(viewer, home), { motion: 'shared-x', dir: 'fwd' })
    assert.deepEqual(resolvePageMotion(download, viewer), { motion: 'shared-x', dir: 'fwd' })
    assert.deepEqual(resolvePageMotion(home, viewer), { motion: 'shared-x', dir: 'back' })
    assert.deepEqual(resolvePageMotion(join, download), { motion: 'shared-x', dir: 'back' })
  })

  it('fades through between same-depth pages of one section', () => {
    assert.equal(resolvePageMotion(join, home).motion, 'fade-through')
  })

  it('honors a one-shot override, then applies the level', () => {
    assert.equal(resolvePageMotion(viewer, home, 'full', 'fade').motion, 'fade')
    assert.equal(resolvePageMotion(viewer, home, 'reduced').motion, 'fade')
    assert.equal(resolvePageMotion(history, users, 'reduced').motion, 'fade')
    assert.equal(resolvePageMotion(viewer, home, 'off').motion, 'none')
    assert.equal(resolvePageMotion(viewer, home, 'reduced', 'none').motion, 'none')
  })
})

describe('pageMotion state', () => {
  const store = new Map<string, string>()
  let dataset: Record<string, string | undefined>
  const g = globalThis as Record<string, unknown>

  beforeEach(() => {
    store.clear()
    dataset = {}
    g.document = { documentElement: { dataset } }
    g.localStorage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v)
    }
    delete g.matchMedia
  })

  afterEach(() => {
    pageMotion.setLevel('full')
    pageMotion.leaveDone()
  })

  it('persists the level under motion_level and mirrors it on <html>', () => {
    pageMotion.setLevel('reduced')
    assert.equal(store.get('motion_level'), 'reduced')
    assert.equal(dataset.motion, 'reduced')
  })

  it('only allows full motion at the full level', () => {
    assert.equal(pageMotion.allowsFullMotion(), true)
    pageMotion.setLevel('reduced')
    assert.equal(pageMotion.allowsFullMotion(), false)
    pageMotion.setLevel('off')
    assert.equal(pageMotion.allowsFullMotion(), false)
  })

  it('treats the OS reduced-motion setting as off', () => {
    g.matchMedia = (query: string) => ({
      matches: query.includes('prefers-reduced-motion'),
      addEventListener: () => undefined,
      removeEventListener: () => undefined
    })
    pageMotion.setLevel('full')
    assert.equal(pageMotion.effective(), 'off')
    assert.equal(dataset.motion, 'off')
    assert.equal(pageMotion.prepare(viewer, home).motion, 'none')
  })

  it('writes the plan; afterLeave waits for leaveDone', async () => {
    pageMotion.prepare(viewer, home)
    assert.equal(dataset.pageMotion, 'shared-x')
    assert.equal(dataset.pageDir, 'fwd')
    let done = false
    void pageMotion.afterLeave().then(() => (done = true))
    await Promise.resolve()
    assert.equal(done, false)
    pageMotion.leaveDone()
    await Promise.resolve()
    assert.equal(done, true)
  })

  it('keeps the settling window closed while the old page is mounted', () => {
    pageMotion.beginEnter()
    pageMotion.prepare(viewer, home) // 换页:旧页面还在 DOM,窗口必须关
    assert.equal('pageSettling' in dataset, false)
    pageMotion.beginEnter() // 新页面插入前再开
    assert.equal('pageSettling' in dataset, true)
    pageMotion.leaveDone()
    delete dataset.pageSettling
  })

  it('leaves the window alone for query-only changes, opens it on first navigation', () => {
    pageMotion.beginEnter()
    pageMotion.prepare(users, users)
    assert.equal('pageSettling' in dataset, true)
    delete dataset.pageSettling
    pageMotion.prepare(users, loc('/', {}, false))
    assert.equal('pageSettling' in dataset, true)
    delete dataset.pageSettling
  })
})
