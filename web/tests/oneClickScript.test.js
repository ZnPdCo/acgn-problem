import test from 'node:test'
import assert from 'node:assert/strict'
import { ONE_CLICK_SCRIPT } from '../src/lib/oneClickScript.js'

test('one-click script reads the Luogu practice context and prints problem ids', () => {
  assert.ok(ONE_CLICK_SCRIPT.startsWith('(async () => {'))
  assert.ok(ONE_CLICK_SCRIPT.endsWith('})()'))
  assert.ok(ONE_CLICK_SCRIPT.includes('lentille-context'))
  assert.ok(ONE_CLICK_SCRIPT.includes('application\\/json'))
  assert.ok(ONE_CLICK_SCRIPT.includes('([\\s\\S]*?)'))
  assert.ok(ONE_CLICK_SCRIPT.includes('<\\/script>'))
  assert.equal(ONE_CLICK_SCRIPT.includes('</script>'), false)
  assert.ok(ONE_CLICK_SCRIPT.includes('`/user/${uid}/practice`'))
  assert.ok(ONE_CLICK_SCRIPT.includes('ctx.data.passed.map(p => p.pid)'))
  assert.ok(ONE_CLICK_SCRIPT.includes("pids.join(' ')"))
  assert.ok(ONE_CLICK_SCRIPT.includes('↑ 复制上面这一行'))
})
