/**
 * Difficulty metadata shared by the solver table, dashboard and statistics.
 *
 * Luogu's difficulty levels are ordered; the weights make one NOI/NOI+/CTS
 * problem worth five beginner problems. Problems without a difficulty (mostly
 * UOJ/QOJ entries that still need filling in `data/difficulty.json`) are
 * treated as beginner level so solving them is never worthless.
 */
export const UNSET_DIFFICULTY = '未设置难度'

export const DIFFICULTY_WEIGHTS = Object.freeze({
  '暂无评定': 1,
  '入门': 1,
  '普及−': 1.5,
  '普及': 2,
  '普及+/提高−': 2.5,
  '提高': 3,
  '提高+/省选−': 3.5,
  '省选/NOI−': 4,
  'NOI/NOI+/CTS': 5,
  [UNSET_DIFFICULTY]: 1,
})

const DIFFICULTY_COLORS = Object.freeze({
  '入门': 'green',
  '普及−': 'teal',
  '普及': 'teal',
  '普及+/提高−': 'blue',
  '提高': 'blue',
  '提高+/省选−': 'olive',
  '省选/NOI−': 'orange',
  'NOI/NOI+/CTS': 'red',
})

export function difficultyLabel(difficulty) {
  return difficulty || UNSET_DIFFICULTY
}

export function difficultyWeight(difficulty) {
  return DIFFICULTY_WEIGHTS[difficulty] ?? 1
}

export function difficultyColor(difficulty) {
  return DIFFICULTY_COLORS[difficulty] ?? ''
}

export function difficultyTitle(difficulty) {
  return `难度 ${difficultyLabel(difficulty)}，权重 ${difficultyWeight(difficulty)} 点`
}
