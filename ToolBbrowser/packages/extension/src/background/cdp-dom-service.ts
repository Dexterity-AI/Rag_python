/**
 * CDP DOM Service for bb-browser Extension
 *
 * 使用 CDP Accessibility Tree 生成 snapshot，使用 backendDOMNodeId 定位元素。
 *
 * 主要功能：
 * - snapshot: 使用 Accessibility.getFullAXTree（语义化 accessibility 树）
 * - click/hover: 使用 backendDOMNodeId + Input.dispatchMouseEvent
 * - fill/type: 使用 backendDOMNodeId + Input.insertText
 * - get text: 使用 backendDOMNodeId + Runtime.callFunctionOn
 */

import * as cdp from './cdp-service';
import { formatAXTree, type AXRefInfo } from './ax-tree-formatter';

// ============================================================================
// 类型定义
// ============================================================================

/** Ref 元素信息 */
export interface RefInfo {
  /** CDP backendDOMNodeId（主定位方式） */
  backendDOMNodeId?: number;
  /** 元素的 XPath（向后兼容） */
  xpath?: string;
  /** 可访问性角色 */
  role: string;
  /** 可访问名称 */
  name?: string;
  /** 标签名 */
  tagName?: string;
}

/** Snapshot 结果 */
export interface SnapshotResult {
  snapshot: string;
  refs: Record<string, RefInfo>;
}

/** Snapshot 选项 */
export interface SnapshotOptions {
  /** 只输出可交互元素 */
  interactive?: boolean;
  /** 移除空结构节点 */
  compact?: boolean;
  /** 限制树深度 */
  maxDepth?: number;
  /** CSS 选择器范围 */
  selector?: string;
}

// ============================================================================
// 状态管理（使用 chrome.storage.session 持久化，防止 Service Worker 休眠丢失）
// ============================================================================

/** 按 tabId 存储每个 tab 的 snapshot refs（内存缓存） */
const tabSnapshotRefs = new Map<number, Record<string, RefInfo>>();

/** 按 tabId 存储每个 tab 的活动 Frame ID */
const tabActiveFrameId = new Map<number, string | null>();

/** 从 storage 恢复所有 tab 的 refs（Service Worker 唤醒时调用） */
async function loadRefsFromStorage(): Promise<void> {
  try {
    const result = await chrome.storage.session.get('tabSnapshotRefs');
    if (result.tabSnapshotRefs) {
      const stored = result.tabSnapshotRefs as Record<string, Record<string, RefInfo>>;
      for (const [tabIdStr, refs] of Object.entries(stored)) {
        tabSnapshotRefs.set(Number(tabIdStr), refs);
      }
      console.log('[CDPDOMService] Loaded refs from storage:', tabSnapshotRefs.size, 'tabs');
    }
  } catch (e) {
    console.warn('[CDPDOMService] Failed to load refs from storage:', e);
  }
}

/** 保存指定 tab 的 refs 到 storage */
async function saveRefsToStorage(tabId: number, refs: Record<string, RefInfo>): Promise<void> {
  try {
    const result = await chrome.storage.session.get('tabSnapshotRefs');
    const stored = (result.tabSnapshotRefs || {}) as Record<string, Record<string, RefInfo>>;
    stored[String(tabId)] = refs;
    await chrome.storage.session.set({ tabSnapshotRefs: stored });
  } catch (e) {
    console.warn('[CDPDOMService] Failed to save refs to storage:', e);
  }
}

// Service Worker 启动时恢复 refs
loadRefsFromStorage();

// ============================================================================
// Snapshot 实现 — CDP Accessibility Tree
// ============================================================================

/** 从 DOM 树中批量提取 link 的 href */
interface DOMNodeLite {
  backendNodeId: number;
  nodeName: string;
  attributes?: string[];
  children?: DOMNodeLite[];
  contentDocument?: DOMNodeLite;
  shadowRoots?: DOMNodeLite[];
}

