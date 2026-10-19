<script setup>
import { computed, onMounted, ref } from 'vue'
import Dashboard from './components/Dashboard.vue'
import ImportPanel from './components/ImportPanel.vue'
import ProblemTable from './components/ProblemTable.vue'
import { useSolved } from './composables/useSolved.js'
import { buildIndex } from './lib/dataset.js'
import { formatDateTime } from './lib/format.js'
import { computeStats } from './lib/stats.js'

const { solved, mark } = useSolved()

const dataset = ref(null)
const loading = ref(true)
const error = ref('')

const index = computed(() => (dataset.value ? buildIndex(dataset.value) : null))
const stats = computed(() =>
  dataset.value && index.value ? computeStats(dataset.value, index.value, solved) : null,
)

const dataUrl = new URL('data/acgn.json', document.baseURI).href

async function loadDataset() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(dataUrl, { cache: 'no-cache' })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} ${response.statusText}`)
    }
    const payload = await response.json()
    if (
      !payload ||
      !Array.isArray(payload.works) ||
      !payload.problems ||
      typeof payload.problems !== 'object'
    ) {
      throw new Error('数据格式不正确')
    }
    dataset.value = payload
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    loading.value = false
  }
}

onMounted(loadDataset)
</script>

<template>
  <div v-if="loading" class="ui container loading-screen">
    <div class="ui active inline loader"></div>
    <p>正在加载题单…</p>
  </div>

  <div v-else-if="error || !dataset || !stats" class="ui container loading-screen">
    <div class="ui negative message">
      <div class="header">题单加载失败</div>
      <p>{{ error || '数据为空' }}</p>
      <p>
        如果你是在本地直接打开 <code>index.html</code>，浏览器会拦截数据请求；请用
        <code>npm run dev</code> 或任意 HTTP 静态服务器访问。
      </p>
    </div>
    <button class="ui primary button" type="button" @click="loadDataset">重试</button>
  </div>

  <div v-else id="top">
    <nav class="ui menu site-menu" aria-label="页面导航">
      <div class="ui container">
        <a class="item" href="#problems"><i class="list icon"></i>题库</a>
        <a class="item" href="#record"><i class="edit icon"></i>记录</a>
        <a class="item" href="#dashboard"><i class="chart bar icon"></i>看板</a>
      </div>
    </nav>

    <header class="site-header">
      <div class="ui container">
        <div class="ui segment">
          <div class="ui stackable middle aligned grid">
            <div class="eleven wide column">
              <h1 class="ui header">
                以 ACGN 为题目背景的题
              </h1>
              <div class="ui horizontal bulleted list">
                <div class="item">
                  <i class="sync alternate icon"></i>
                  抓取于 {{ formatDateTime(dataset.source.fetchedAt) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <main class="ui container main-content">
      <ProblemTable :dataset="dataset" :index="index" />

      <ImportPanel :dataset="dataset" :index="index" />

      <Dashboard
        :stats="stats"
        :index="index"
        :solved="solved"
        @mark-solved="mark"
      />
    </main>

    <footer class="ui inverted vertical footer segment">
      <div class="ui center aligned container">
        <div class="ui stackable inverted divided grid">
          <div class="ten wide left aligned column">
            <h4 class="ui inverted header">ACGN 题单</h4>
            <p>
              数据来自
              <a :href="dataset.source.url" target="_blank" rel="noopener noreferrer">洛谷专栏</a>。
            </p>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>
