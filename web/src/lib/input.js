const URL_RULES = [
  {
    re: /https?:\/\/(?:www\.)?luogu\.com\.cn\/problem\/([pb])\s*(\d{1,7})/gi,
    map: (match) => `${match[1].toUpperCase()}${Number(match[2])}`,
  },
  {
    re: /https?:\/\/(?:www\.)?uoj\.ac\/problem\/(\d{1,7})/gi,
    map: (match) => `UOJ${Number(match[1])}`,
  },
  {
    re: /https?:\/\/(?:www\.)?qoj\.ac\/problem\/(\d{1,7})/gi,
    map: (match) => `QOJ${Number(match[1])}`,
  },
]

const ID_RULE =
  /(?<![A-Za-z0-9])(?:([pb])\s*(\d{1,7})|(uoj|qoj)\s*#?\s*(\d{1,7}))(?![0-9])/gi

/**
 * Extract problem keys from a blob of text.
 *
 * Accepted forms include `P1001`, `B3655`, `UOJ#1094`, `QOJ 18255`, and full
 * URLs on Luogu / UOJ / QOJ.  Unknown keys are returned too; the caller decides
 * whether they exist in the current dataset.
 */
export function parseProblemInput(text) {
  const normalized = String(text ?? '')
    .normalize('NFKC')
    .replaceAll('\u00a0', ' ')
  const keys = new Set()

  for (const rule of URL_RULES) {
    for (const match of normalized.matchAll(rule.re)) {
      keys.add(rule.map(match))
    }
  }

  for (const match of normalized.matchAll(ID_RULE)) {
    if (match[1]) {
      keys.add(`${match[1].toUpperCase()}${Number(match[2])}`)
    } else {
      keys.add(`${match[3].toUpperCase()}${Number(match[4])}`)
    }
  }

  return { keys: [...keys] }
}
