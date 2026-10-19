export const OJ_META = {
  luogu: { key: 'luogu', label: '洛谷', short: 'Luogu', className: 'oj-luogu' },
  uoj: { key: 'uoj', label: 'UOJ', short: 'UOJ', className: 'oj-uoj' },
  qoj: { key: 'qoj', label: 'QOJ', short: 'QOJ', className: 'oj-qoj' },
}

export function ojMeta(oj) {
  return OJ_META[oj] ?? { key: oj, label: oj, short: oj, className: 'oj-other' }
}

export function normalizeSearch(value) {
  return String(value ?? '')
    .normalize('NFKC')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
}

function haystack(parts) {
  return normalizeSearch(parts.filter(Boolean).join(' \u0000 '))
}

function rowKey(ref) {
  return typeof ref === 'string' ? ref : ref.key
}

function rowTitle(ref, problem) {
  return (typeof ref === 'string' ? '' : ref.title) || problem.title
}

/**
 * Build the lookup structures used by the table and dashboard. Rows are the
 * flattened (work, problem) pairs. A work may contain the same problem link
 * twice (e.g. a remaster with the same URL), so rows keep their own title and
 * are never collapsed.
 */
export function buildIndex(dataset) {
  const problems = dataset.problems ?? {}
  const works = dataset.works ?? []
  const workById = new Map(works.map((work) => [work.id, work]))
  const problemWorks = new Map()
  const rows = []

  for (const [key, problem] of Object.entries(problems)) {
    const linkedWorks = (problem.works ?? []).map((id) => workById.get(id)).filter(Boolean)
    problemWorks.set(key, linkedWorks)
  }

  for (const work of works) {
    for (const ref of work.problems ?? []) {
      const key = rowKey(ref)
      const problem = problems[key]
      if (!problem) continue
      const title = rowTitle(ref, problem)
      rows.push({
        key,
        title,
        workId: work.id,
        work,
        problem,
        search: haystack([
          key,
          title,
          problem.title,
          problem.id,
          work.name,
          work.original,
        ]),
      })
    }
  }

  const ojCounts = {}
  for (const problem of Object.values(problems)) {
    ojCounts[problem.oj] = (ojCounts[problem.oj] ?? 0) + 1
  }

  return {
    dataset,
    works,
    problems,
    rows,
    workById,
    problemWorks,
    ojCounts,
    problemCount: Object.keys(problems).length,
  }
}

export function displayWorkFor(problem, index) {
  const works = index.problemWorks.get(problem.key) ?? []
  return works[0] ?? null
}
