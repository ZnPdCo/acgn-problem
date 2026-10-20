<script setup>
import { computed, ref, watch } from 'vue'
import { displayWorkFor } from '../lib/dataset.js'
import {
  difficultyColor,
  difficultyLabel,
  difficultyTitle,
} from '../lib/difficulty.js'
import { formatWeight } from '../lib/format.js'
import { RANKS } from '../lib/stats.js'

const props = defineProps({
  stats: { type: Object, required: true },
  index: { type: Object, required: true },
  solved: { type: Object, required: true },
})

const emit = defineEmits(['mark-solved'])

const progress = computed(() => Math.max(0, Math.min(100, props.stats.concentration)))
const percentText = computed(() => progress.value.toFixed(1))
const achievementPercent = computed(() =>
  props.stats.achievementCount
    ? Math.min(
        100,
        (props.stats.unlockedAchievements / props.stats.achievementCount) * 100,
      )
    : 0,
)

const pool = computed(() => Object.keys(props.index.problems).filter((key) => !props.solved[key]))
const recommendedKey = ref(null)

function chooseRandom(exclude = null) {
  const keys = pool.value
  if (!keys.length) return null
  const candidates = keys.length > 1 && exclude ? keys.filter((key) => key !== exclude) : keys
  return candidates[Math.floor(Math.random() * candidates.length)] ?? null
}

watch(
  pool,
  () => {
    if (!pool.value.length) {
      recommendedKey.value = null
      return
    }
    if (
      !recommendedKey.value ||
      !props.index.problems[recommendedKey.value] ||
      props.solved[recommendedKey.value]
    ) {
      recommendedKey.value = chooseRandom()
    }
  },
  { immediate: true },
)

const recommended = computed(() => {
  if (!recommendedKey.value) return null
  const problem = props.index.problems[recommendedKey.value]
  if (!problem) return null
  return {
    problem,
    work: displayWorkFor(problem, props.index),
    works: props.index.problemWorks.get(problem.key) ?? [],
  }
})

function reroll() {
  recommendedKey.value = chooseRandom(recommendedKey.value)
}

function markRecommended() {
  if (!recommendedKey.value) return
  emit('mark-solved', recommendedKey.value)
}

function rankThreshold(min) {
  return min > 0 && min < 0.01 ? '> 0%' : `${min}%`
}

function difficultyClass(difficulty) {
  const color = difficultyColor(difficulty)
  return color ? `ui mini ${color} label` : 'ui mini basic label'
}
</script>

