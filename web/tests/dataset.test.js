import test from 'node:test'
import assert from 'node:assert/strict'
import { buildIndex, displayWorkFor } from '../src/lib/dataset.js'

const dataset = {
  works: [
    {
      id: 'w1',
      name: '作品 A',
      original: '作品A',
      problems: [
        { key: 'P1', title: '第一题' },
        { key: 'P2', title: '第二题' },
        { key: 'P2', title: '第二题 加强版' },
      ],
    },
    { id: 'w2', name: '作品 B', original: '', problems: [{ key: 'P2', title: '第二题' }] },
  ],
  problems: {
    P1: {
      key: 'P1',
      id: 'P1',
      oj: 'luogu',
      ojName: '洛谷',
      title: '第一题',
      url: 'https://www.luogu.com.cn/problem/P1',
      works: ['w1'],
    },
    P2: {
      key: 'P2',
      id: 'P2',
      oj: 'luogu',
      ojName: '洛谷',
      title: '第二题',
      url: 'https://www.luogu.com.cn/problem/P2',
      works: ['w1', 'w2'],
    },
  },
}

test('builds flattened rows and keeps duplicate rows', () => {
  const index = buildIndex(dataset)
  assert.equal(index.rows.length, 4)
  assert.equal(index.problemCount, 2)
  assert.deepEqual(index.ojCounts, { luogu: 2 })
  assert.deepEqual(
    index.problemWorks.get('P2').map((work) => work.name),
    ['作品 A', '作品 B'],
  )
  assert.equal(displayWorkFor(dataset.problems.P2, index).name, '作品 A')
  assert.equal(index.rows[1].title, '第二题')
  assert.equal(index.rows[2].title, '第二题 加强版')
  assert.match(index.rows[2].search, /加强版/)
  assert.match(index.rows[1].search, /作品 a/)
})
