import { reactive, watch } from 'vue'
import { readJSON, writeJSON } from '../lib/storage.js'

export const SOLVED_STORAGE_KEY = 'acgn-problem/solved/v1'

function loadSolved() {
  const raw = readJSON(SOLVED_STORAGE_KEY, {})
  const result = {}
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    for (const key of Object.keys(raw)) {
      if (key) result[key] = true
    }
  }
  return result
}

const state = reactive(loadSolved())
let suppressSave = false

watch(
  state,
  () => {
    if (suppressSave) return
    writeJSON(SOLVED_STORAGE_KEY, state)
  },
  { deep: true },
)

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key !== SOLVED_STORAGE_KEY || !event.newValue) return
    let parsed
    try {
      parsed = JSON.parse(event.newValue)
    } catch {
      return
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return
    const next = {}
    for (const key of Object.keys(parsed)) {
      if (key) next[key] = true
    }
    suppressSave = true
    for (const key of Object.keys(state)) delete state[key]
    Object.assign(state, next)
    suppressSave = false
  })
}

function isSolved(key) {
  return Object.prototype.hasOwnProperty.call(state, key)
}

function mark(key) {
  if (isSolved(key)) return false
  state[key] = true
  return true
}

function markMany(keys) {
  let added = 0
  for (const key of keys) {
    if (mark(key)) added += 1
  }
  return added
}

function unmark(key) {
  if (!isSolved(key)) return false
  delete state[key]
  return true
}

function toggle(key) {
  if (isSolved(key)) {
    unmark(key)
    return false
  }
  mark(key)
  return true
}

function clearAll() {
  for (const key of Object.keys(state)) delete state[key]
}

function exportPayload(dataset) {
  return {
    format: 'acgn-problem-solved',
    version: 1,
    exportedAt: new Date().toISOString(),
    source: dataset?.source?.url ?? null,
    solved: { ...state },
  }
}

function importPayload(payload, validKeys) {
  const source = payload?.solved && typeof payload.solved === 'object' ? payload.solved : payload
  if (!source || typeof source !== 'object' || Array.isArray(source)) {
    return { added: 0, duplicate: 0, invalid: 1, unknown: 0 }
  }
  let added = 0
  let duplicate = 0
  let invalid = 0
  let unknown = 0
  for (const key of Object.keys(source)) {
    if (!key) {
      invalid += 1
      continue
    }
    if (validKeys && !validKeys.has(key)) {
      unknown += 1
      continue
    }
    if (isSolved(key)) {
      duplicate += 1
      continue
    }
    state[key] = true
    added += 1
  }
  return { added, duplicate, invalid, unknown }
}

export function useSolved() {
  return {
    solved: state,
    isSolved,
    mark,
    markMany,
    unmark,
    toggle,
    clearAll,
    exportPayload,
    importPayload,
  }
}
