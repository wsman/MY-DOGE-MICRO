import { describe, it, expect } from 'vitest'
import {
  useFuzzySearch,
  tokenize,
  scoreMatch,
  graphemeSubsetMatch,
} from '../composables/useFuzzySearch'

describe('useFuzzySearch', () => {
  it('matches an exact field (score 100)', () => {
    const { search } = useFuzzySearch()
    const items = [{ ticker: 'AAPL', name: 'Apple' }]
    const out = search('AAPL', items, i => [i.ticker, i.name])
    expect(out).toHaveLength(1)
    expect(out[0]!.item.ticker).toBe('AAPL')
    expect(out[0]!.score).toBe(100)
  })

  it('matches a prefix (score 80)', () => {
    const { search } = useFuzzySearch()
    const items = [{ ticker: '600519', name: '贵州茅台' }]
    const out = search('6005', items, i => [i.ticker, i.name])
    expect(out).toHaveLength(1)
    expect(out[0]!.score).toBe(80)
  })

  it('returns [] for an empty query', () => {
    const { search } = useFuzzySearch()
    const items = [{ ticker: 'AAPL', name: 'Apple' }]
    expect(search('', items, i => [i.ticker, i.name])).toEqual([])
    expect(search('   ', items, i => [i.ticker, i.name])).toEqual([])
  })

  it('returns [] when no field matches', () => {
    const { search } = useFuzzySearch()
    const items = [
      { ticker: 'AAPL', name: 'Apple' },
      { ticker: 'MSFT', name: 'Microsoft' },
    ]
    expect(search('zzzznotfound', items, i => [i.ticker, i.name])).toEqual([])
  })

  it('CJK subsequence match: 贵茅 matches 贵州茅台 via graphemeSubsetMatch', () => {
    // The two-grapheme query 贵茅 appears in order inside 贵州茅台 (positions 0 and 2).
    expect(graphemeSubsetMatch('贵茅', '贵州茅台')).toBe(true)
    // Reversed order does NOT match.
    expect(graphemeSubsetMatch('茅贵', '贵州茅台')).toBe(false)
  })

  it('CJK partial query scores via scoreMatch (grapheme subsequence = 40)', () => {
    // 贵茅 is a subsequence of 贵州茅台 but not a prefix/contains/exact match,
    // so scoreMatch should fall through to the graphemeSubsetMatch branch (40).
    expect(scoreMatch('贵茅', ['贵州茅台'])).toBe(40)
  })

  it('useFuzzySearch.search ranks a CJK subsequence query above minScore', () => {
    const { search } = useFuzzySearch({ minScore: 10 })
    const items = [
      { ticker: '600519', name: '贵州茅台' },
      { ticker: '000858', name: '五粮液' },
    ]
    const out = search('贵茅', items, i => [i.ticker, i.name])
    expect(out).toHaveLength(1)
    expect(out[0]!.item.ticker).toBe('600519')
  })

  it('respects maxResults and minScore options', () => {
    const { search } = useFuzzySearch({ maxResults: 2, minScore: 60 })
    // 'a' is a prefix of apple, contains in apricot/banana — only >= 60 kept.
    const items = [
      { ticker: 'A', name: 'apple' },
      { ticker: 'B', name: 'apricot' },
      { ticker: 'C', name: 'banana' },
    ]
    const out = search('a', items, i => [i.ticker, i.name])
    expect(out.length).toBeLessThanOrEqual(2)
    for (const r of out) {
      expect(r.score).toBeGreaterThanOrEqual(60)
    }
  })

  it('tokenize() lowercases and segments', () => {
    // 'AAPL' should come back lowercased; the API stays as a single word-like token.
    const tokens = tokenize('AAPL Apple')
    expect(tokens.length).toBeGreaterThan(0)
    expect(tokens.every(t => t === t.toLowerCase())).toBe(true)
    expect(tokens).toContain('aapl')
  })
})
