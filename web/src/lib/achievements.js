/**
 * All achievement definitions. This file is the single source of truth for
 * thresholds, descriptions, series groups and category buckets; stats.js only
 * computes metrics and progress.
 *
 * Problem-count achievements use difficulty-weighted points (a beginner
 * problem is 1 point, each difficulty level adds 0.5, NOI/NOI+/CTS is 5).
 * Work-count achievements still count works.
 *
 * Category achievements reference tag slugs, never work names. The mapping
 * from work to tags lives in `web/public/data/tags.json`; run `python scripts/sync_tags.py`
 * after the article gains a new work, then fill in its empty tag list.
 */
const CATEGORY_ACHIEVEMENTS = [
  {
    id: 'category-yuri',
    icon: 'heart',
    name: '百合绽放',
    desc: '累计获得 50 难度点（百合向）',
    metric: 'tag',
    tag: 'yuri',
    threshold: 50,
    unit: ' 点',
  },
  {
    id: 'category-galgame',
    icon: 'gamepad',
    name: 'Galgame 玩家',
    desc: '累计获得 50 难度点（Galgame / 视觉小说）',
    metric: 'tag',
    tag: 'galgame',
    threshold: 50,
    unit: ' 点',
  },
  {
    id: 'touhou',
    icon: 'moon',
    name: '幻想乡住民',
    desc: '累计获得 50 难度点（东方 Project）',
    metric: 'tag',
    tag: 'touhou',
    threshold: 50,
    unit: ' 点',
  },
  {
    id: 'key',
    icon: 'key',
    name: 'Key 社信徒',
    desc: '累计获得 50 难度点（Key 社）',
    metric: 'tag',
    tag: 'key',
    threshold: 50,
    unit: ' 点',
  },
  {
    id: 'category-music',
    icon: 'music',
    name: '一起组乐队吧',
    desc: '累计获得 50 难度点（乐队题材）',
    metric: 'tag',
    tag: 'music',
    threshold: 50,
    unit: ' 点',
  },
  {
    id: 'category-mahou',
    icon: 'magic',
    name: '魔法少女契约',
    desc: '累计获得 50 难度点（魔法少女）',
    metric: 'tag',
    tag: 'mahou',
    threshold: 50,
    unit: ' 点',
  },
]
const GROWTH_ACHIEVEMENTS = [
  {
    id: 'first',
    icon: 'seedling',
    name: '初次接触',
    desc: '获得第一个难度点',
    metric: 'weightedSolved',
    threshold: 1,
    unit: ' 点',
  },
  {
    id: 'hundred',
    icon: 'star',
    name: '百炼成钢',
    desc: '累计获得 100 难度点',
    metric: 'weightedSolved',
    threshold: 100,
    unit: ' 点',
  },
  {
    id: 'threehundred',
    icon: 'fire',
    name: '渐入佳境',
    desc: '累计获得 300 难度点',
    metric: 'weightedSolved',
    threshold: 300,
    unit: ' 点',
  },
  {
    id: 'fivehundred',
    icon: 'trophy',
    name: '驾轻就熟',
    desc: '累计获得 500 难度点',
    metric: 'weightedSolved',
    threshold: 500,
    unit: ' 点',
  },
  {
    id: 'sevenhundred',
    icon: 'medal',
    name: '传奇大师',
    desc: '累计获得 700 难度点',
    metric: 'weightedSolved',
    threshold: 700,
    unit: ' 点',
  },
  {
    id: 'thousand',
    icon: 'crown',
    name: '千点传说',
    desc: '累计获得 1000 难度点',
    metric: 'weightedSolved',
    threshold: 1000,
    unit: ' 点',
  },
  {
    id: 'works3',
    icon: 'users',
    name: '三坑起步',
    desc: '点亮 3 部不同作品',
    metric: 'touchedWorkCount',
    threshold: 3,
    unit: ' 部',
  },
  {
    id: 'works10',
    icon: 'map',
    name: 'DD 全开',
    desc: '点亮 10 部不同作品',
    metric: 'touchedWorkCount',
    threshold: 10,
    unit: ' 部',
  },
  {
    id: 'works30',
    icon: 'map marked',
    name: '多坑巡礼',
    desc: '点亮 30 部不同作品',
    metric: 'touchedWorkCount',
    threshold: 30,
    unit: ' 部',
  },
  {
    id: 'works50',
    icon: 'globe',
    name: '博闻强识',
    desc: '点亮 50 部不同作品',
    metric: 'touchedWorkCount',
    threshold: 50,
    unit: ' 部',
  },
  {
    id: 'works80',
    icon: 'route',
    name: '行者无疆',
    desc: '点亮 80 部不同作品',
    metric: 'touchedWorkCount',
    threshold: 80,
    unit: ' 部',
  },
  {
    id: 'works100',
    icon: 'award',
    name: '集大成者',
    desc: '点亮 100 部不同作品',
    metric: 'touchedWorkCount',
    threshold: 100,
    unit: ' 部',
  },
]

export const ACHIEVEMENTS = [
  ...GROWTH_ACHIEVEMENTS,
  ...CATEGORY_ACHIEVEMENTS,
]