<template>
  <section id="dashboard">
    <div class="ui stackable grid">
      <div class="six wide column">
        <div class="ui segment center aligned">
          <div class="ui statistic">
            <div class="value">
              {{ percentText }}<span class="stat-suffix">%</span>
            </div>
            <div class="label">ACGN 浓度</div>
          </div>

          <div class="rank-line">
            <div class="ui label" :class="stats.rank.level === 'Lv.0' ? '' : 'purple'">
              <i class="certificate icon"></i>
              {{ stats.rank.level }} · {{ stats.rank.name }}
            </div>
          </div>

          <!-- Fomantic hides non-empty bars when data-percent is absent (no JS init here). -->
          <div
            class="ui small teal progress"
            :data-percent="progress"
            :title="`${percentText}%`"
          >
            <div class="bar" :style="{ width: `${progress}%` }">
              <div class="progress">{{ percentText }}%</div>
            </div>
          </div>

          <p class="muted-text weight-line">
            难度点 {{ formatWeight(stats.solvedWeight) }} /
            {{ formatWeight(stats.totalWeight) }}
            · 满浓度目标 {{ formatWeight(stats.targetWeight) }}
          </p>

          <p v-if="stats.nextRank" class="muted-text">
            再获得 <strong>{{ formatWeight(stats.weightToNext) }}</strong> 难度点，晋级
            <strong>{{ stats.nextRank.name }}</strong>
          </p>
          <p v-else class="muted-text">已达到最高浓度。</p>

          <div class="ui divider"></div>

          <div class="ui mini info message">
            浓度按难度赋权：入门 1 点，每升一级 +0.5 点，NOI/NOI+/CTS 5
            点，暂无评定 / 未设置难度按 1 点；达到总权重的 50% 即 100%。同一道题只计一次。
          </div>
        </div>
      </div>

      <div class="ten wide column">
        <div class="ui three column stackable grid">
          <div class="column">
            <div class="ui segment">
              <div class="ui small statistic">
                <div class="value">
                  {{ stats.solvedCount }}<span class="stat-suffix">/ {{ stats.problemCount }}</span>
                </div>
                <div class="label">已 AC 题目</div>
              </div>
              <div class="ui mini progress">
                <div class="bar" :style="{ width: `${Math.min(100, stats.uniquePercent)}%` }"></div>
              </div>
              <p class="muted-text">
                题目完成度 {{ stats.uniquePercent.toFixed(1) }}%
                · 难度点 {{ formatWeight(stats.solvedWeight) }}
              </p>
            </div>
          </div>

          <div class="column">
            <div class="ui segment">
              <div class="ui small statistic">
                <div class="value">
                  {{ stats.touchedWorkCount }}<span class="stat-suffix">/ {{ stats.workCount }}</span>
                </div>
                <div class="label">点亮的作品</div>
              </div>
              <div class="ui mini progress">
                <div
                  class="bar"
                  :style="{
                    width: `${Math.min(100, stats.workCount ? (stats.touchedWorkCount / stats.workCount) * 100 : 0)}%`,
                  }"
                ></div>
              </div>
              <p class="muted-text">足迹遍布 {{ stats.touchedWorkCount }} 部作品</p>
            </div>
          </div>

          <div class="column">
            <div class="ui segment">
              <div class="ui small statistic">
                <div class="value">
                  {{ stats.unlockedAchievements }}<span class="stat-suffix">/ {{ stats.achievementCount }}</span>
                </div>
                <div class="label">已解锁成就</div>
              </div>
              <div class="ui mini progress">
                <div class="bar" :style="{ width: `${achievementPercent}%` }"></div>
              </div>
              <p class="muted-text">按难度点、作品与类别收集</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="ui stackable grid">
      <div class="eight wide column">
        <div class="ui segment">
          <h3 class="ui header">
            浓度成就
            <div class="sub header">{{ stats.unlockedAchievements }} / {{ stats.achievementCount }}</div>
          </h3>

          <div class="ui middle aligned relaxed divided list compact-list">
            <div v-for="achievement in stats.achievements" :key="achievement.id" class="item">
              <div class="right floated content">
                <span class="ui mini label" :class="achievement.unlocked ? 'green' : 'basic'">
                  {{ achievement.progress }}
                </span>
              </div>
              <i
                class="large icon"
                :class="[achievement.icon, achievement.unlocked ? 'green' : 'grey']"
                :title="achievement.desc"
              ></i>
              <div class="content">
                <div class="header">{{ achievement.name }}</div>
                <div class="description">{{ achievement.desc }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="eight wide column">
        <div class="ui segment">
          <h3 class="ui header">
            随机推荐
            <div class="sub header">随机抽一道还没做的题</div>
          </h3>

          <template v-if="recommended">
            <div class="ui basic label">
              <i class="bookmark outline icon"></i>
              {{ recommended.work?.name ?? '未知作品' }}
            </div>
            <h4 class="ui header recommend-title">
              <a
                :href="recommended.problem.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ recommended.problem.title }}
              </a>
            </h4>
            <div class="ui labels">
              <span class="ui mini label">{{ recommended.problem.key }}</span>
              <span class="ui mini blue label">{{ recommended.problem.ojName }}</span>
              <span
                class="ui mini label"
                :class="difficultyClass(recommended.problem.difficulty)"
                :title="difficultyTitle(recommended.problem.difficulty)"
              >
                {{ difficultyLabel(recommended.problem.difficulty) }}
              </span>
              <span v-if="recommended.works.length > 1" class="ui mini orange label">
                多厨 ×{{ recommended.works.length }}
              </span>
            </div>
            <div class="ui buttons dashboard-actions">
              <a
                class="ui button"
                :href="recommended.problem.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                打开题目
              </a>
              <button type="button" class="ui primary button" @click="markRecommended">
                <i class="check icon"></i>标记已 AC
              </button>
              <button type="button" class="ui icon button" title="换一题" @click="reroll">
                <i class="refresh icon"></i>
              </button>
            </div>
          </template>
          <div v-else class="ui message">
            <i class="crown icon"></i>
            你已经把整份题单做完了，去评论区催更吧。
          </div>
        </div>

        <div class="ui segment">
          <h3 class="ui header">
            浓度等级
            <div class="sub header">按难度赋权题目计算，总权重的 50% 为满浓度</div>
          </h3>
          <div class="ui relaxed divided list compact-list">
            <div v-for="rank in RANKS" :key="rank.name" class="item">
              <div class="right floated content">
                <span v-if="rank.name === stats.rank.name" class="ui mini purple label">当前</span>
                <span class="ui mini basic label">{{ rankThreshold(rank.min) }}</span>
              </div>
              <div class="content">
                <div class="header" :class="{ 'current-rank': rank.name === stats.rank.name }">
                  {{ rank.level }} · {{ rank.name }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
