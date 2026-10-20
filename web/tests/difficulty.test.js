import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import {
  DIFFICULTY_WEIGHTS,
  UNSET_DIFFICULTY,
  difficultyColor,
  difficultyLabel,
  difficultyWeight,
} from '../src/lib/difficulty.js'

const dataset = JSON.parse(
  readFileSync(fileURLToPath(new URL('../public/data/acgn.json', import.meta.url)), 'utf8'),
)

const DIFFICULTIES = new Set([
  '暂无评定',
  '入门',
  '普及−',
  '普及',
  '普及+/提高−',
  '提高',
  '提高+/省选−',
  '省选/NOI−',
  'NOI/NOI+/CTS',
  '未设置难度',
])

test('every problem has a known difficulty label', () => {
  for (const [key, problem] of Object.entries(dataset.problems)) {
    assert.equal(typeof problem.difficulty, 'string', `${key} has no difficulty`)
    assert.ok(DIFFICULTIES.has(problem.difficulty), `${key} has ${problem.difficulty}`)
  }
})

test('difficulty weights rise with difficulty and have a safe fallback', () => {
  const order = [
    '入门',
    '普及−',
    '普及',
    '普及+/提高−',
    '提高',
    '提高+/省选−',
    '省选/NOI−',
    'NOI/NOI+/CTS',
  ]
  for (let i = 1; i < order.length; i += 1) {
    assert.ok(
      difficultyWeight(order[i]) > difficultyWeight(order[i - 1]),
      `${order[i]} should outweigh ${order[i - 1]}`,
    )
  }
  assert.equal(difficultyWeight('入门'), 1)
  assert.equal(difficultyWeight('NOI/NOI+/CTS'), 5)
  assert.equal(difficultyWeight(UNSET_DIFFICULTY), 1)
  assert.equal(difficultyWeight('unknown'), 1)
  assert.equal(difficultyLabel(''), UNSET_DIFFICULTY)
  assert.equal(difficultyColor('NOI/NOI+/CTS'), 'red')
  assert.equal(difficultyColor(UNSET_DIFFICULTY), '')
  assert.equal(DIFFICULTY_WEIGHTS['暂无评定'], 1)
})

test('Luogu difficulties are populated when the problem is in the snapshot', () => {
  const luogu = Object.values(dataset.problems).filter((problem) => problem.oj === 'luogu')
  const withDifficulty = luogu.filter((problem) => problem.difficulty !== '未设置难度')
  assert.ok(withDifficulty.length > 0)
  assert.ok(withDifficulty.length >= luogu.length * 0.9)
})
