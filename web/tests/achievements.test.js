import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { ACHIEVEMENTS } from '../src/lib/achievements.js'
import { UNSET_DIFFICULTY, difficultyWeight } from '../src/lib/difficulty.js'

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
  assert.equal(ACHIEVEMENTS.some((achievement) => achievement.id === 'complete'), false)
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

test('every tag achievement is reachable with the current tags or unset difficulties', () => {
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
    let known = 0
    let unset = 0
    for (const key of taggedKeys.get(achievement.tag) ?? []) {
      const difficulty = dataset.problems[key]?.difficulty
      if (difficulty === UNSET_DIFFICULTY) {
        unset += 1
      } else {
        known += difficultyWeight(difficulty)
      }
    }
    const maxPossible = known + unset * difficultyWeight('NOI/NOI+/CTS')
    assert.ok(
      maxPossible >= achievement.threshold,
      `${achievement.name} can only reach ${maxPossible} difficulty points, threshold is ${achievement.threshold}`,
    )
  }
})

test('problem-count achievements use the configured difficulty thresholds', () => {
  const weighted = ACHIEVEMENTS.filter(
    (achievement) =>
      achievement.metric === 'weightedSolved' || achievement.metric === 'tag',
  )
  assert.ok(weighted.length > 0)
  for (const achievement of weighted) {
    assert.equal(achievement.unit, ' 点', `${achievement.name} should use points`)
  }

  const categories = ACHIEVEMENTS.filter((achievement) => achievement.metric === 'tag')
  assert.ok(categories.every((achievement) => achievement.threshold === 50))

  const growth = ACHIEVEMENTS.filter(
    (achievement) => achievement.metric === 'weightedSolved',
  )
  assert.deepEqual(
    growth.map((achievement) => achievement.threshold),
    [1, 100, 300, 500, 700, 1000],
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
