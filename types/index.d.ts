export type Step = { id: string; group: string; title: string; state: string; detail: string; command?: string; ask?: string }
export type Section = { heading: string; level: number; state: string; notes: string[]; words: number }
export type Item = { kind: string; file: string; line: number; section: string; text: string; path: string; find?: string; doc?: string; bookmark?: string; open_in?: string }
export type Blocker = { id: string; req: string; ref: string; why: string; action: string }
export type Reg = { id: string; client: string; engagement?: string; claim: string; clearance: string; ban_phrases?: string }
export type Role = { id: string; role: string; status: string; person: string; headcount: string; loe_pct: string; phases: string; resume?: string }
export type StatusData = {
  title: string
  generated: string
  steps: Step[]
  sections: Section[]
  items: Item[]
  blockers: Blocker[]
  register: Reg[]
  roster: Role[]
  files: [string, string][]
}

declare module 'claude-code' {
  interface PluginState {
    'rfps': {
      data: StatusData | null
      focus: string
      stepFilter: string
      itemFilter: string
      query: string
      itemLimit: number
      busy: boolean
      watching: boolean
      error: string
    }
  }
}
