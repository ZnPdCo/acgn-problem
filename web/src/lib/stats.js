import { ACHIEVEMENTS } from './achievements.js'
import { ojMeta } from './dataset.js'
import { difficultyWeight } from './difficulty.js'
import { formatWeight } from './format.js'

/**
 * 100% concentration is reached at half of the total difficulty weight. The
 * remaining half is headroom, so the rank does not require a full clear.
 */
export const CONCENTRATION_TARGET = 0.5

export const RANKS = [
  { min: 0, level: 'Lv.0', name: 'Newbie' },
  { min: 0.0001, level: 'Lv.1', name: 'Pupil' },
  { min: 2, level: 'Lv.2', name: 'Specialist' },
  { min: 5, level: 'Lv.3', name: 'Expert' },
  { min: 10, level: 'Lv.4', name: 'Candidate Master' },
  { min: 20, level: 'Lv.5', name: 'Master' },
  { min: 35, level: 'Lv.6', name: 'International Master' },
  { min: 50, level: 'Lv.7', name: 'Grandmaster' },
  { min: 70, level: 'Lv.8', name: 'International Grandmaster' },
  { min: 90, level: 'Lv.9', name: 'Legendary Grandmaster' },
  { min: 100, level: 'MAX', name: 'ACGN tourist' },
]

export function rankFor(percent) {
  let current = RANKS[0]
  for (const rank of RANKS) {
    if (percent >= rank.min) current = rank
  }
  return current
}

function refKey(ref) {
  return typeof ref === 'string' ? ref : ref.key
}

function touchCount(work, solvedSet) {
  return (work.problems ?? []).reduce(
    (count, ref) => count + (solvedSet.has(refKey(ref)) ? 1 : 0),
    0,
  )
}

function problemWeight(problem) {
  return difficultyWeight(problem?.difficulty)
}

function weightedSolvedWithTag(tag, dataset, problems, solvedSet, tagMap) {
  const solved = new Set()
  for (const work of dataset.works) {
    if (!(tagMap[work.name] ?? []).includes(tag)) continue
    for (const ref of work.problems ?? []) {
      const key = refKey(ref)
      if (solvedSet.has(key)) solved.add(key)
    }
  }

  let weight = 0
  for (const key of solved) {
    const problem = problems[key]
    if (problem) weight += problemWeight(problem)
  }
  return weight
}

function formatMetric(value, weighted) {
  return weighted ? formatWeight(value) : String(Math.round(value))
}

export function computeStats(dataset, index, solved, tagMap = {}) {
  const validSolvedKeys = Object.keys(solved).filter((key) => index.problems[key])
  const solvedSet = new Set(validSolvedKeys)

  const uniquePercent = index.problemCount
    ? (validSolvedKeys.length / index.problemCount) * 100
    : 0

  const totalWeight = Object.values(index.problems).reduce(
    (sum, problem) => sum + problemWeight(problem),
    0,
  )
  const solvedWeight = validSolvedKeys.reduce(
    (sum, key) => sum + problemWeight(index.problems[key]),
    0,
  )
  const targetWeight = totalWeight * CONCENTRATION_TARGET
  // Multi-work problems are deduplicated by key before their weight is added.
  const concentration = targetWeight > 0
    ? Math.min(100, (solvedWeight / targetWeight) * 100)
    : 0

  const workStats = dataset.works.map((work) => ({
    ...work,
    total: work.problems.length,
    done: touchCount(work, solvedSet),
  }))
  const touchedWorks = workStats.filter((work) => work.done > 0)

  const ojStats = Object.keys(index.ojCounts).map((oj) => {
    const meta = ojMeta(oj)
    let solvedCount = 0
    for (const problem of Object.values(index.problems)) {
      if (problem.oj === oj && solvedSet.has(problem.key)) solvedCount += 1
    }
    return {
      ...meta,
      total: index.ojCounts[oj],
      solved: solvedCount,
      percent: index.ojCounts[oj] ? (solvedCount / index.ojCounts[oj]) * 100 : 0,
    }
  })

  const metrics = {
    solvedCount: validSolvedKeys.length,
    weightedSolved: solvedWeight,
    touchedWorkCount: touchedWorks.length,
    problemCount: index.problemCount,
  }
  const tagMetricCache = new Map()

  const achievements = ACHIEVEMENTS.map((config) => {
    let value
    if (config.metric === 'tag') {
      if (!tagMetricCache.has(config.tag)) {
        tagMetricCache.set(
          config.tag,
          weightedSolvedWithTag(
            config.tag,
            dataset,
            index.problems,
            solvedSet,
            tagMap,
          ),
        )
      }
      value = tagMetricCache.get(config.tag)
    } else {
      value = metrics[config.metric] ?? 0
    }

    const threshold =
      config.threshold === 'problemCount' ? index.problemCount : config.threshold
    const weighted = config.metric === 'weightedSolved' || config.metric === 'tag'
    const unit = config.unit ?? (weighted ? ' 点' : '')
    const shownValue = Math.min(value, threshold)
    return {
      id: config.id,
      icon: config.icon,
      name: config.name,
      desc: config.desc,
      unlocked: threshold > 0 && value >= threshold,
      progress: `${formatMetric(shownValue, weighted)} / ${formatMetric(threshold, weighted)}${unit}`,
      weighted,
    }
  })

  const rank = rankFor(concentration)
  const nextRank = RANKS.find((candidate) => candidate.min > concentration) ?? null
  const weightToNext = nextRank && targetWeight > 0
    ? Math.max(0, (targetWeight * nextRank.min) / 100 - solvedWeight)
    : 0

  return {
    solvedCount: validSolvedKeys.length,
    solvedWeight,
    totalWeight,
    targetWeight,
    problemCount: index.problemCount,
    workCount: dataset.works.length,
    touchedWorkCount: touchedWorks.length,
    concentration,
    uniquePercent,
    rank,
    nextRank,
    weightToNext,
    ojStats,
    achievements,
    unlockedAchievements: achievements.filter((achievement) => achievement.unlocked).length,
    achievementCount: achievements.length,
  }
}
