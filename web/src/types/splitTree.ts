/**
 * Ghostty-style split tree type definitions.
 *
 * The layout is a binary tree where:
 *   - Leaf nodes display a single view (e.g. scanner, cn-archive)
 *   - Split nodes divide space horizontally or vertically between two children
 *   - ratio controls how much space the left/top child receives (0.05–0.95)
 *
 * Reference: ghostty/src/datastruct/split_tree.zig
 */

/** Unique identifier for a tree node (UUID string). */
export type SplitHandle = string

/** Direction of a split. 'horizontal' splits left/right, 'vertical' splits top/bottom. */
export type SplitLayout = 'horizontal' | 'vertical'

/** Compass directions for spatial navigation between panels. */
export type SpatialDirection = 'left' | 'right' | 'up' | 'down'

/** All view IDs that can be displayed in a panel. */
export type ViewId =
  | 'scanner'
  | 'cn-archive'
  | 'us-archive'
  | 'ticker'
  | 'insights'
  | 'analysis'
  | 'research-agent'
  | 'workspace-list'
  | 'workspace-detail'
  | 'project-detail'
  | 'case-detail'
  | 'template-center'
  | 'run-detail'
  | 'admin-center'

/** Normalized spatial slot in the [0,1]×[0,1] grid. */
export interface SpatialSlot {
  x: number
  y: number
  width: number
  height: number
}

/** A leaf node: displays one view at full panel size. */
export interface LeafNode {
  type: 'leaf'
  handle: SplitHandle
  viewId: ViewId
  /** Optional runtime-computed minimum content width (overrides registry default) */
  minContentWidth?: number
}

/** A split node: divides space between two children along one axis. */
export interface SplitNode {
  type: 'split'
  handle: SplitHandle
  layout: SplitLayout
  /** [0.05, 0.95] — fraction of space the left (or top) child receives. */
  ratio: number
  left: SplitTreeNode
  right: SplitTreeNode
}

/** Union of all node types. */
export type SplitTreeNode = LeafNode | SplitNode

/** The full tree state, persisted to localStorage. */
export interface SplitTreeState {
  root: SplitTreeNode
  zoomedHandle: SplitHandle | null
  activeHandle: SplitHandle
}
