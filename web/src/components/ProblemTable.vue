<script setup>
import { computed, ref } from 'vue'
import { useSolved } from '../composables/useSolved.js'
import { normalizeSearch, ojMeta } from '../lib/dataset.js'

const props = defineProps({
  dataset: { type: Object, required: true },
  index: { type: Object, required: true },
})

const { solved, toggle } = useSolved()

const query = ref('')
const status = ref('all')
const ojFilter = ref('all')

const OJ_ORDER = ['luogu', 'uoj', 'qoj']

const rowsByWork = computed(() => {
  const map = new Map()
  for (const work of props.dataset.works) map.set(work.id, [])
  for (const row of props.index.rows) {
    const bucket = map.get(row.workId)
    if (bucket) bucket.push(row)
  }
  return map
})

const ojOptions = computed(() =>
  OJ_ORDER.filter((oj) => props.index.ojCounts[oj]).map((oj) => ({
    key: oj,
    label: ojMeta(oj).label,
  })),
)

const multiInfo = computed(() => {
  const map = new Map()
  for (const [key, works] of props.index.problemWorks.entries()) {
    if (works.length > 1) {
      map.set(key, {
        count: works.length,
        names: works.map((work) => work.name).join('、'),
      })
    }
  }
  return map
})

const tokens = computed(() => normalizeSearch(query.value).split(' ').filter(Boolean))

const filteredWorks = computed(() => {
  const searchedTokens = tokens.value
  const result = []
  for (const work of props.dataset.works) {
    const rows = rowsByWork.value.get(work.id) ?? []
    const viewProblems = []
    for (const row of rows) {
      if (status.value === 'solved' && !solved[row.key]) continue
      if (status.value === 'unsolved' && solved[row.key]) continue
      if (ojFilter.value !== 'all' && row.problem.oj !== ojFilter.value) continue
      if (searchedTokens.length && !searchedTokens.every((token) => row.search.includes(token))) {
        continue
      }
      viewProblems.push(row)
    }
    if (viewProblems.length) {
      result.push({ ...work, viewProblems, progress: workProgress(work) })
    }
  }
  return result
})

const visibleCount = computed(() =>
  filteredWorks.value.reduce((total, work) => total + work.viewProblems.length, 0),
)

const isFiltered = computed(
  () => Boolean(query.value) || status.value !== 'all' || ojFilter.value !== 'all',
)

const solvedRowCount = computed(
  () => props.index.rows.reduce((total, row) => total + (solved[row.key] ? 1 : 0), 0),
)

function workProgress(work) {
  const rows = rowsByWork.value.get(work.id) ?? []
  let done = 0
  for (const row of rows) {
    if (solved[row.key]) done += 1
  }
  return {
    done,
    total: rows.length,
    percent: rows.length ? (done / rows.length) * 100 : 0,
  }
}

function multiFor(key) {
  return multiInfo.value.get(key) ?? null
}

function ojColor(oj) {
  if (oj === 'luogu') return 'blue'
  if (oj === 'uoj') return 'teal'
  if (oj === 'qoj') return 'purple'
  return ''
}

function filterByWork(work) {
  query.value = work.name
  status.value = 'all'
  ojFilter.value = 'all'
}

function resetFilters() {
  query.value = ''
  status.value = 'all'
  ojFilter.value = 'all'
}
</script>

