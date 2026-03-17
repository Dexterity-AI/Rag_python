/**
 * AX 树格式化器
 *
 * 将 CDP Accessibility.getFullAXTree 返回的 AXNode[] 转换为
 * 类似 Playwright ariaSnapshot 的文本格式，供 AI Agent 消费。
 */

import type { AXNode } from './cdp-service';

// ============================================================================
// 类型
// ============================================================================

export interface AXRefInfo {
  backendDOMNodeId: number;
  role: string;
  name?: string;
  nth?: number;
}

export interface FormatOptions {
  /** 只输出可交互元素 */
  interactive?: boolean;
  /** 移除空结构节点 */
  compact?: boolean;
  /** 限制树深度 */
  maxDepth?: number;
}

export interface FormatResult {
  snapshot: string;
  refs: Record<string, AXRefInfo>;
}

// ============================================================================
// 角色分类
// ============================================================================

const INTERACTIVE_ROLES = new Set([
  'button', 'link', 'textbox', 'searchbox', 'combobox', 'listbox',
  'checkbox', 'radio', 'slider', 'spinbutton', 'switch',
  'tab', 'menuitem', 'menuitemcheckbox', 'menuitemradio',
  'option', 'treeitem',
]);

/** 跳过的角色（噪声节点） */
const SKIP_ROLES = new Set([
  'none', 'InlineTextBox', 'LineBreak', 'Ignored',
]);

/** 在 interactive 模式下也需要分配 ref 的内容角色 */
const CONTENT_ROLES_WITH_REF = new Set([
  'heading', 'img', 'cell', 'columnheader', 'rowheader',
]);

// ============================================================================
// RoleNameTracker — 统计同 role+name 的重复，标记 [nth=N]
// ============================================================================

interface RoleNameTracker {
  counts: Map<string, number>;
  refsByKey: Map<string, string[]>;
  getKey(role: string, name?: string): string;
  getNextIndex(role: string, name?: string): number;
  trackRef(role: string, name: string | undefined, ref: string): void;
  getDuplicateKeys(): Set<string>;
}

function createRoleNameTracker(): RoleNameTracker {
  const counts = new Map<string, number>();
  const refsByKey = new Map<string, string[]>();
  return {
    counts,
    refsByKey,
    getKey(role: string, name?: string): string {
      return `${role}:${name ?? ''}`;
    },
    getNextIndex(role: string, name?: string): number {
      const key = this.getKey(role, name);
      const current = counts.get(key) ?? 0;
      counts.set(key, current + 1);
      return current;
    },
    trackRef(role: string, name: string | undefined, ref: string): void {
      const key = this.getKey(role, name);
      const refs = refsByKey.get(key) ?? [];
      refs.push(ref);
      refsByKey.set(key, refs);
    },
    getDuplicateKeys(): Set<string> {
      const duplicates = new Set<string>();
      for (const [key, refs] of refsByKey) {
        if (refs.length > 1) duplicates.add(key);
      }
      return duplicates;
    },
  };
}

/** 遍历结束后，清理非重复元素的 nth */
function removeNthFromNonDuplicates(
  refs: Record<string, AXRefInfo>,
  tracker: RoleNameTracker,
): void {
  const duplicateKeys = tracker.getDuplicateKeys();
  for (const refInfo of Object.values(refs)) {
    const key = tracker.getKey(refInfo.role, refInfo.name);
    if (!duplicateKeys.has(key)) {
      delete refInfo.nth;
    }
  }
}

// ============================================================================
// 辅助函数
// ============================================================================

function getProperty(node: AXNode, propName: string): unknown {
  const prop = node.properties?.find(p => p.name === propName);
  return prop?.value?.value;
}

function truncate(text: string, max = 80): string {
  if (text.length <= max) return text;
  return text.slice(0, max - 3) + '...';
}

function indent(depth: number): string {
  return '  '.repeat(depth);
}

function getIndentLevel(line: string): number {
  const match = line.match(/^(\s*)/);
  return match ? Math.floor(match[1].length / 2) : 0;
}

// ============================================================================
// 核心格式化
// ============================================================================

