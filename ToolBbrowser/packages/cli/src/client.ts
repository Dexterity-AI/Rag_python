/**
 * CDP 客户端 - 与 Chrome DevTools Protocol 通信
 */

import type { Request, Response } from "@bb-browser/shared";
import { applyJq } from "./jq.js";
import { sendCommand as sendCdpCommand } from "./cdp-client.js";

let jqExpression: string | undefined;

export function setJqExpression(expression?: string): void {
  jqExpression = expression;
}

function printJqResults(response: Response): never {
  const target = response.data ?? response;
  const results = applyJq(target, jqExpression || ".");
  for (const result of results) {
    console.log(typeof result === "string" ? result : JSON.stringify(result));
  }
  process.exit(0);
}

export function handleJqResponse(response: Response): void {
  if (jqExpression) {
    printJqResults(response);
  }
}

export async function sendCommand(request: Request): Promise<Response> {
  return sendCdpCommand(request);
}
