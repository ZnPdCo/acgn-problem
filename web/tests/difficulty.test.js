import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import {
  DIFFICULTY_WEIGHTS,
  UNSET_DIFFICULTY,
  difficultyColor,
  difficultyLabel,
  difficultyStyle,
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
  assert.equal(DIFFICULTY_WEIGHTS['暂无评定'], 1)
})

test('difficulty colors use the project palette', () => {
  const expected = {
    '暂无评定': 'rgb(191, 191, 191)',
    '入门': 'rgb(254, 76, 97)',
    '普及−': 'rgb(243, 156, 17)',
    '普及': 'rgb(255, 193, 22)',
    '普及+/提高−': 'rgb(82, 196, 26)',
    '提高': 'rgb(19, 194, 194)',
    '提高+/省选−': 'rgb(52, 152, 219)',
    '省选/NOI−': 'rgb(157, 61, 207)',
    'NOI/NOI+/CTS': 'rgb(14, 29, 105)',
    [UNSET_DIFFICULTY]: 'rgb(191, 191, 191)',
  }
  for (const [label, color] of Object.entries(expected)) {
    assert.equal(difficultyColor(label), color)
  }
  assert.equal(difficultyColor('unknown'), 'rgb(191, 191, 191)')
  assert.equal(difficultyStyle('入门').color, '#fff')
  assert.equal(difficultyStyle('普及').color, 'rgba(0, 0, 0, 0.7)')
})

test('Luogu difficulties are populated when the problem is in the snapshot', () => {
  const luogu = Object.values(dataset.problems).filter((problem) => problem.oj === 'luogu')
  const withDifficulty = luogu.filter((problem) => problem.difficulty !== '未设置难度')
  assert.ok(withDifficulty.length > 0)
  assert.ok(withDifficulty.length >= luogu.length * 0.9)
})

test('manual Luogu overrides fill snapshot gaps', () => {
  assert.equal(dataset.problems.P15851.difficulty, 'NOI/NOI+/CTS')
  assert.equal(dataset.problems.P8489.difficulty, '省选/NOI−')
  assert.equal(dataset.problems.P4691.difficulty, '省选/NOI−')
})
