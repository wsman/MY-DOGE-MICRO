/**
 * Naive UI theme bridge for OpenDoge.
 *
 * Mirrors the dark-first design tokens declared in tokens.css into Naive's
 * GlobalThemeOverrides so the component library renders the sanctioned palette.
 *
 * NOTE: Naive's theme API consumes plain JS values, so these constants are a
 * hand-maintained mirror of the :root tokens — tokens.css remains the single
 * source of truth. If a token value changes, update BOTH files (or, in a
 * follow-up, read :root via getComputedStyle at setup like useKlineChart does).
 */
import type { GlobalThemeOverrides } from 'naive-ui'

export const themeOverrides: GlobalThemeOverrides = {
  common: {
    bodyColor: '#1a1a2e',
    textColorBase: 'rgba(255,255,255,0.95)',
    primaryColor: '#2196f3',
    successColor: '#63e2b7',
    errorColor: '#ef5350',
    borderColor: 'rgba(255,255,255,0.08)',
    fontFamily: "'Microsoft YaHei','PingFang SC','Hiragino Sans GB',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif",
  },
}
