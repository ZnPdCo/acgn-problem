import test from 'node:test'
import assert from 'node:assert/strict'
import { buildIndex } from '../src/lib/dataset.js'
import { computeStats, rankFor } from '../src/lib/stats.js'

const dataset = {
  source: { url: 'https://www.luogu.com.cn/article/93r0yhdc' },
  works: [
    {
      id: 'w1',
      name: 'CLANNAD',
      original: '',
      problems: [
        { key: 'P1', title: '一' },
        { key: 'P2', title: '二' },
      ],
    },
    {
      id: 'w2',
      name: '东方 Project',
      original: '東方Project',
      problems: [{ key: 'P2', title: '二' }],
    },
    { id: 'w3', name: 'Fate', original: '', problems: [{ key: 'P3', title: '三' }] },
  ],
  problems: {
    P1: {
      key: 'P1', id: 'P1', oj: 'luogu', ojName: '洛谷', title: '一',
      url: 'https://www.luogu.com.cn/problem/P1', works: ['w1'],
    },
    P2: {
      key: 'P2', id: 'P2', oj: 'luogu', ojName: '洛谷', title: '二',
      url: 'https://www.luogu.com.cn/problem/P2', works: ['w1', 'w2'],
    },
    P3: {
      key: 'P3', id: 'P3', oj: 'uoj', ojName: 'UOJ', title: '三',
      url: 'https://uoj.ac/problem/3', works: ['w3'],
    },
  },
}

const index = buildIndex(dataset)
const tagMap = {
  CLANNAD: ['key', 'galgame', 'romance'],
  '东方 Project': ['touhou'],
  Fate: [],
}
const now = Date.now()

test('concentration uses unique problems, not work rows', () => {
  const stats = computeStats(dataset, index, { P1: now })
  assert.equal(stats.solvedCount, 1)
  assert.ok(Math.abs(stats.concentration - 100 / 3) < 1e-9)
  assert.ok(Math.abs(stats.uniquePercent - 100 / 3) < 1e-9)
  assert.equal(stats.touchedWorkCount, 1)
  assert.equal(stats.ojStats.find((oj) => oj.key === 'luogu').solved, 1)
  assert.equal(stats.achievements.find((item) => item.id === 'first').unlocked, true)
  assert.equal(stats.achievements.find((item) => item.id === 'complete').unlocked, false)
})

test('a multi-work problem lights up every column but counts once', () => {
  const stats = computeStats(dataset, index, { P1: now, P2: now, P3: now })
  assert.equal(stats.solvedCount, 3)
  assert.equal(stats.concentration, 100)
  assert.equal(stats.achievements.find((item) => item.id === 'works3').unlocked, true)
  assert.equal(stats.achievements.find((item) => item.id === 'complete').unlocked, true)
})

test('problemsToNext is based on unique problems', () => {
  const stats = computeStats(dataset, index, { P1: now })
  assert.equal(stats.nextRank.min, 35)
  assert.equal(stats.problemsToNext, 1)
})

test('tag achievements count unique solved problems across tagged works', () => {
  const stats = computeStats(dataset, index, { P1: now, P2: now }, tagMap)
  const key = stats.achievements.find((item) => item.id === 'key')
  assert.equal(key.progress, '2 / 10')
  assert.equal(key.unlocked, false)
  const touhou = stats.achievements.find((item) => item.id === 'touhou')
  assert.equal(touhou.progress, '1 / 10')
  const galgame = stats.achievements.find((item) => item.id === 'category-galgame')
  assert.equal(galgame.progress, '2 / 10')
})

test('tag achievements stay locked when no tag map is loaded', () => {
  const stats = computeStats(dataset, index, { P1: now, P2: now })
  const key = stats.achievements.find((item) => item.id === 'key')
  assert.equal(key.progress, '0 / 10')
})

test('does not expose time-based statistics', () => {
  const stats = computeStats(dataset, index, { P1: now })
  assert.equal('streak' in stats, false)
  assert.equal('todayAdded' in stats, false)
  assert.equal('recent' in stats, false)
  assert.equal('lastSolvedAt' in stats, false)
})

test('ranks follow concentration thresholds', () => {
  assert.equal(rankFor(0).name, 'Newbie')
  assert.equal(rankFor(0.5).name, 'Pupil')
  assert.equal(rankFor(5).name, 'Expert')
  assert.equal(rankFor(100).name, 'ACGN tourist')
})

test('empty solved state is safe', () => {
  const stats = computeStats(dataset, index, {})
  assert.equal(stats.concentration, 0)
  assert.equal(stats.rank.name, 'Newbie')
  assert.equal(stats.achievements.every((item) => !item.unlocked), true)
})