export function formatAXTree(
  nodes: AXNode[],
  urlMap: Map<number, string>,
  options: FormatOptions = {},
): FormatResult {
  // 建树：nodeId → AXNode
  const nodeMap = new Map<string, AXNode>();
  for (const node of nodes) {
    nodeMap.set(node.nodeId, node);
  }

  // 找根节点（第一个非 ignored 节点）
  const rootNode = nodes[0];
  if (!rootNode) {
    return { snapshot: '(empty)', refs: {} };
  }

  const lines: string[] = [];
  const refs: Record<string, AXRefInfo> = {};
  const tracker = createRoleNameTracker();
  let refCounter = 0;

  function nextRef(): string {
    return String(refCounter++);
  }

  function shouldAssignRef(role: string): boolean {
    if (options.interactive) {
      return INTERACTIVE_ROLES.has(role);
    }
    // full 模式：交互元素 + 内容元素
    return INTERACTIVE_ROLES.has(role) || CONTENT_ROLES_WITH_REF.has(role);
  }

  function traverse(nodeId: string, depth: number): void {
    const node = nodeMap.get(nodeId);
    if (!node) return;
    if (node.ignored) {
      // 被忽略的节点仍可能有可见子节点
      for (const childId of node.childIds || []) {
        traverse(childId, depth);
      }
      return;
    }

    // 深度限制
    if (options.maxDepth !== undefined && depth > options.maxDepth) return;

    const role = node.role?.value || '';

    // 跳过噪声角色（但遍历子节点）
    if (SKIP_ROLES.has(role)) {
      for (const childId of node.childIds || []) {
        traverse(childId, depth);
      }
      return;
    }

    const name = node.name?.value?.trim() || '';
    const isInteractive = INTERACTIVE_ROLES.has(role);

    // interactive 模式：跳过非交互节点但遍历子节点
    if (options.interactive && !isInteractive) {
      for (const childId of node.childIds || []) {
        traverse(childId, depth);
      }
      return;
    }

    // StaticText → text: 行
    if (role === 'StaticText') {
      if (name) {
        const displayText = truncate(name, 100);
        lines.push(`${indent(depth)}- text: ${displayText}`);
      }
      return;
    }

    // GenericContainer 无名称时跳过（折叠）
    if ((role === 'GenericContainer' || role === 'generic') && !name) {
      for (const childId of node.childIds || []) {
        traverse(childId, depth);
      }
      return;
    }

    // 构建输出行
    // 角色名称小写化以保持一致性
    const displayRole = role.charAt(0).toLowerCase() + role.slice(1);
    let line = `${indent(depth)}- ${displayRole}`;

    if (name) {
      line += ` "${truncate(name, 50)}"`;
    }

    // heading level
    const level = getProperty(node, 'level');
    if (level !== undefined) {
      line += ` [level=${level}]`;
    }

    // 分配 ref
    const hasBackendId = node.backendDOMNodeId !== undefined;
    if (shouldAssignRef(role) && hasBackendId) {
      const ref = nextRef();
      const nth = tracker.getNextIndex(role, name || undefined);
      tracker.trackRef(role, name || undefined, ref);

      line += ` [ref=${ref}]`;
      if (nth > 0) line += ` [nth=${nth}]`;

      refs[ref] = {
        backendDOMNodeId: node.backendDOMNodeId!,
        role: displayRole,
        name: name || undefined,
        nth,
      };
    }

    // link URL 内联（interactive 模式不需要 URL）
    if (!options.interactive && role === 'link' && node.backendDOMNodeId !== undefined) {
      const url = urlMap.get(node.backendDOMNodeId);
      if (url) {
        lines.push(line);
        lines.push(`${indent(depth + 1)}- /url: ${url}`);
        // 递归子节点
        for (const childId of node.childIds || []) {
          traverse(childId, depth + 1);
        }
        return;
      }
    }

    lines.push(line);

    // interactive 模式：扁平输出，不遍历交互元素的子节点
    if (options.interactive) return;

    // 递归子节点
    for (const childId of node.childIds || []) {
      traverse(childId, depth + 1);
    }
  }

  traverse(rootNode.nodeId, 0);

  // 清理非重复项的 nth
  removeNthFromNonDuplicates(refs, tracker);

  // 从输出行中也清理非重复的 [nth=0]
  const duplicateKeys = tracker.getDuplicateKeys();
  const cleanedLines = lines.map(line => {
    // 移除 [nth=0]（第一个出现的不需要 nth）
    const nthMatch = line.match(/\[nth=0\]/);
    if (nthMatch) {
      return line.replace(' [nth=0]', '');
    }
    // 检查非重复项的 nth 标记并移除
    const refMatch = line.match(/\[ref=(\d+)\].*\[nth=\d+\]/);
    if (refMatch) {
      const refId = refMatch[1];
      const refInfo = refs[refId];
      if (refInfo) {
        const key = tracker.getKey(refInfo.role, refInfo.name);
        if (!duplicateKeys.has(key)) {
          return line.replace(/\s*\[nth=\d+\]/, '');
        }
      }
    }
    return line;
  });

  let snapshot = cleanedLines.join('\n');

  // compact 模式
  if (options.compact) {
    snapshot = compactTree(snapshot);
  }

  return { snapshot: snapshot || '(empty)', refs };
}

// ============================================================================
// Compact 模式 — 移除空结构节点
// ============================================================================

function compactTree(tree: string): string {
  const lines = tree.split('\n');
  const result: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // 保留带 ref 的行
    if (line.includes('[ref=')) {
      result.push(line);
      continue;
    }

    // 保留 text: 行和 /url: 行
    if (line.includes('- text:') || line.includes('- /url:')) {
      result.push(line);
      continue;
    }

    // 保留有名称的行（引号包裹）
    if (line.includes('"')) {
      result.push(line);
      continue;
    }

    // 检查结构节点是否有带 ref 或有内容的子节点
    const currentIndent = getIndentLevel(line);
    let hasRelevantChildren = false;

    for (let j = i + 1; j < lines.length; j++) {
      const childIndent = getIndentLevel(lines[j]);
      if (childIndent <= currentIndent) break;
      if (lines[j].includes('[ref=') || lines[j].includes('"') || lines[j].includes('- text:')) {
        hasRelevantChildren = true;
        break;
      }
    }

    if (hasRelevantChildren) {
      result.push(line);
    }
  }

  return result.join('\n');
}
