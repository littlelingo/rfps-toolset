import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { StatusData } from '../types'

const PANE = 'rfps-status'
const UV = [
  'uv',
  '/opt/homebrew/bin/uv',
]

const dataAtom = atom({ plugin: 'rfps', key: 'data' } as const, null as StatusData | null)
const focusAtom = atom({ plugin: 'rfps', key: 'focus' } as const, 'overview')
const itemLimitAtom = atom({ plugin: 'rfps', key: 'itemLimit' } as const, 15)
const stepFilterAtom = atom({ plugin: 'rfps', key: 'stepFilter' } as const, 'all')
const itemFilterAtom = atom({ plugin: 'rfps', key: 'itemFilter' } as const, 'all')
const queryAtom = atom({ plugin: 'rfps', key: 'query' } as const, '')
const busyAtom = atom({ plugin: 'rfps', key: 'busy' } as const, false)
const errorAtom = atom({ plugin: 'rfps', key: 'error' } as const, '')

const SC: Record<string, string> = {
  done: '#3b8a3e',
  attention: '#c27a0e',
  blocking: '#c0392b',
  todo: '#8a8880',
  skipped: '#2f6fb5',
}
const LABEL: Record<string, string> = {
  done: 'Done',
  attention: 'Needs attention',
  blocking: 'Blocking',
  todo: 'Not started',
  skipped: 'Skipped',
}
const KC: Record<string, string> = { DECISION: '#c0392b', OPEN: '#c27a0e', 'EVIDENCE NEEDED': '#8e44ad', ASSERTION: '#b8a600' }
const SOFT = '#88888822'
const NAV: [string, string][] = [
  ['all', 'Everything'],
  ['overview', 'Overview'],
  ['steps', 'Steps'],
  ['sections', 'Sections'],
  ['items', 'Open items'],
  ['blockers', 'Blockers'],
  ['evidence', 'Evidence'],
  ['team', 'Team'],
  ['files', 'Files'],
]

