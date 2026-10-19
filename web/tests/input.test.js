import test from 'node:test'
import assert from 'node:assert/strict'
import { parseProblemInput } from '../src/lib/input.js'

test('extracts plain problem ids from text', () => {
  const { keys } = parseProblemInput('今天过了 P12533、P3694 和 B3655，UOJ#1094 还没动，QOJ18255 也不会。')
  assert.deepEqual(keys.sort(), ['B3655', 'P12533', 'P3694', 'QOJ18255', 'UOJ1094'].sort())
})

test('extracts ids from URLs', () => {
  const { keys } = parseProblemInput(`
    https://www.luogu.com.cn/problem/P12533
    https://uoj.ac/problem/1094
    https://qoj.ac/problem/18255
  `)
  assert.deepEqual(keys.sort(), ['P12533', 'QOJ18255', 'UOJ1094'].sort())
})

test('deduplicates and normalizes case / width', () => {
  const { keys } = parseProblemInput('p12533 P12533 Ｐ１２５３３ UOJ#01094 uoj1094')
  assert.deepEqual(keys.sort(), ['P12533', 'UOJ1094'].sort())
})

test('does not match ids embedded in words or overly long numbers', () => {
  const { keys } = parseProblemInput('RP1000 XP123456 P12345678 ABC123')
  assert.deepEqual(keys, [])
})

test('returns an empty list for empty input', () => {
  assert.deepEqual(parseProblemInput('').keys, [])
  assert.deepEqual(parseProblemInput(null).keys, [])
})
