import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'rfps',
  component: 'Pane',
  requestId: 'rfps-status',
  props: {
    title: 'RFP status',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

const DATA = {
  title: 'Test solution',
  generated: '2026-10-22 12:00',
  steps: [
    { id: 'a', group: 'G', title: 'Step A', state: 'done', detail: 'ok' },
    { id: 'b', group: 'G', title: 'Step B', state: 'blocking', detail: 'needs work', command: '/rfps:resources' },
  ],
  sections: [{ heading: 'Intro', level: 2, state: 'attention', notes: ['1 OPEN'], words: 10 }],
  items: [{ kind: 'DECISION', file: 'a.md', line: 3, section: 'Intro', text: 'pick one', path: 'file:///a.md', find: '[DECISION: pick one', doc: 'file:///w.docx#rfps_Intro_abc123', open_in: 'docx' }],
  blockers: [{ id: 'C-1', req: 'Req', ref: 'WO', why: 'because', action: 'do it' }],
  register: [{ id: 'E-001', client: 'X', claim: 'c', clearance: 'cleared' }],
  files: [['progress.md', 'file:///p.md']],
  roster: [{ id: 'P-001', role: 'Sr. PM', status: 'KP', person: '', headcount: '1', loe_pct: '50', phases: '1;2;3' }],
}

test('the pane shows the status on every surface', async ($, on) => {
  on('command.register', () => ({ value: { command: 'rfps-pane' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('clock.every', () => ({ value: { id: 't' } }))
  on('process.run', () => ({
    value: { exitCode: 0, stdout: JSON.stringify(DATA), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'rfps-pane' })          // the pane is opened by asking for it

  for (const surface of ['terminal', 'desktop', 'vscode'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    const head = await ui.find({ type: 'Text', text: /Test solution/ })
    expect(head?.text).toBe('Test solution')
    const prog = await ui.find({ type: 'Text', text: /steps done/ })
    expect(prog?.text).toMatch(/1 of 2 steps done \(50%\)/)
    await ui.unmount()
  }
})

test('pressing Open items then Work on this puts a prompt in the box', async ($, on) => {
  const fills: string[] = []
  const submits: string[] = []
  on('command.register', () => ({ value: { command: 'rfps-pane' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('clock.every', () => ({ value: { id: 't' } }))
  on('process.run', () => ({
    value: { exitCode: 0, stdout: JSON.stringify(DATA), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('prompt.fill', (_, e) => {
    fills.push(e.text)

    return { isFilled: true }
  })
  on('prompt.submit', (_, e) => {
    submits.push(e.text)

    return { text: e.text }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'rfps-pane' })          // the pane is opened by asking for it
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const tabBtn = await ui.find({ type: 'Button', text: /^Open items$/ })
  expect(tabBtn).toBeDefined()
  await ui.press({ key: tabBtn?.key as string })
  const work = await ui.find({ type: 'Button', text: /Work on this/ })
  expect(work).toBeDefined()
  await ui.press({ key: work?.key as string })
  expect(fills[0]).toContain('Resolve the DECISION in response/a.md line 3')
  const open = await ui.find({ type: 'Button', text: /Open in document/ })
  expect(open).toBeDefined()
  await ui.press({ key: open?.key as string })
  expect(submits[0]).toContain('rfps-open-doc --section "Intro"')
  await ui.unmount()
})

test('starting a session opens nothing and runs nothing; asking for the pane opens it once and keeps it fresh', async ($, on) => {
  const opened: string[] = []
  const ran: string[] = []
  const timers: number[] = []
  on('command.register', () => ({ value: { command: 'rfps-pane' } }))
  on('ui.open', (_, e) => {
    opened.push(e.id)

    return { value: { isPlaced: true } }
  })
  on('clock.every', (_, e) => {
    timers.push(e.ms)

    return { value: { id: 't' } }
  })
  on('process.run', (_, e) => {
    ran.push(e.argv.join(' '))

    return { value: { exitCode: 0, stdout: JSON.stringify(DATA), stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(opened).toEqual([])      // nothing pops up on its own
  expect(ran).toEqual([])         // and no status command runs in a session that never wanted the pane
  expect(timers).toEqual([])

  await $.command.run({ command: 'rfps-pane' })
  await $.command.run({ command: 'rfps-status-pane' })
  expect(opened).toEqual(['rfps-status', 'rfps-status'])
  expect([...timers]).toEqual([60000])     // one refresh timer however many times it is opened (checked before the harness's own clock runs on)
  await new Promise(resolve => setTimeout(resolve, 100))     // let the background status read finish before the test ends
  expect(ran.length).toBeGreaterThan(0)
})
