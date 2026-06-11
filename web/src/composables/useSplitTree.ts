/**
 * Ghostty-style split tree composable.
 *
 * Manages a binary tree of horizontal/vertical splits that divide the viewport
 * into resizable panels. Each leaf panel displays one registered view.
 *
 * Algorithms ported from: ghostty/src/datastruct/split_tree.zig
 *   - split()       → L505-569
 *   - remove()      → L576-613
 *   - resizeInPlace→ L483-495
 *   - equalize()    → L759-795
 *   - spatial()     → L968-1048
 *   - nearest()     → L390-474
 */
import { reactive, computed, toRaw } from 'vue'
import type {
  SplitHandle, SplitLayout, SpatialDirection,
  LeafNode, SplitNode, SplitTreeNode, SplitTreeState, SpatialSlot, ViewId,
} from '../types/splitTree'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'my-doge-split-layout'
const MIN_RATIO = 0.05
const MAX_RATIO = 0.95

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

let _idCounter = 0
function uid(): SplitHandle {
  return `n${Date.now().toString(36)}_${(++_idCounter).toString(36)}`
}

function createLeaf(viewId: ViewId): LeafNode {
  return { type: 'leaf', handle: uid(), viewId }
}

function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

/** Count leaf nodes in a subtree. */
function countLeaves(node: SplitTreeNode): number {
  if (node.type === 'leaf') return 1
  return countLeaves(node.left) + countLeaves(node.right)
}

/** Find a node by handle. Returns the node or null. */
function findNode(root: SplitTreeNode, handle: SplitHandle): SplitTreeNode | null {
  if (root.handle === handle) return root
  if (root.type === 'leaf') return null
  return findNode(root.left, handle) ?? findNode(root.right, handle)
}

/** Collect all leaf nodes. */
function collectLeaves(node: SplitTreeNode): LeafNode[] {
  if (node.type === 'leaf') return [node]
  return [...collectLeaves(node.left), ...collectLeaves(node.right)]
}

/** Find the first leaf in in-order traversal. */
function firstLeaf(node: SplitTreeNode): LeafNode {
  if (node.type === 'leaf') return node
  return firstLeaf(node.left)
}

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

function loadFromStorage(): SplitTreeState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed?.root || !parsed?.activeHandle) return null
    return parsed as SplitTreeState
  } catch {
    return null
  }
}

let _persistTimer: ReturnType<typeof setTimeout> | null = null

// ---------------------------------------------------------------------------
// Spatial calculation  (ghostty: spatial() + fillSpatialSlots L968-1048)
// ---------------------------------------------------------------------------

function fillSpatialSlots(
  node: SplitTreeNode,
  parentSlot: SpatialSlot,
  slots: Map<SplitHandle, SpatialSlot>,
): void {
  slots.set(node.handle, { ...parentSlot })

  if (node.type === 'leaf') return

  const { layout, ratio, left, right } = node

  const leftSlot: SpatialSlot = layout === 'horizontal'
    ? { x: parentSlot.x, y: parentSlot.y,
        width: parentSlot.width * ratio, height: parentSlot.height }
    : { x: parentSlot.x, y: parentSlot.y,
        width: parentSlot.width, height: parentSlot.height * ratio }

  const rightSlot: SpatialSlot = layout === 'horizontal'
    ? { x: parentSlot.x + parentSlot.width * ratio, y: parentSlot.y,
        width: parentSlot.width * (1 - ratio), height: parentSlot.height }
    : { x: parentSlot.x, y: parentSlot.y + parentSlot.height * ratio,
        width: parentSlot.width, height: parentSlot.height * (1 - ratio) }

  fillSpatialSlots(left, leftSlot, slots)
  fillSpatialSlots(right, rightSlot, slots)
}

function getSpatialSlots(root: SplitTreeNode): Map<SplitHandle, SpatialSlot> {
  const slots = new Map<SplitHandle, SpatialSlot>()
  fillSpatialSlots(root, { x: 0, y: 0, width: 1, height: 1 }, slots)
  return slots
}

