<template>
  <!--
    Loading: skeleton text rows (or a spinner when skeletonRows === 0). The
    wrapper announces itself to assistive tech as busy + politely live so a
    screen reader cues the operator that content is arriving.
  -->
  <div
    v-if="status === 'loading'"
    class="sv-loading"
    aria-live="polite"
    aria-busy="true"
  >
    <n-spin v-if="skeletonRows === 0" class="sv-spin" />
    <n-skeleton
      v-for="i in skeletonRows"
      v-else
      :key="i"
      text
      :repeat="1"
      class="sv-skeleton-row"
    />
  </div>

  <!--
    Empty: no data to show. Naive UI's n-empty draws the muted "no data"
    illustration + description; we pass the caller's description through.
  -->
  <n-empty
    v-else-if="status === 'empty'"
    :description="emptyDescription"
    class="sv-empty"
  />

  <!--
    Error: surface the structured { code, message } instead of blanking. The
    wrapper is an assertive alert so screen readers announce the failure
    immediately. The Retry button only renders when the caller wired onRetry.
  -->
  <div
    v-else-if="status === 'error'"
    class="sv-error"
    role="alert"
    aria-live="assertive"
  >
    <n-result
      status="error"
      :title="error?.message ?? 'Something went wrong'"
    >
      <template v-if="onRetry" #footer>
        <n-button type="primary" @click="onRetry">Retry</n-button>
      </template>
    </n-result>
  </div>

  <!--
    idle (or any unknown): render the default slot. This is the only path that
    yields the slot — loading/empty/error are replaced wholesale so views never
    render stale content behind a skeleton or error.
  -->
  <slot v-else />
</template>

<script setup lang="ts">
import { NSkeleton, NSpin, NEmpty, NResult, NButton } from 'naive-ui'

/**
 * StatusView — a shared loading / empty / error / idle triad (S003-009).
 *
 * Views wrap their content area in this component and bind a status enum plus
 * (optionally) a structured error and a retry callback. StatusView renders the
 * appropriate Naive UI primitive for the non-idle states and only yields the
 * default slot when `status === 'idle'`, so a view never shows stale content
 * behind a skeleton or an error banner. The error shape is the shared
 * `{ code, message }` vocabulary (utils/fetchError.ts FetchError /
 * composables/useSSE.ts SSEError) so one StatusView renders both REST and SSE
 * failures identically.
 */

/**
 * The lifecycle StatusView branches on. `idle` yields the slot; the other
 * three are replaced wholesale with the matching Naive UI primitive.
 */
type Status = 'idle' | 'loading' | 'empty' | 'error'

withDefaults(
  defineProps<{
    /** Current render status. Only `idle` yields the default slot. */
    status: Status
    /** Description for the empty state. */
    emptyDescription?: string
    /** Structured error for the error state. Ignored unless status === 'error'. */
    error?: { code: string; message: string } | null
    /**
     * Retry handler. When provided AND status === 'error', a Retry button is
     * rendered in the n-result footer; omit it for non-retryable errors.
     */
    onRetry?: () => void
    /**
     * Number of skeleton text rows to show while loading. Pass 0 to render an
     * n-spin instead (useful for non-list contexts like a chart panel).
     */
    skeletonRows?: number
  }>(),
  {
    emptyDescription: 'No data',
    error: null,
    skeletonRows: 3,
  },
)
</script>

<style scoped>
/* Loading: stack skeleton rows (or center a spinner) with breathing room. */
.sv-loading {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

/* When skeletonRows === 0 we render a bare n-spin; center it. */
.sv-spin {
  align-self: center;
  margin: 16px 0;
}

.sv-skeleton-row {
  /* n-skeleton text defaults to a comfortable line height; this just keeps
     repeated rows visually distinct rather than fusing into a block. */
  height: 14px;
}

/* Empty + error centers the Naive UI primitive so it reads as a status, not
   as left-flush content. */
.sv-empty,
.sv-error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 12px;
}

/* ---------------------------------------------------------------------------
 * a11y reduced-motion: neutralize the n-spin rotation and the n-skeleton
 * shimmer so motion-sensitive operators aren't subjected to perpetual
 * animation while a panel is loading. Mirrors the global baseline in
 * styles/tokens.css but is re-declared here because Naive UI's animation
 * classes live on shadow elements that the global * selector already covers
 * — this block keeps the intent explicit and self-documenting at the
 * component boundary.
 * ------------------------------------------------------------------------- */
@media (prefers-reduced-motion: reduce) {
  .sv-spin :deep(.n-spin),
  .sv-skeleton-row {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
</style>
