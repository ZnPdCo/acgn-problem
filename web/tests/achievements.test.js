import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { ACHIEVEMENTS } from '../src/lib/achievements.js'

const dataset = JSON.parse(
  readFileSync(fileURLToPath(new URL('../public/data/acgn.json', import.meta.url)), 'utf8'),
)
const works = new Map(dataset.works.map((work) => [work.name, work]))

test('achievement configs have unique ids and required fields', () => {
  const ids = new Set()
  for (const achievement of ACHIEVEMENTS) {
    assert.ok(achievement.id, 'missing id')
    assert.equal(ids.has(achievement.id), false, `duplicate id: ${achievement.id}`)
    ids.add(achievement.id)
    assert.ok(achievement.name, `missing name: ${achievement.id}`)
    assert.ok(achievement.desc, `missing desc: ${achievement.id}`)
    assert.ok(achievement.icon, `missing icon: ${achievement.id}`)
    assert.ok(achievement.metric, `missing metric: ${achievement.id}`)
    assert.ok(achievement.threshold, `missing threshold: ${achievement.id}`)
    if (achievement.metric === 'works') {
      assert.ok(Array.isArray(achievement.works) && achievement.works.length > 0)
    }
  }
})

test('all achievement definitions live in one external config', () => {
  assert.ok(ACHIEVEMENTS.length >= 10)
  assert.ok(ACHIEVEMENTS.some((achievement) => achievement.id === 'category-yuri'))
  assert.ok(ACHIEVEMENTS.some((achievement) => achievement.id === 'category-galgame'))
  assert.ok(ACHIEVEMENTS.some((achievement) => achievement.id === 'complete'))
})

test('works-based achievements reference real works and enough problems', () => {
  for (const achievement of ACHIEVEMENTS) {
    if (achievement.metric !== 'works') continue
    const missing = achievement.works.filter((name) => !works.has(name))
    assert.deepEqual(missing, [], `${achievement.name} has unknown works`)
    const total = achievement.works.reduce(
      (count, name) => count + (works.get(name)?.problems.length ?? 0),
      0,
    )
    assert.ok(
      total >= achievement.threshold,
      `${achievement.name} only has ${total} problems, threshold is ${achievement.threshold}`,
    )
  }
})