async function buildURLMap(
  tabId: number,
  linkBackendIds: Set<number>,
): Promise<Map<number, string>> {
  if (linkBackendIds.size === 0) return new Map();

  const urlMap = new Map<number, string>();
  try {
    const doc = await cdp.getDocument(tabId, { depth: -1, pierce: true });

    function walk(node: DOMNodeLite): void {
      if (linkBackendIds.has(node.backendNodeId)) {
        const attrs = node.attributes || [];
        for (let i = 0; i < attrs.length; i += 2) {
          if (attrs[i] === 'href') {
            urlMap.set(node.backendNodeId, attrs[i + 1]);
            break;
          }
        }
      }
      for (const child of node.children || []) walk(child);
      if (node.contentDocument) walk(node.contentDocument as DOMNodeLite);
      for (const shadow of node.shadowRoots || []) walk(shadow as DOMNodeLite);
    }

    walk(doc as unknown as DOMNodeLite);
  } catch (e) {
    console.warn('[CDPDOMService] Failed to build URL map:', e);
  }
  return urlMap;
}

/**
 * 获取页面快照 — 使用 CDP Accessibility Tree
 */
export async function getSnapshot(
  tabId: number,
  options: SnapshotOptions = {},
): Promise<SnapshotResult> {
  console.log('[CDPDOMService] Getting snapshot via AX tree for tab:', tabId, options);

  // 1. 获取 AX 树
  let axNodes: cdp.AXNode[];

  if (options.selector) {
    // selector 范围：先找 DOM 节点，再获取子树
    try {
      const doc = await cdp.getDocument(tabId, { depth: 0 });
      const nodeId = await cdp.querySelector(tabId, doc.nodeId, options.selector);
      if (!nodeId) throw new Error(`Selector "${options.selector}" not found`);
      axNodes = await cdp.getPartialAccessibilityTree(tabId, nodeId);
    } catch (e) {
      throw new Error(`Selector "${options.selector}" failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  } else {
    axNodes = await cdp.getFullAccessibilityTree(tabId);
  }

  // 2. 收集 link 节点的 backendDOMNodeId
  const linkBackendIds = new Set<number>();
  for (const node of axNodes) {
    if (node.role?.value === 'link' && node.backendDOMNodeId !== undefined) {
      linkBackendIds.add(node.backendDOMNodeId);
    }
  }

  // 3. 批量获取 link 的 href
  const urlMap = await buildURLMap(tabId, linkBackendIds);

  // 4. 格式化 AX 树
  const result = formatAXTree(axNodes, urlMap, {
    interactive: options.interactive,
    compact: options.compact,
    maxDepth: options.maxDepth,
  });

  // 5. 转换为 RefInfo 并存储
  const convertedRefs: Record<string, RefInfo> = {};
  for (const [refId, axRef] of Object.entries(result.refs)) {
    convertedRefs[refId] = {
      backendDOMNodeId: axRef.backendDOMNodeId,
      role: axRef.role,
      name: axRef.name,
    };
  }

  tabSnapshotRefs.set(tabId, convertedRefs);
  await saveRefsToStorage(tabId, convertedRefs);

  console.log('[CDPDOMService] Snapshot complete:', {
    linesCount: result.snapshot.split('\n').length,
    refsCount: Object.keys(convertedRefs).length,
  });

  return { snapshot: result.snapshot, refs: convertedRefs };
}

// ============================================================================
// 元素定位工具 — 通过 backendDOMNodeId
// ============================================================================

/**
 * 获取元素中心坐标（滚动到可见 + getBoundingClientRect）
 */
async function getElementCenter(
  tabId: number,
  backendNodeId: number,
): Promise<{ x: number; y: number }> {
  const objectId = await cdp.resolveNodeByBackendId(tabId, backendNodeId);
  if (!objectId) throw new Error('Failed to resolve node');

  const result = await cdp.callFunctionOn(tabId, objectId, `function() {
    this.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
    const rect = this.getBoundingClientRect();
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }`);

  if (!result || typeof result !== 'object') throw new Error('Failed to get element center');
  return result as { x: number; y: number };
}

/**
 * 在元素上执行 JS 函数
 */
async function evaluateOnElement(
  tabId: number,
  backendNodeId: number,
  fn: string,
  args: unknown[] = [],
): Promise<unknown> {
  const objectId = await cdp.resolveNodeByBackendId(tabId, backendNodeId);
  if (!objectId) throw new Error('Failed to resolve node');
  return cdp.callFunctionOn(tabId, objectId, fn, args);
}

/**
 * 从 RefInfo 获取 backendDOMNodeId，或 fallback 到 xpath
 */
function getBackendNodeId(refInfo: RefInfo): number | null {
  return refInfo.backendDOMNodeId ?? null;
}

// Legacy fallback：通过 xpath 获取元素中心坐标
async function getElementCenterByXPath(
  tabId: number,
  xpath: string,
): Promise<{ x: number; y: number }> {
  const result = await cdp.evaluate(tabId, `
    (function() {
      const result = document.evaluate(
        ${JSON.stringify(xpath)},
        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
      );
      const element = result.singleNodeValue;
      if (!element) return null;
      element.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
      const rect = element.getBoundingClientRect();
      return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()
  `, { returnByValue: true });

  if (!result) throw new Error(`Element not found by xpath: ${xpath}`);
  return result as { x: number; y: number };
}

// ============================================================================
// DOM 操作
// ============================================================================

/**
 * 获取 ref 对应的信息
 */
export async function getRefInfo(tabId: number, ref: string): Promise<RefInfo | null> {
  const refId = ref.startsWith('@') ? ref.slice(1) : ref;

  const refs = tabSnapshotRefs.get(tabId);
  if (refs?.[refId]) return refs[refId];

  // 内存中没有，尝试从 storage 恢复
  if (!tabSnapshotRefs.has(tabId)) {
    await loadRefsFromStorage();
    const loaded = tabSnapshotRefs.get(tabId);
    if (loaded?.[refId]) return loaded[refId];
  }

  return null;
}

/**
 * 清理指定 tab 的状态
 */
export function cleanupTab(tabId: number): void {
  tabSnapshotRefs.delete(tabId);
  tabActiveFrameId.delete(tabId);
}

/**
 * 点击元素
 */
export async function clickElement(
  tabId: number,
  ref: string,
): Promise<{ role: string; name?: string }> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const { role, name } = refInfo;
  const backendNodeId = getBackendNodeId(refInfo);

  let x: number, y: number;
  if (backendNodeId !== null) {
    ({ x, y } = await getElementCenter(tabId, backendNodeId));
  } else if (refInfo.xpath) {
    ({ x, y } = await getElementCenterByXPath(tabId, refInfo.xpath));
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  await cdp.click(tabId, x, y);
  console.log('[CDPDOMService] Clicked element:', { ref, role, name, x, y });
  return { role, name };
}

/**
 * 悬停在元素上
 */
export async function hoverElement(
  tabId: number,
  ref: string,
): Promise<{ role: string; name?: string }> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const { role, name } = refInfo;
  const backendNodeId = getBackendNodeId(refInfo);

  let x: number, y: number;
  if (backendNodeId !== null) {
    ({ x, y } = await getElementCenter(tabId, backendNodeId));
  } else if (refInfo.xpath) {
    ({ x, y } = await getElementCenterByXPath(tabId, refInfo.xpath));
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  await cdp.moveMouse(tabId, x, y);
  console.log('[CDPDOMService] Hovered element:', { ref, role, name, x, y });
  return { role, name };
}

/**
 * 填充输入框（清空后输入）
 */
export async function fillElement(
  tabId: number,
  ref: string,
  text: string,
): Promise<{ role: string; name?: string }> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const { role, name } = refInfo;
  const backendNodeId = getBackendNodeId(refInfo);

  if (backendNodeId !== null) {
    await evaluateOnElement(tabId, backendNodeId, `function() {
      this.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
      this.focus();
      if (this.tagName === 'INPUT' || this.tagName === 'TEXTAREA') {
        this.value = '';
      } else if (this.isContentEditable) {
        this.textContent = '';
      }
    }`);
  } else if (refInfo.xpath) {
    await cdp.evaluate(tabId, `
      (function() {
        const result = document.evaluate(${JSON.stringify(refInfo.xpath)}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        const element = result.singleNodeValue;
        if (!element) throw new Error('Element not found');
        element.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
        element.focus();
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') { element.value = ''; }
        else if (element.isContentEditable) { element.textContent = ''; }
      })()
    `);
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  await cdp.insertText(tabId, text);
  console.log('[CDPDOMService] Filled element:', { ref, role, name, textLength: text.length });
  return { role, name };
}

/**
 * 逐字符输入文本（不清空）
 */
export async function typeElement(
  tabId: number,
  ref: string,
  text: string,
): Promise<{ role: string; name?: string }> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const { role, name } = refInfo;
  const backendNodeId = getBackendNodeId(refInfo);

  if (backendNodeId !== null) {
    await evaluateOnElement(tabId, backendNodeId, `function() {
      this.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
      this.focus();
    }`);
  } else if (refInfo.xpath) {
    await cdp.evaluate(tabId, `
      (function() {
        const result = document.evaluate(${JSON.stringify(refInfo.xpath)}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        const element = result.singleNodeValue;
        if (!element) throw new Error('Element not found');
        element.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
        element.focus();
      })()
    `);
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  for (const char of text) {
    await cdp.pressKey(tabId, char);
  }

  console.log('[CDPDOMService] Typed in element:', { ref, role, name, textLength: text.length });
  return { role, name };
}

/**
 * 获取元素文本内容
 */
export async function getElementText(tabId: number, ref: string): Promise<string> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const backendNodeId = getBackendNodeId(refInfo);

  let text: unknown;
  if (backendNodeId !== null) {
    text = await evaluateOnElement(tabId, backendNodeId, `function() {
      return (this.textContent || '').trim();
    }`);
  } else if (refInfo.xpath) {
    text = await cdp.evaluate(tabId, `
      (function() {
        const result = document.evaluate(${JSON.stringify(refInfo.xpath)}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        const element = result.singleNodeValue;
        if (!element) return '';
        return (element.textContent || '').trim();
      })()
    `);
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  return (text as string) || '';
}

/**
 * 勾选复选框
 */
export async function checkElement(
  tabId: number,
  ref: string,
): Promise<{ role: string; name?: string; wasAlreadyChecked: boolean }> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const { role, name } = refInfo;
  const backendNodeId = getBackendNodeId(refInfo);

  let wasChecked: unknown;
  if (backendNodeId !== null) {
    wasChecked = await evaluateOnElement(tabId, backendNodeId, `function() {
      if (this.type !== 'checkbox' && this.type !== 'radio') throw new Error('Element is not a checkbox or radio');
      const was = this.checked;
      if (!was) { this.checked = true; this.dispatchEvent(new Event('change', { bubbles: true })); }
      return was;
    }`);
  } else if (refInfo.xpath) {
    wasChecked = await cdp.evaluate(tabId, `
      (function() {
        const result = document.evaluate(${JSON.stringify(refInfo.xpath)}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        const element = result.singleNodeValue;
        if (!element) throw new Error('Element not found');
        if (element.type !== 'checkbox' && element.type !== 'radio') throw new Error('Element is not a checkbox or radio');
        const was = element.checked;
        if (!was) { element.checked = true; element.dispatchEvent(new Event('change', { bubbles: true })); }
        return was;
      })()
    `);
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  return { role, name, wasAlreadyChecked: wasChecked as boolean };
}

/**
 * 取消勾选复选框
 */
export async function uncheckElement(
  tabId: number,
  ref: string,
): Promise<{ role: string; name?: string; wasAlreadyUnchecked: boolean }> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const { role, name } = refInfo;
  const backendNodeId = getBackendNodeId(refInfo);

  let wasUnchecked: unknown;
  if (backendNodeId !== null) {
    wasUnchecked = await evaluateOnElement(tabId, backendNodeId, `function() {
      if (this.type !== 'checkbox' && this.type !== 'radio') throw new Error('Element is not a checkbox or radio');
      const was = !this.checked;
      if (!was) { this.checked = false; this.dispatchEvent(new Event('change', { bubbles: true })); }
      return was;
    }`);
  } else if (refInfo.xpath) {
    wasUnchecked = await cdp.evaluate(tabId, `
      (function() {
        const result = document.evaluate(${JSON.stringify(refInfo.xpath)}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        const element = result.singleNodeValue;
        if (!element) throw new Error('Element not found');
        if (element.type !== 'checkbox' && element.type !== 'radio') throw new Error('Element is not a checkbox or radio');
        const was = !element.checked;
        if (!was) { element.checked = false; element.dispatchEvent(new Event('change', { bubbles: true })); }
        return was;
      })()
    `);
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  return { role, name, wasAlreadyUnchecked: wasUnchecked as boolean };
}

/**
 * 选择下拉框选项
 */
export async function selectOption(
  tabId: number,
  ref: string,
  value: string,
): Promise<{ role: string; name?: string; selectedValue: string; selectedLabel: string }> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const { role, name } = refInfo;
  const backendNodeId = getBackendNodeId(refInfo);

  const selectFn = `function(selectValue) {
    if (this.tagName !== 'SELECT') throw new Error('Element is not a <select> element');
    let matched = null;
    for (const opt of this.options) {
      if (opt.value === selectValue || opt.textContent.trim() === selectValue) { matched = opt; break; }
    }
    if (!matched) {
      const lower = selectValue.toLowerCase();
      for (const opt of this.options) {
        if (opt.value.toLowerCase() === lower || opt.textContent.trim().toLowerCase() === lower) { matched = opt; break; }
      }
    }
    if (!matched) {
      const available = Array.from(this.options).map(o => ({ value: o.value, label: o.textContent.trim() }));
      throw new Error('Option not found: ' + selectValue + '. Available: ' + JSON.stringify(available));
    }
    this.value = matched.value;
    this.dispatchEvent(new Event('change', { bubbles: true }));
    return { selectedValue: matched.value, selectedLabel: matched.textContent.trim() };
  }`;

  let result: unknown;
  if (backendNodeId !== null) {
    result = await evaluateOnElement(tabId, backendNodeId, selectFn, [value]);
  } else if (refInfo.xpath) {
    result = await cdp.evaluate(tabId, `
      (function() {
        const selectValue = ${JSON.stringify(value)};
        const xpathResult = document.evaluate(${JSON.stringify(refInfo.xpath)}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        const element = xpathResult.singleNodeValue;
        if (!element) throw new Error('Element not found');
        return (${selectFn}).call(element, selectValue);
      })()
    `);
  } else {
    throw new Error(`No locator for ref "${ref}"`);
  }

  const { selectedValue, selectedLabel } = result as { selectedValue: string; selectedLabel: string };
  return { role, name, selectedValue, selectedLabel };
}

/**
 * 等待元素出现
 */
export async function waitForElement(
  tabId: number,
  ref: string,
  maxWait = 10000,
  interval = 200,
): Promise<void> {
  const refInfo = await getRefInfo(tabId, ref);
  if (!refInfo) throw new Error(`Ref "${ref}" not found. Run snapshot first to get available refs.`);

  const backendNodeId = getBackendNodeId(refInfo);
  let elapsed = 0;

  while (elapsed < maxWait) {
    try {
      if (backendNodeId !== null) {
        // 尝试 resolve 节点，成功则存在
        const objectId = await cdp.resolveNodeByBackendId(tabId, backendNodeId);
        if (objectId) return;
      } else if (refInfo.xpath) {
        const found = await cdp.evaluate(tabId, `
          (function() {
            const result = document.evaluate(${JSON.stringify(refInfo.xpath)}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            return result.singleNodeValue !== null;
          })()
        `);
        if (found) return;
      }
    } catch {
      // 节点不存在，继续等待
    }

    await new Promise(resolve => setTimeout(resolve, interval));
    elapsed += interval;
  }

  throw new Error(`Timeout waiting for element @${ref} after ${maxWait}ms`);
}

// ============================================================================
// Frame 管理
// ============================================================================

export function setActiveFrameId(tabId: number, frameId: string | null): void {
  tabActiveFrameId.set(tabId, frameId);
}

export function getActiveFrameId(tabId: number): string | null {
  return tabActiveFrameId.get(tabId) ?? null;
}

// ============================================================================
// 输入操作
// ============================================================================

export async function pressKey(
  tabId: number,
  key: string,
  modifiers: string[] = [],
): Promise<void> {
  let modifierFlags = 0;
  if (modifiers.includes('Alt')) modifierFlags |= 1;
  if (modifiers.includes('Control')) modifierFlags |= 2;
  if (modifiers.includes('Meta')) modifierFlags |= 4;
  if (modifiers.includes('Shift')) modifierFlags |= 8;

  await cdp.pressKey(tabId, key, { modifiers: modifierFlags });
}

export async function scrollPage(
  tabId: number,
  direction: 'up' | 'down' | 'left' | 'right',
  pixels: number,
): Promise<void> {
  const result = await cdp.evaluate(
    tabId,
    'JSON.stringify({ width: window.innerWidth, height: window.innerHeight })',
  );
  const { width, height } = JSON.parse(result as string);

  const x = width / 2;
  const y = height / 2;

  let deltaX = 0;
  let deltaY = 0;

  switch (direction) {
    case 'up': deltaY = -pixels; break;
    case 'down': deltaY = pixels; break;
    case 'left': deltaX = -pixels; break;
    case 'right': deltaX = pixels; break;
  }

  await cdp.scroll(tabId, x, y, deltaX, deltaY);
}
