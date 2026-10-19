import { ACHIEVEMENTS } from './achievements.js'
import { ojMeta } from './dataset.js'

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

function countSolvedInWorks(workNames, dataset, solvedSet) {
  const names = new Set(workNames)
  const solved = new Set()
  for (const work of dataset.works) {
    if (!names.has(work.name)) continue
    for (const ref of work.problems) {
      const key = refKey(ref)
      if (solvedSet.has(key)) solved.add(key)
    }
  }
  return solved.size
}

export function computeStats(dataset, index, solved) {
  const validSolvedKeys = Object.keys(solved).filter((key) => index.problems[key])
  const solvedSet = new Set(validSolvedKeys)

  const uniquePercent = index.problemCount
    ? (validSolvedKeys.length / index.problemCount) * 100
    : 0
  // Concentration is per unique problem: multi-work problems count once.
  const concentration = uniquePercent

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
    touchedWorkCount: touchedWorks.length,
    problemCount: index.problemCount,
  }
  const worksMetricCache = new Map()

  const achievements = ACHIEVEMENTS.map((config) => {
    let value
    if (config.metric === 'works') {
      if (!worksMetricCache.has(config.id)) {
        worksMetricCache.set(
          config.id,
          countSolvedInWorks(config.works ?? [], dataset, solvedSet),
        )
      }
      value = worksMetricCache.get(config.id)
    } else {
      value = metrics[config.metric] ?? 0
    }

    const threshold =
      config.threshold === 'problemCount' ? index.problemCount : config.threshold
    return {
      id: config.id,
      icon: config.icon,
      name: config.name,
      desc: config.desc,
      unlocked: threshold > 0 && value >= threshold,
      progress: `${Math.min(value, threshold)} / ${threshold}${config.unit ?? ''}`,
    }
  })

  const rank = rankFor(concentration)
  const nextRank = RANKS.find((candidate) => candidate.min > concentration) ?? null
  const problemsToNext = nextRank
    ? Math.max(
        0,
        Math.ceil((index.problemCount * nextRank.min) / 100) - validSolvedKeys.length,
      )
    : 0

  return {
    solvedCount: validSolvedKeys.length,
    problemCount: index.problemCount,
    workCount: dataset.works.length,
    touchedWorkCount: touchedWorks.length,
    concentration,
    uniquePercent,
    rank,
    nextRank,
    problemsToNext,
    ojStats,
    achievements,
    unlockedAchievements: achievements.filter((achievement) => achievement.unlocked).length,
    achievementCount: achievements.length,
  }
}
