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
})

const DARK_TEXT_DIFFICULTIES = new Set([
  UNSET_DIFFICULTY,
  '暂无评定',
  '普及',
])

export function difficultyLabel(difficulty) {
  return difficulty || UNSET_DIFFICULTY
}

export function difficultyWeight(difficulty) {
  return DIFFICULTY_WEIGHTS[difficulty] ?? 1
}

export function difficultyColor(difficulty) {
  return DIFFICULTY_COLORS[difficulty] ?? DIFFICULTY_COLORS[UNSET_DIFFICULTY]
}

export function difficultyTextColor(difficulty) {
  return DARK_TEXT_DIFFICULTIES.has(difficultyLabel(difficulty))
    ? 'rgba(0, 0, 0, 0.7)'
    : '#fff'
}

export function difficultyStyle(difficulty) {
  return {
    backgroundColor: difficultyColor(difficulty),
    color: difficultyTextColor(difficulty),
  }
}

export function difficultyTitle(difficulty) {
  return `难度 ${difficultyLabel(difficulty)}，权重 ${difficultyWeight(difficulty)} 点`
}