// ---------------------------------------------------------------------------
// Spatial navigation  (ghostty: nearest() L390-435, nearestWrapped() L438-474)
// ---------------------------------------------------------------------------

function nearest(
  slots: Map<SplitHandle, SpatialSlot>,
  leaves: LeafNode[],
  fromHandle: SplitHandle,
  direction: SpatialDirection,
  overrideSlot?: SpatialSlot,
): SplitHandle | null {
  const source = overrideSlot ?? slots.get(fromHandle)
  if (!source) return null

  let result: SplitHandle | null = null
  let minDist = Infinity

  for (const leaf of leaves) {
    if (leaf.handle === fromHandle) continue
    const slot = slots.get(leaf.handle)
    if (!slot) continue

    // Direction check: candidate must be in the correct direction
    let valid = false
    switch (direction) {
      case 'left':   valid = slot.x + slot.width <= source.x + 1e-6; break
      case 'right':  valid = slot.x >= source.x + source.width - 1e-6; break
      case 'up':     valid = slot.y + slot.height <= source.y + 1e-6; break
      case 'down':   valid = slot.y >= source.y + source.height - 1e-6; break
    }
    if (!valid) continue

    // Distance between slot centers
    const dx = (slot.x + slot.width / 2) - (source.x + source.width / 2)
    const dy = (slot.y + slot.height / 2) - (source.y + source.height / 2)
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist < minDist) {
      minDist = dist
      result = leaf.handle
    }
  }
  return result
}

function nearestWrapped(
  root: SplitTreeNode,
  fromHandle: SplitHandle,
  direction: SpatialDirection,
): SplitHandle | null {
  const slots = getSpatialSlots(root)
  const leaves = collectLeaves(root)
  const source = slots.get(fromHandle)
  if (!source) return null

  // Try direct
  const direct = nearest(slots, leaves, fromHandle, direction)
  if (direct) return direct

  // Wrap: shift source slot by 1 unit in opposite direction
  const wrapped = { ...source }
  switch (direction) {
    case 'left':   wrapped.x += 1; break
    case 'right':  wrapped.x -= 1; break
    case 'up':     wrapped.y += 1; break
    case 'down':   wrapped.y -= 1; break
  }
  return nearest(slots, leaves, fromHandle, direction, wrapped)
}

// ---------------------------------------------------------------------------
// Tree mutation helpers
// ---------------------------------------------------------------------------

interface ParentRef {
  parent: SplitNode
  side: 'left' | 'right'
}

/** Walk the tree and record the parent path to a target handle. */
function findParent(
  node: SplitTreeNode,
  target: SplitHandle,
  path: ParentRef[] = [],
): ParentRef[] | null {
  if (node.type === 'leaf') return null
  if (node.left.handle === target) return [...path, { parent: node, side: 'left' }]
  if (node.right.handle === target) return [...path, { parent: node, side: 'right' }]
  return findParent(node.left, target, path) ?? findParent(node.right, target, path)
}

/** Equalize ratios based on leaf weight (ghostty: equalize() L759-795). */
function equalizeNode(node: SplitTreeNode): void {
  if (node.type === 'leaf') return
  const wLeft = weight(node.left, node.layout, 0)
  const wRight = weight(node.right, node.layout, 0)
  node.ratio = wLeft / (wLeft + wRight)
  equalizeNode(node.left)
  equalizeNode(node.right)
}

function weight(node: SplitTreeNode, layout: SplitLayout, acc: number): number {
  if (node.type === 'leaf') return acc + 1
  if (node.layout === layout)
    return weight(node.left, layout, acc) + weight(node.right, layout, acc)
  return 1  // orthogonal split counts as single unit
}

// ---------------------------------------------------------------------------
// Singleton state (module-level so all consumers share it)
// ---------------------------------------------------------------------------

