/**
 * Fuzzy search composable using Intl.Segmenter for CJK-aware matching.
 * Inspired by pretext's analysis.ts — uses word + grapheme segmentation
 * to support partial CJK queries like "贵茅" matching "贵州茅台".
 */

export interface FuzzySearchOptions {
  maxResults?: number
  minScore?: number
}

// Singleton segmenters (matching pretext's hoisted pattern)
let _wordSeg: Intl.Segmenter | null = null
let _graphemeSeg: Intl.Segmenter | null = null

function getWordSegmenter(): Intl.Segmenter {
  if (!_wordSeg) {
    _wordSeg = new Intl.Segmenter('zh-CN', { granularity: 'word' })
  }
  return _wordSeg
}

function getGraphemeSegmenter(): Intl.Segmenter {
  if (!_graphemeSeg) {
    _graphemeSeg = new Intl.Segmenter('zh-CN', { granularity: 'grapheme' })
  }
  return _graphemeSeg
}

/**
 * Tokenize text into searchable units.
 * CJK characters are segmented per-grapheme; Latin words stay intact.
 */
export function tokenize(text: string): string[] {
  const tokens: string[] = []
  for (const seg of getWordSegmenter().segment(text)) {
    const s = seg.segment.trim()
    if (!s) continue
    // Accept word-like segments or any CJK character
    if (seg.isWordLike || /[一-鿿㐀-䶿]/.test(s)) {
      tokens.push(s.toLowerCase())
    }
  }
  return tokens
}

/**
 * Check if all graphemes in query appear in order in target (subsequence).
 * "贵茅" vs "贵州茅台" → ["贵","茅"] found at positions [0,2] → true
 */
export function graphemeSubsetMatch(query: string, target: string): boolean {
  const qGraphemes = [...getGraphemeSegmenter().segment(query)].map(s => s.segment)
  const tGraphemes = [...getGraphemeSegmenter().segment(target)].map(s => s.segment)
  let qi = 0
  for (const tg of tGraphemes) {
    if (qi < qGraphemes.length && tg === qGraphemes[qi]) qi++
  }
  return qi === qGraphemes.length
}

/**
 * Score a single query against searchable text fields.
 * Returns 0 if no match.
 */
export function scoreMatch(query: string, fields: string[]): number {
  const q = query.toLowerCase()
  let best = 0

  for (const field of fields) {
    const f = field.toLowerCase()
    if (!f) continue

    // Exact match
    if (f === q) { best = Math.max(best, 100); continue }

    // Prefix match
    if (f.startsWith(q)) { best = Math.max(best, 80); continue }

    // Contains match
    if (f.includes(q)) { best = Math.max(best, 60); continue }

    // Grapheme subsequence (CJK partial match)
    if (graphemeSubsetMatch(q, f)) { best = Math.max(best, 40); continue }

    // Token-level matching
    const qTokens = tokenize(q)
    const fTokens = tokenize(f)
    if (qTokens.length > 0 && fTokens.length > 0) {
      const tokenScore = scoreTokenMatch(qTokens, fTokens)
      best = Math.max(best, tokenScore)
    }
  }

  return best
}

function scoreTokenMatch(queryTokens: string[], targetTokens: string[]): number {
  let total = 0
  const matched = new Set<number>()

  for (const qTok of queryTokens) {
    let bestScore = 0
    let bestIdx = -1

    for (let i = 0; i < targetTokens.length; i++) {
      if (matched.has(i)) continue
      const tTok = targetTokens[i]!

      let s = 0
      if (tTok === qTok) s = 95
      else if (tTok.startsWith(qTok)) s = 75
      else if (tTok.includes(qTok)) s = 55
      else if (graphemeSubsetMatch(qTok, tTok)) s = 35

      if (s > bestScore) {
        bestScore = s
        bestIdx = i
      }
    }

    if (bestIdx >= 0) {
      total += bestScore
      matched.add(bestIdx)
    }
  }

  // Normalize: full score if all query tokens matched
  return queryTokens.length > 0 ? Math.round(total / queryTokens.length) : 0
}

export interface SearchResult<T> {
  item: T
  score: number
}

export function useFuzzySearch(options: FuzzySearchOptions = {}) {
  const { maxResults = 30, minScore = 10 } = options

  function search<T>(
    query: string,
    items: T[],
    getSearchableFields: (item: T) => string[],
  ): SearchResult<T>[] {
    const q = query.trim()
    if (!q) return []

    const scored: SearchResult<T>[] = []
    for (const item of items) {
      const fields = getSearchableFields(item)
      const score = scoreMatch(q, fields)
      if (score >= minScore) {
        scored.push({ item, score })
      }
    }

    scored.sort((a, b) => b.score - a.score)
    return scored.slice(0, maxResults)
  }

  return { search, tokenize, scoreMatch, graphemeSubsetMatch }
}
