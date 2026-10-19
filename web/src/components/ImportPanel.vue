<script setup>
import { computed, ref } from 'vue'
import { useSolved } from '../composables/useSolved.js'
import { parseProblemInput } from '../lib/input.js'

const props = defineProps({
  dataset: { type: Object, required: true },
  index: { type: Object, required: true },
})

const { solved, mark, clearAll, exportPayload, importPayload } = useSolved()

const text = ref('')
const report = ref(null)
const fileInput = ref(null)

const validKeys = computed(() => new Set(Object.keys(props.index.problems)))

const recordCount = computed(
  () => Object.keys(solved).filter((key) => props.index.problems[key]).length,
)
const staleCount = computed(
  () => Object.keys(solved).filter((key) => !props.index.problems[key]).length,
)

function chips(keys, limit = 12) {
  const shown = keys.slice(0, limit)
  const rest = keys.length - shown.length
  return rest > 0 ? `${shown.join('、')} 等 ${keys.length} 个` : shown.join('、')
}

function importText() {
  const source = text.value
  const { keys } = parseProblemInput(source)
  if (!keys.length) {
    report.value = {
      tone: 'warning',
      title: '没有识别到题号',
      lines: ['支持 P1001、B3655、UOJ#1094、QOJ18255，以及对应 OJ 的题目链接。'],
      unknown: [],
    }
    return
  }

  const added = []
  const duplicate = []
  const unknown = []
  for (const key of keys) {
    if (!props.index.problems[key]) {
      unknown.push(key)
    } else if (solved[key]) {
      duplicate.push(key)
    } else if (mark(key)) {
      added.push(key)
    }
  }

  const lines = [
    `识别 ${keys.length} 个题号：新增 ${added.length}，已记录 ${duplicate.length}${
      unknown.length ? `，未收录 ${unknown.length}` : ''
    }。`,
  ]
  if (added.length) lines.push(`新增：${chips(added)}`)
  if (unknown.length) lines.push(`未收录（已跳过）：${chips(unknown)}`)

  report.value = {
    tone: added.length ? 'positive' : unknown.length ? 'warning' : 'info',
    title: added.length
      ? `成功记下 ${added.length} 道题`
      : unknown.length
        ? '没有新增记录'
        : '这些题都已经记录过啦',
    lines,
    unknown,
  }
  text.value = ''
}

async function handleBackup(event) {
  const file = event.target.files?.[0]
  if (!file) return
  try {
    const parsed = JSON.parse(await file.text())
    const result = importPayload(parsed, validKeys.value)
    report.value = {
      tone: result.added ? 'positive' : 'info',
      title: result.added ? `备份导入成功，新增 ${result.added} 道` : '备份中没有新的记录',
      lines: [
        `新增 ${result.added}，已存在 ${result.duplicate}，无效 ${result.invalid}，题单中不存在 ${result.unknown}。`,
      ],
      unknown: [],
    }
  } catch {
    report.value = {
      tone: 'negative',
      title: '备份文件读取失败',
      lines: ['请选择由本页面导出的 JSON 备份文件。'],
      unknown: [],
    }
  } finally {
    event.target.value = ''
  }
}

function exportBackup() {
  const payload = exportPayload(props.dataset)
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `acgn-solved-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function clearRecords() {
  const count = Object.keys(solved).length
  if (!count) return
  if (!window.confirm(`确定清空全部 ${count} 条做题记录吗？此操作无法撤销。`)) return
  clearAll()
  report.value = {
    tone: 'info',
    title: '记录已清空',
    lines: ['可以重新粘贴题号。'],
    unknown: [],
  }
}
</script>

<template>
  <section id="record">
    <div class="ui stackable grid">
      <div class="wide column">
        <div class="ui segment">
          <div class="ui form">
            <div class="field">
              <label for="import-text">粘贴你的 AC 记录</label>
              <textarea
                id="import-text"
                v-model="text"
                rows="5"
                spellcheck="false"
                placeholder="例如：P12533 P3694 UOJ#1094 QOJ18255&#10;也可以直接粘贴整段文字或题目链接，会自动提取题号。"
              ></textarea>
            </div>
            <button
              type="button"
              class="ui primary button"
              :disabled="!text.trim()"
              @click="importText"
            >
              <i class="plus icon"></i>
              增量导入
            </button>
            <button type="button" class="ui button" @click="clearRecords">清空所有做题记录</button>
          </div>

          <div v-if="report" class="ui message report-message" :class="report.tone">
            <div class="header">{{ report.title }}</div>
            <p v-for="line in report.lines" :key="line">{{ line }}</p>
            <div v-if="report.unknown.length" class="ui labels">
              <span v-for="key in report.unknown.slice(0, 20)" :key="key" class="ui mini label">
                {{ key }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