<template>
  <section id="problems">
    <div class="ui segment">
      <div class="table-toolbar">
        <div class="ui icon input table-search">
          <input
            v-model="query"
            type="search"
            placeholder="搜索作品、题目或题号…"
            aria-label="搜索作品、题目或题号"
          />
          <i class="search icon"></i>
        </div>

        <div class="ui compact buttons" role="group" aria-label="按完成状态筛选">
          <button
            type="button"
            class="ui button"
            :class="{ active: status === 'all', primary: status === 'all' }"
            @click="status = 'all'"
          >
            全部
          </button>
          <button
            type="button"
            class="ui button"
            :class="{ active: status === 'unsolved', primary: status === 'unsolved' }"
            @click="status = 'unsolved'"
          >
            未做
          </button>
          <button
            type="button"
            class="ui button"
            :class="{ active: status === 'solved', primary: status === 'solved' }"
            @click="status = 'solved'"
          >
            已 AC
          </button>
        </div>

        <div class="ui compact buttons" role="group" aria-label="按题目来源筛选">
          <button
            type="button"
            class="ui button"
            :class="{ active: ojFilter === 'all', primary: ojFilter === 'all' }"
            @click="ojFilter = 'all'"
          >
            全部来源
          </button>
          <button
            v-for="oj in ojOptions"
            :key="oj.key"
            type="button"
            class="ui button"
            :class="{ active: ojFilter === oj.key, primary: ojFilter === oj.key }"
            @click="ojFilter = oj.key"
          >
            {{ oj.label }}
          </button>
        </div>

        <div class="ui basic label result-count">
          显示 {{ visibleCount }} / {{ index.rows.length }} 条
        </div>
        <button v-if="isFiltered" type="button" class="ui basic small button" @click="resetFilters">
          <i class="undo icon"></i>重置
        </button>
      </div>

      <div class="table-scroll">
        <table class="ui celled compact unstackable table acgn-table">
          <thead>
            <tr>
              <th class="work-column">作品</th>
              <th>题目</th>
              <th class="oj-column">来源</th>
              <th class="state-column">状态</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="work in filteredWorks" :key="work.id">
              <tr
                v-for="(row, rowIndex) in work.viewProblems"
                :key="`${work.id}-${rowIndex}-${row.key}`"
                class="problem-row"
              >
                <td
                  v-if="rowIndex === 0"
                  :rowspan="work.viewProblems.length"
                  class="work-cell"
                  @click.stop
                >
                  <div class="work-name-row">
                    <a
                      href="#problems"
                      class="work-name-link"
                      title="只显示该作品"
                      @click.prevent.stop="filterByWork(work)"
                    >
                      {{ work.name }}
                    </a>
                  </div>
                  <div v-if="work.original" class="work-original">{{ work.original }}</div>
                  <div class="work-progress">
                    <span class="ui mini basic label">
                      {{ work.progress.done }} / {{ work.progress.total }}
                    </span>
                  </div>
                </td>

                <td class="problem-cell">
                  <div class="problem-title-line">
                    <a
                      :href="row.problem.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="problem-link"
                      @click.stop
                    >
                      {{ row.title }}
                    </a>
                  </div>
                  <div class="problem-meta">
                    <code class="problem-id">{{ row.key }}</code>
                    <span
                      v-if="multiFor(row.key)"
                      class="ui mini orange label"
                      :title="multiFor(row.key).names"
                    >
                      多厨 ×{{ multiFor(row.key).count }}
                    </span>
                  </div>
                </td>

                <td class="oj-cell">
                  <span class="ui mini label" :class="ojColor(row.problem.oj)">
                    {{ row.problem.ojName }}
                  </span>
                </td>

                <td class="state-cell">
                  <button
                    type="button"
                    class="ui mini button"
                    :class="solved[row.key] ? 'green' : 'basic'"
                    :aria-pressed="Boolean(solved[row.key])"
                    :aria-label="`${solved[row.key] ? '取消' : '标记'} ${row.title}`"
                    @click.stop="toggle(row.key)"
                  >
                    <i :class="[solved[row.key] ? 'check circle' : 'circle outline', 'icon']"></i>
                    {{ solved[row.key] ? '已 AC' : '未做' }}
                  </button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>

        <div v-if="!filteredWorks.length" class="ui message table-empty">
          <i class="search minus icon"></i>
          没有匹配的题目，试试清空筛选条件。
          <button type="button" class="ui basic mini button" @click="resetFilters">重置筛选</button>
        </div>
      </div>

      <div class="table-footer">
        <div class="ui basic label">
          <i class="check circle icon"></i>
          {{ solvedRowCount }} / {{ index.rows.length }} 行已点亮
        </div>
      </div>
    </div>
  </section>
</template>