async function refresh($: any) {
  const script = `${$.plugin.root}/tools/status_page.py`
  await update($, busyAtom, () => true)
  await update($, errorAtom, () => '')
  let last = ''
  for (const uv of UV) {
    try {
      const run = await $.process.run([uv, 'run', script, '--json'], { timeoutMs: 120000 })
      if (run.exitCode === 0) {
        await update($, dataAtom, () => JSON.parse(run.stdout) as StatusData)
        await update($, busyAtom, () => false)
        return
      }
      last = run.stderr.slice(-300)
    } catch (err) {
      last = String(err).slice(0, 300)
    }
  }
  try {
    const run = await $.process.run(['/bin/zsh', '-lc', `uv run '${script}' --json`], { timeoutMs: 120000 })
    if (run.exitCode === 0) {
      await update($, dataAtom, () => JSON.parse(run.stdout) as StatusData)
      await update($, busyAtom, () => false)
      return
    }
    last = run.stderr.slice(-300)
  } catch (err) {
    last = String(err).slice(0, 300)
  }
  await update($, errorAtom, () => `Could not read the status: ${last}`)
  await update($, busyAtom, () => false)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'rfps-pane',
      description: 'Open the live RFP status pane beside the chat',
    })
    await $.command.register({
      name: 'rfps-status-pane',
      description: 'Open the live RFP status pane beside the chat (same as /rfps-pane)',
    })
    void $.ui.open({ id: PANE, title: 'RFP status' })
    void refresh($)
    $.clock.every(60000, () => void refresh($))

    return next(e)
  })

  on('command.run', { command: 'rfps-pane' }, async $ => {
    await $.ui.open({ id: PANE, title: 'RFP status' })
    void refresh($)

    return { text: 'RFP status pane opened.' }
  })

  on('command.run', { command: 'rfps-status-pane' }, async $ => {
    await $.ui.open({ id: PANE, title: 'RFP status' })
    void refresh($)

    return { text: 'RFP status pane opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button, Input } = $.ui.resolve(e)
    const d = await read($, dataAtom)
    const focus = await read($, focusAtom)
    const sf = await read($, stepFilterAtom)
    const itf = await read($, itemFilterAtom)
    const queryText = await read($, queryAtom)
    const itemLimit = await read($, itemLimitAtom)
    const q = queryText.toLowerCase()
    const busy = await read($, busyAtom)
    const err = await read($, errorAtom)

    const fill = (text: string) => void $.prompt.fill({ text, mode: 'replace' })
    const ask = (text: string) => void $.prompt.submit({ text })
    const match = (s: string) => !q || s.toLowerCase().includes(q)
    const show = (k: string) => focus === 'all' || focus === k

    const dot = (state: string) => <Text color={SC[state] ?? SC.todo}>●</Text>
    const chip = (label: string, isOn: boolean, act: () => void) => (
      <Button variant={isOn ? 'primary' : 'secondary'} onPress={act}>{label}</Button>
    )
    const card = (title: string | null, children: any) => (
      <Box flexDirection="column" borderStyle="round" borderDimColor paddingX="md" paddingY="sm" gap="sm" marginBottom="sm">
        {title && <Text weight="semibold" dimColor>{title}</Text>}
        {children}
      </Box>
    )
    const strip = (color: string, children: any) => (
      <Box flexDirection="row" gap="sm">
        <Box width={1} backgroundColor={color} />
        <Box flexDirection="column" flexGrow={1}>{children}</Box>
      </Box>
    )
    const heading = (t: string) => <Text size="heading" weight="semibold">{t}</Text>

    if (!d) {
      return (
        <Box flexDirection="column" gap="sm">
          <Text>{busy ? 'Reading the status...' : err || 'No status yet.'}</Text>
          <Button onPress={() => void refresh($)}>Refresh</Button>
        </Box>
      )
    }

    const counts: Record<string, number> = { done: 0, attention: 0, blocking: 0, todo: 0, skipped: 0 }
    d.steps.forEach(s => (counts[s.state] = (counts[s.state] ?? 0) + 1))
    const total = d.steps.length - counts.skipped
    const pct = total ? Math.round((100 * counts.done) / total) : 0
    const rank: Record<string, number> = { blocking: 0, attention: 1, todo: 2 }
    const next3 = d.steps.filter(s => s.state in rank).sort((a, b) => rank[a.state] - rank[b.state]).slice(0, 3)

    const sections: any[] = []

    if (show('overview')) {
      sections.push(
        <Box flexDirection="column" gap="sm">
          {card(
            null,
            <Box flexDirection="column" gap="sm">
              <Box flexDirection="row" gap="md" alignItems="center">
                <Box flexGrow={1} flexDirection="row" backgroundColor={SOFT}>
                  <Box width={`${Math.max(pct, 1)}%`} backgroundColor={SC.done}><Text> </Text></Box>
                </Box>
                <Text weight="semibold">{`${counts.done} of ${total} steps done (${pct}%)`}</Text>
              </Box>
              <Box flexDirection="row" flexWrap="wrap" gap="sm">
                {['done', 'attention', 'blocking', 'todo', 'skipped']
                  .filter(k => counts[k])
                  .map(k => (
                    <Box paddingX="sm" backgroundColor={SOFT}>
                      <Text>{dot(k)}{` ${counts[k]} ${LABEL[k].toLowerCase()}`}</Text>
                    </Box>
                  ))}
              </Box>
            </Box>,
          )}
          {heading('Next up')}
          {next3.length === 0 && <Text dimColor>Nothing open.</Text>}
          {next3.map(s =>
            card(
              null,
              strip(
                SC[s.state],
                <Box flexDirection="column" gap="xs">
                  <Text weight="semibold">{s.title}</Text>
                  <Text dimColor size="footnote">{s.detail}</Text>
                  {s.command && (
                    <Box flexDirection="row" gap="sm" flexWrap="wrap">
                      <Button onPress={() => fill(s.command as string)}>{`Put ${s.command} in the prompt`}</Button>
                      <Button onPress={p => void $.ui.copy({ text: s.command as string, surface: p.surface })}>Copy command</Button>
                    </Box>
                  )}
                  {s.ask && <Text dimColor size="footnote">{`Ask: ${s.ask}`}</Text>}
                </Box>,
              ),
            ),
          )}
        </Box>,
      )
    }

    if (show('steps')) {
      const groups: Record<string, typeof d.steps> = {}
      d.steps
        .filter(s => (sf === 'all' || s.state === sf) && match(`${s.title} ${s.detail} ${s.id}`))
        .forEach(s => (groups[s.group] = [...(groups[s.group] ?? []), s]))
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading('Steps')}
          <Box flexDirection="row" flexWrap="wrap" gap="sm">
            {['all', 'blocking', 'attention', 'todo', 'done'].map(k =>
              chip(k === 'all' ? 'All' : LABEL[k], sf === k, () => void update($, stepFilterAtom, () => k)),
            )}
          </Box>
          {Object.keys(groups).length === 0 && <Text dimColor>No steps match.</Text>}
          {Object.keys(groups).map(g =>
            card(
              g,
              <Box flexDirection="column" gap="sm">
                {groups[g].map(s => (
                  <Box flexDirection="row" gap="sm">
                    <Text color={SC[s.state]}>●</Text>
                    <Box flexDirection="column" flexGrow={1}>
                      <Text weight="medium">{s.title}</Text>
                      <Text dimColor size="footnote">{s.detail}</Text>
                      {s.command && s.state !== 'done' && (
                        <Box flexDirection="row">
                          <Button onPress={() => fill(s.command as string)}>{`Put ${s.command} in the prompt`}</Button>
                        </Box>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>,
            ),
          )}
        </Box>,
      )
    }

    if (show('sections')) {
      const blocks: any[] = []
      let title = ''
      let tiles: any[] = []
      const flush = () => {
        if (tiles.length) {
          blocks.push(
            card(
              title,
              <Box flexDirection="row" flexWrap="wrap" gap="sm">{tiles}</Box>,
            ),
          )
        }
        tiles = []
      }
      d.sections.forEach(s => {
        if (s.level === 1) {
          flush()
          title = s.heading

          return
        }
        if (!match(s.heading)) return
        const note = s.notes.length ? `  ·  ${s.notes.join(', ')}` : ''
        tiles.push(
          <Box flexDirection="row" gap="sm" width={30} paddingX="sm" backgroundColor={SOFT}>
            <Box width={1} backgroundColor={s.state === 'done' ? SC.done : SC.attention} />
            <Box flexDirection="column" flexGrow={1}>
              <Text size="footnote" weight="medium">{s.heading}</Text>
              <Text size="caption" dimColor>{`${s.words} words${note}`}</Text>
              <Button
                key={`sec-${s.heading}`}
                plain
                onPress={() => fill(`Work on the "${s.heading}" section: resolve its open items${s.notes.length ? ` (${s.notes.join(', ')})` : ''}.`)}
              >
                Work on this
              </Button>
            </Box>
          </Box>,
        )
      })
      flush()
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading('Response sections')}
          <Text dimColor size="footnote">Orange means the heading still carries open notes. Press a tile to put a request about it in the prompt.</Text>
          {blocks}
        </Box>,
      )
    }

    if (show('items')) {
      const kinds = ['all', 'DECISION', 'OPEN', 'EVIDENCE NEEDED', 'ASSERTION']
      const rows = d.items.filter(i => (itf === 'all' || i.kind === itf) && match(`${i.text} ${i.section} ${i.file}`))
      const cap = focus === 'all' ? 5 : itemLimit
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading('Open items')}
          <Box flexDirection="row" flexWrap="wrap" gap="sm">
            {kinds.map(k =>
              chip(
                k === 'all' ? `All (${d.items.length})` : `${k.charAt(0)}${k.slice(1).toLowerCase()} (${d.items.filter(i => i.kind === k).length})`,
                itf === k,
                () => void update($, itemFilterAtom, () => k),
              ),
            )}
          </Box>
          {rows.length === 0 && <Text dimColor>No open items match.</Text>}
          {rows.slice(0, cap).map(i =>
            card(
              null,
              strip(
                KC[i.kind] ?? SC.todo,
                <Box flexDirection="column" gap="xs">
                  <Box flexDirection="row" gap="sm" flexWrap="wrap">
                    <Box paddingX="sm" backgroundColor={KC[i.kind] ?? SC.todo}><Text color="#ffffff" size="caption" weight="semibold">{i.kind}</Text></Box>
                    <Text dimColor size="footnote">{`${i.section}  ·  ${i.file}:${i.line}`}</Text>
                  </Box>
                  <Text>{i.text.length > 240 ? `${i.text.slice(0, 237)}...` : i.text}</Text>
                  <Box flexDirection="row" gap="sm" flexWrap="wrap">
                    <Button onPress={() => fill(`Resolve the ${i.kind} in response/${i.file} line ${i.line} (${i.section}): ${i.text}`)}>Work on this</Button>
                    {i.doc ? (
                      <Button onPress={() => ask(`Run rfps-open-doc --section "${i.section}" --find "${(i.find ?? '').replace(/"/g, "'")}" to open the shared WIP docx; the text to search for goes on the clipboard.`)}>Open in document</Button>
                    ) : (
                      <Button onPress={() => ask(`Open response/${i.file} at line ${i.line} in the file pane.`)}>{`Open ${i.file}:${i.line}`}</Button>
                    )}
                    {i.doc && i.find && <Button onPress={p => void $.ui.copy({ text: i.find as string, surface: p.surface })}>Copy search text</Button>}
                  </Box>
                </Box>,
              ),
            ),
          )}
          {rows.length > cap && (
            <Box flexDirection="row">
              <Button
                onPress={() => {
                  void update($, itemLimitAtom, n => n + 15)
                  void update($, focusAtom, () => 'items')
                }}
              >
                {`Show more (${rows.length - cap} more)`}
              </Button>
            </Box>
          )}
        </Box>,
      )
    }

    if (show('blockers')) {
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading('Blocking compliance checks')}
          {d.blockers.length === 0 && <Text dimColor>No blocking compliance checks.</Text>}
          {d.blockers.filter(b => match(`${b.id} ${b.req} ${b.why}`)).map(b =>
            card(
              null,
              strip(
                SC.blocking,
                <Box flexDirection="column" gap="xs">
                  <Text weight="semibold">{`${b.id}  ${b.req}`}</Text>
                  <Text dimColor size="footnote">{`${b.ref}  ·  ${b.why}`}</Text>
                  <Box flexDirection="row">
                    <Button onPress={() => fill(`Help me clear compliance check ${b.id}: ${b.action}`)}>Help me clear this</Button>
                  </Box>
                </Box>,
              ),
            ),
          )}
        </Box>,
      )
    }

    if (show('evidence')) {
      const cc: Record<string, string> = { cleared: SC.done, hold: SC.attention, 'needs-permission': SC.attention, 'do-not-use': SC.blocking }
      const rows = d.register.filter(r => match(`${r.id} ${r.client} ${r.engagement ?? ''} ${r.claim}`))
      const tally: Record<string, number> = {}
      d.register.forEach(r => (tally[r.clearance] = (tally[r.clearance] ?? 0) + 1))
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading('Evidence register')}
          <Box flexDirection="row" flexWrap="wrap" gap="sm">
            {Object.keys(tally).map(k => (
              <Box paddingX="sm" backgroundColor={SOFT}>
                <Text><Text color={cc[k] ?? SC.todo}>●</Text>{` ${tally[k]} ${k}`}</Text>
              </Box>
            ))}
          </Box>
          {rows.length === 0 && <Text dimColor>No evidence rows match.</Text>}
          {rows.map(r =>
            card(
              null,
              strip(
                cc[r.clearance] ?? SC.todo,
                <Box flexDirection="column" gap="xs">
                  <Box flexDirection="row" gap="sm" flexWrap="wrap" alignItems="center">
                    <Text weight="semibold">{r.id}</Text>
                    <Box paddingX="sm" backgroundColor={cc[r.clearance] ?? SC.todo}>
                      <Text color="#ffffff" size="caption" weight="semibold">{r.clearance}</Text>
                    </Box>
                    <Text dimColor size="footnote">{`${r.client}${r.engagement ? '  ·  ' + r.engagement : ''}`}</Text>
                  </Box>
                  <Text size="footnote">{r.claim}</Text>
                  {r.ban_phrases && <Text size="caption" color={SC.blocking}>{`Banned wording: ${r.ban_phrases}`}</Text>}
                  {r.clearance !== 'cleared' && r.clearance !== 'do-not-use' && (
                    <Box flexDirection="row">
                      <Button onPress={() => fill(`Review evidence row ${r.id} so it can be cleared: what needs to be verified or approved?`)}>Review for clearance</Button>
                    </Box>
                  )}
                </Box>,
              ),
            ),
          )}
        </Box>,
      )
    }

    if (show('team')) {
      const people = d.roster.reduce((n, r) => n + (parseFloat(r.headcount || '1') || 1), 0)
      const fte = d.roster.reduce((n, r) => n + (parseFloat(r.headcount || '1') || 1) * ((parseFloat(r.loe_pct) || 0) / 100), 0)
      const unnamedKp = d.roster.filter(r => r.status === 'KP' && !(r.person || '').trim()).length
      const tc: Record<string, string> = { KP: '#c0392b', Recommended: '#2f6fb5', Ours: '#8e44ad' }
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading('Team roster')}
          <Box flexDirection="row" flexWrap="wrap" gap="sm">
            <Box paddingX="sm" backgroundColor={SOFT}><Text weight="semibold">{`${Math.round(people * 10) / 10} people`}</Text></Box>
            <Box paddingX="sm" backgroundColor={SOFT}><Text weight="semibold">{`${Math.round(fte * 100) / 100} FTE`}</Text></Box>
            {unnamedKp > 0 && (
              <Box paddingX="sm" backgroundColor={SC.blocking}>
                <Text color="#ffffff" weight="semibold">{`${unnamedKp} Key Personnel unnamed`}</Text>
              </Box>
            )}
          </Box>
          {d.roster.filter(r => match(`${r.id} ${r.role} ${r.person}`)).map(r => {
            const unnamed = !(r.person || '').trim()
            const needsName = unnamed && r.status === 'KP'

            return card(
              null,
              strip(
                needsName ? SC.blocking : tc[r.status] ?? SC.todo,
                <Box flexDirection="column" gap="xs">
                  <Box flexDirection="row" gap="sm" flexWrap="wrap" alignItems="center">
                    <Text weight="semibold">{`${r.id}  ${r.role}`}</Text>
                    <Box paddingX="sm" backgroundColor={tc[r.status] ?? SC.todo}>
                      <Text color="#ffffff" size="caption" weight="semibold">{r.status === 'KP' ? 'Key Personnel' : r.status}</Text>
                    </Box>
                  </Box>
                  <Box flexDirection="row" gap="md" flexWrap="wrap">
                    {needsName ? (
                      <Text color={SC.blocking} weight="semibold">Person: not yet named</Text>
                    ) : (
                      <Text>{`Person: ${r.person || 'TBD'}`}</Text>
                    )}
                    <Text dimColor>{`${r.headcount || '1'} × ${r.loe_pct}%`}</Text>
                    <Text dimColor>{`Phases ${r.phases}`}</Text>
                    {r.resume && <Text dimColor>{`Resume: ${r.resume}`}</Text>}
                  </Box>
                  {needsName && (
                    <Box flexDirection="row">
                      <Button onPress={() => fill(`I will name the person for ${r.role} (${r.id}) and note any overlap with other commitments:`)}>Name this person</Button>
                    </Box>
                  )}
                </Box>,
              ),
            )
          })}
        </Box>,
      )
    }

    if (show('files')) {
      sections.push(
        <Box flexDirection="column" gap="sm">
          {heading('Files')}
          <Box flexDirection="row" flexWrap="wrap" gap="sm">
            {(d.files ?? []).map(f => (
              <Button onPress={() => ask(`Open ${f[0]} from the active solution in the file pane.`)}>{f[0]}</Button>
            ))}
          </Box>
        </Box>,
      )
    }

    return (
      <Box flexDirection="column" gap="sm">
        <Box flexDirection="row" gap="md" alignItems="center" flexWrap="wrap">
          <Box flexDirection="column" flexGrow={1}>
            <Text size="title" weight="semibold">{d.title}</Text>
            <Text dimColor size="footnote">{`Updated ${d.generated}  ·  refreshes every minute`}</Text>
          </Box>
          <Button onPress={() => void refresh($)}>{busy ? 'Refreshing...' : 'Refresh'}</Button>
        </Box>
        <Input
          key="query"
          value={queryText}
          placeholder="Search steps, sections and open items..."
          onInput={(v: string) => void update($, queryAtom, () => v)}
          onSubmit={(v: string) => void update($, queryAtom, () => v)}
        />
        <Box flexDirection="row" flexWrap="wrap" gap="sm">
          {NAV.map(([k, label]) => chip(label, focus === k, () => void update($, focusAtom, () => k)))}
        </Box>
        {err && <Text color={SC.blocking}>{err}</Text>}
        {sections}
      </Box>
    )
  })
}