let _initialized = false
const state = reactive<SplitTreeState>(loadFromStorage() ?? {
  root: createLeaf('scanner'),
  zoomedHandle: null,
  activeHandle: '',
})
if (!state.activeHandle) {
  state.activeHandle = firstLeaf(state.root).handle
}
_initialized = true

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useSplitTree() {

  // -- Computed --

  const root = computed(() => state.root)
  const activeHandle = computed(() => state.activeHandle)
  const zoomedHandle = computed(() => state.zoomedHandle)
  const leafCount = computed(() => countLeaves(state.root))
  const isZoomed = computed(() => state.zoomedHandle !== null)

  /** The root to render: if zoomed, show only the zoomed leaf. */
  const visibleRoot = computed<SplitTreeNode>(() => {
    if (state.zoomedHandle) {
      const found = findNode(state.root, state.zoomedHandle)
      if (found) return found
    }
    return state.root
  })

  // -- Persistence --

  let _persistTimer: ReturnType<typeof setTimeout> | null = null
  function persist() {
    if (_persistTimer) clearTimeout(_persistTimer)
    _persistTimer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toRaw(state)))
    }, 300)
  }

  function forcePersist() {
    if (_persistTimer) clearTimeout(_persistTimer)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toRaw(state)))
  }

  // -- Tree operations --

  /**
   * Split a leaf node into a split with two children.
   * (ghostty: split() L505-569)
   */
  function split(handle: SplitHandle, layout: SplitLayout, viewId: ViewId) {
    const node = findNode(state.root, handle)
    if (!node || node.type !== 'leaf') return

    // Build a new split replacing this leaf
    const newLeaf = createLeaf(viewId)
    const splitNode: SplitNode = {
      type: 'split',
      handle: uid(),
      layout,
      ratio: 0.5,
      left: { ...node },   // original leaf
      right: newLeaf,
    }

    // If splitting the root, replace root
    if (state.root.handle === handle) {
      state.root = splitNode
    } else {
      // Find parent and replace the child reference
      const parentPath = findParent(state.root, handle)
      if (parentPath && parentPath.length > 0) {
        const { parent, side } = parentPath[parentPath.length - 1]
        if (side === 'left') parent.left = splitNode
        else parent.right = splitNode
      }
    }

    state.activeHandle = newLeaf.handle
    state.zoomedHandle = null
    persist()
  }

  /**
   * Remove a leaf node. Its parent split is replaced by its sibling.
   * (ghostty: remove() L576-613)
   */
  function remove(handle: SplitHandle) {
    // Cannot remove the last panel
    if (state.root.type === 'leaf') return
    // Cannot remove the root itself
    if (state.root.handle === handle) return

    const node = findNode(state.root, handle)
    if (!node || node.type !== 'leaf') return

    // Find parent
    const parentPath = findParent(state.root, handle)
    if (!parentPath || parentPath.length === 0) return

    const { parent, side } = parentPath[parentPath.length - 1]
    const sibling = side === 'left' ? parent.right : parent.left

    // If the parent IS the root, replace root with sibling
    if (state.root.handle === parent.handle) {
      state.root = deepClone(sibling)
    } else {
      // Find grandparent and replace parent reference with sibling
      const grandPath = findParent(state.root, parent.handle)
      if (grandPath && grandPath.length > 0) {
        const { parent: grandparent, side: gpSide } = grandPath[grandPath.length - 1]
        if (gpSide === 'left') grandparent.left = deepClone(sibling)
        else grandparent.right = deepClone(sibling)
      }
    }

    // Fix active handle
    if (state.activeHandle === handle) {
      state.activeHandle = firstLeaf(state.root).handle
    }
    if (state.zoomedHandle === handle) {
      state.zoomedHandle = null
    }
    persist()
  }

  /**
   * Resize a split node by setting its ratio directly (in-place mutation).
   * (ghostty: resizeInPlace() L483-495)
   */
  function resize(handle: SplitHandle, newRatio: number) {
    const node = findNode(state.root, handle)
    if (!node || node.type !== 'split') return
    node.ratio = Math.max(MIN_RATIO, Math.min(MAX_RATIO, newRatio))
    // Don't persist on every move — the caller persists on pointerup
  }

  /**
   * Equalize all splits so each leaf gets equal space.
   * (ghostty: equalize() L759-795)
   */
  function equalize() {
    equalizeNode(state.root)
    persist()
  }

  /** Zoom a panel to fill the entire viewport. */
  function zoom(handle: SplitHandle | null) {
    state.zoomedHandle = handle
    persist()
  }

  /** Toggle zoom on a handle. */
  function toggleZoom(handle: SplitHandle) {
    zoom(state.zoomedHandle === handle ? null : handle)
  }

  // -- Panel management --

  /** Set the active panel. */
  function setActive(handle: SplitHandle) {
    state.activeHandle = handle
  }

  /** Change the view displayed in a leaf. */
  function setView(handle: SplitHandle, viewId: ViewId) {
    const node = findNode(state.root, handle)
    if (!node || node.type !== 'leaf') return
    node.viewId = viewId
    persist()
  }

  /** Check if a panel can be closed (not the last one). */
  function canClose(): boolean {
    return countLeaves(state.root) > 1
  }

  // -- Navigation --

  /** Spatial navigation: move to the nearest panel in a direction. */
  function gotoSpatial(direction: SpatialDirection): SplitHandle | null {
    const target = nearestWrapped(state.root, state.activeHandle, direction)
    if (target) state.activeHandle = target
    return target
  }

  /** Linear navigation: previous leaf in in-order traversal. */
  function gotoPrevious(): SplitHandle | null {
    const leaves = collectLeaves(state.root)
    const idx = leaves.findIndex(l => l.handle === state.activeHandle)
    if (idx > 0) {
      state.activeHandle = leaves[idx - 1].handle
      return leaves[idx - 1].handle
    }
    // Wrap
    if (leaves.length > 1) {
      state.activeHandle = leaves[leaves.length - 1].handle
      return leaves[leaves.length - 1].handle
    }
    return null
  }

  /** Linear navigation: next leaf in in-order traversal. */
  function gotoNext(): SplitHandle | null {
    const leaves = collectLeaves(state.root)
    const idx = leaves.findIndex(l => l.handle === state.activeHandle)
    if (idx < leaves.length - 1) {
      state.activeHandle = leaves[idx + 1].handle
      return leaves[idx + 1].handle
    }
    // Wrap
    if (leaves.length > 1) {
      state.activeHandle = leaves[0].handle
      return leaves[0].handle
    }
    return null
  }

  // -- Layout presets --

  function applyPreset(preset: 'single' | 'h-split' | 'v-split' | 'quad', defaultView: ViewId = 'scanner') {
    const leaves = collectLeaves(state.root)
    const currentView = leaves.find(l => l.handle === state.activeHandle)?.viewId ?? defaultView
    const secondView: ViewId = currentView === 'ticker' ? 'cn-archive' : 'ticker'

    switch (preset) {
      case 'single':
        state.root = createLeaf(currentView)
        break
      case 'h-split':
        state.root = {
          type: 'split', handle: uid(), layout: 'horizontal', ratio: 0.5,
          left: createLeaf(currentView),
          right: createLeaf(secondView),
        }
        break
      case 'v-split':
        state.root = {
          type: 'split', handle: uid(), layout: 'vertical', ratio: 0.5,
          left: createLeaf(currentView),
          right: createLeaf(secondView),
        }
        break
      case 'quad':
        state.root = {
          type: 'split', handle: uid(), layout: 'horizontal', ratio: 0.5,
          left: createLeaf(currentView),
          right: {
            type: 'split', handle: uid(), layout: 'vertical', ratio: 0.5,
            left: createLeaf('us-archive'),
            right: createLeaf('insights'),
          },
        }
        break
    }
    state.activeHandle = firstLeaf(state.root).handle
    state.zoomedHandle = null
    forcePersist()
  }

  return {
    // Reactive state
    root, activeHandle, zoomedHandle, leafCount, isZoomed, visibleRoot, state,

    // Tree operations
    split, remove, resize, equalize,
    zoom, toggleZoom,

    // Panel management
    setActive, setView, canClose,

    // Navigation
    gotoPrevious, gotoNext, gotoSpatial,

    // Presets
    applyPreset,

    // Persistence
    persist: forcePersist,
  }
}
