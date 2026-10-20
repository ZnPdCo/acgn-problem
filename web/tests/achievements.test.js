import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { ACHIEVEMENTS } from '../src/lib/achievements.js'
import { difficultyWeight } from '../src/lib/difficulty.js'

const dataset = JSON.parse(
  readFileSync(fileURLToPath(new URL('../public/data/acgn.json', import.meta.url)), 'utf8'),
)
const tagMap = JSON.parse(
  readFileSync(fileURLToPath(new URL('../public/data/tags.json', import.meta.url)), 'utf8'),
)
const workNames = dataset.works.map((work) => work.name)

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
    if (achievement.metric === 'tag') {
      assert.match(achievement.tag, /^[a-z][a-z0-9-]*$/, `bad tag: ${achievement.id}`)
      assert.equal('works' in achievement, false, `${achievement.id} still hardcodes works`)
    }
  }
})

test('all achievement definitions live in one external config', () => {
  assert.ok(ACHIEVEMENTS.length >= 10)
  assert.ok(ACHIEVEMENTS.some((achievement) => achievement.id === 'category-yuri'))
  assert.ok(ACHIEVEMENTS.some((achievement) => achievement.id === 'category-galgame'))
  assert.ok(ACHIEVEMENTS.some((achievement) => achievement.id === 'complete'))
})

test('tag definitions use unique slugs', () => {
  const tags = ACHIEVEMENTS.filter((achievement) => achievement.metric === 'tag').map(
    (achievement) => achievement.tag,
  )
  assert.equal(new Set(tags).size, tags.length)
})

test('acgn.json does not embed tags', () => {
  for (const work of dataset.works) {
    assert.equal('tags' in work, false, `${work.name} still embeds tags`)
  }
})

test('public/data/tags.json covers exactly the works in the dataset', () => {
  assert.deepEqual(Object.keys(tagMap).sort(), [...workNames].sort())
  for (const name of workNames) {
    assert.ok(Array.isArray(tagMap[name]), `${name} should map to a tag list`)
    for (const tag of tagMap[name]) {
      assert.equal(typeof tag, 'string')
      assert.equal(tag.trim(), tag, `${name} has a padded tag`)
      assert.equal(/\s/.test(tag), false, `${name} has a tag containing whitespace`)
    }
    assert.equal(new Set(tagMap[name]).size, tagMap[name].length, `${name} repeats a tag`)
  }
})

test('untagged works are listed after tagged ones', () => {
  const entries = Object.entries(tagMap)
  const firstUntagged = entries.findIndex(([, tags]) => tags.length === 0)
  if (firstUntagged === -1) return
  assert.equal(
    entries.slice(firstUntagged).every(([, tags]) => tags.length === 0),
    true,
    'untagged works should form a block at the end of public/data/tags.json',
  )
})

test('every tag achievement is reachable with the current tags', () => {
  const taggedKeys = new Map()
  for (const work of dataset.works) {
    for (const tag of tagMap[work.name] ?? []) {
      if (!taggedKeys.has(tag)) taggedKeys.set(tag, new Set())
      for (const ref of work.problems ?? []) {
        taggedKeys.get(tag).add(typeof ref === 'string' ? ref : ref.key)
      }
    }
  }
  for (const achievement of ACHIEVEMENTS) {
    if (achievement.metric !== 'tag') continue
    let total = 0
    for (const key of taggedKeys.get(achievement.tag) ?? []) {
      total += difficultyWeight(dataset.problems[key]?.difficulty)
    }
    assert.ok(
      total >= achievement.threshold,
      `${achievement.name} only has ${total} difficulty points, threshold is ${achievement.threshold}`,
    )
  }
})

test('problem-count achievements use difficulty points', () => {
  const weighted = ACHIEVEMENTS.filter(
    (achievement) =>
      achievement.metric === 'weightedSolved' || achievement.metric === 'tag',
  )
  assert.ok(weighted.length > 0)
  for (const achievement of weighted) {
    assert.equal(achievement.unit, ' 点', `${achievement.name} should use points`)
  }
  assert.equal(
    ACHIEVEMENTS.find((achievement) => achievement.id === 'complete').metric,
    'solvedCount',
  )
})

test('every tag used by a work belongs to a category achievement', () => {
  const knownTags = new Set(
    ACHIEVEMENTS.filter((achievement) => achievement.metric === 'tag').map(
      (achievement) => achievement.tag,
    ),
  )
  for (const [name, tags] of Object.entries(tagMap)) {
    for (const tag of tags) {
      assert.ok(knownTags.has(tag), `${name} uses unknown tag ${tag}`)
    }
  }
})
