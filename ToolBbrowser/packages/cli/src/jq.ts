function splitTopLevel(input: string, separator: string): string[] {
  const parts: string[] = [];
  let current = "";
  let depth = 0;
  let inString = false;

  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    const prev = input[i - 1];
    if (char === '"' && prev !== '\\') inString = !inString;
    if (!inString) {
      if (char === '{' || char === '(' || char === '[') depth++;
      if (char === '}' || char === ')' || char === ']') depth--;
      if (depth === 0 && input.slice(i, i + separator.length) === separator) {
        parts.push(current.trim());
        current = "";
        i += separator.length - 1;
        continue;
      }
    }
    current += char;
  }

  if (current.trim()) parts.push(current.trim());
  return parts;
}

function parseLiteral(value: string): unknown {
  const trimmed = value.trim();
  if (trimmed.startsWith('"') && trimmed.endsWith('"')) return JSON.parse(trimmed);
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed === "null") return null;
  return Number(trimmed);
}

function getField(value: unknown, field: string): unknown {
  return value !== null && typeof value === "object" ? (value as Record<string, unknown>)[field] : undefined;
}

function applySegment(inputs: unknown[], expr: string): unknown[] {
  if (expr === ".") return inputs;
  if (expr.startsWith("select(")) {
    const match = expr.match(/^select\((.+?)\s*(==|>)\s*(.+)\)$/);
    if (!match) throw new Error(`不支持的 jq 表达式: ${expr}`);
    const [, leftExpr, op, rightExpr] = match;
    const expected = parseLiteral(rightExpr);
    return inputs.filter((item) => {
      const left = applyExpression([item], leftExpr)[0];
      return op === "==" ? left === expected : Number(left) > Number(expected);
    });
  }
  if (expr.startsWith("{") && expr.endsWith("}")) {
    const body = expr.slice(1, -1).trim();
    if (!body) return inputs.map(() => ({}));
    const entries = splitTopLevel(body, ",");
    return inputs.map((item) => {
      const obj: Record<string, unknown> = {};
      for (const entry of entries) {
        const colon = entry.indexOf(":");
        if (colon === -1) {
          const key = entry.trim().replace(/^\./, "");
          obj[key] = applyExpression([item], `.${key}`)[0];
        } else {
          const key = entry.slice(0, colon).trim();
          const valueExpr = entry.slice(colon + 1).trim();
          obj[key] = applyExpression([item], valueExpr)[0];
        }
      }
      return obj;
    });
  }
  if (!expr.startsWith(".")) throw new Error(`不支持的 jq 表达式: ${expr}`);

  let current = inputs;
  let remaining = expr.slice(1);
  while (remaining.length > 0) {
    if (remaining.startsWith("[]")) {
      current = current.flatMap((item) => Array.isArray(item) ? item : []);
      remaining = remaining.slice(2);
    } else if (remaining.startsWith("[")) {
      const match = remaining.match(/^\[(-?\d+)\]/);
      if (!match) throw new Error(`不支持的 jq 表达式: .${remaining}`);
      const index = Number(match[1]);
      current = current.map((item) => {
        if (!Array.isArray(item)) return undefined;
        return item[index >= 0 ? index : item.length + index];
      });
      remaining = remaining.slice(match[0].length);
    } else if (remaining.startsWith(".")) {
      remaining = remaining.slice(1);
    } else {
      const match = remaining.match(/^([A-Za-z_][A-Za-z0-9_]*)/);
      if (!match) throw new Error(`不支持的 jq 表达式: .${remaining}`);
      const field = match[1];
      current = current.map((item) => getField(item, field));
      remaining = remaining.slice(field.length);
    }
  }
  return current;
}

function applyExpression(inputs: unknown[], expression: string): unknown[] {
  const segments = splitTopLevel(expression.trim(), "|");
  return segments.reduce((current, segment) => applySegment(current, segment.trim()), inputs);
}

export function applyJq(data: unknown, expression: string): unknown[] {
  return applyExpression([data], expression).filter((item) => item !== undefined);
}
