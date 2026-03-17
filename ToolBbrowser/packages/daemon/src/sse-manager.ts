/**
 * SSE 连接管理
 *
 * 职责：
 * - 管理与扩展的 SSE 长连接
 * - 发送心跳保活
 * - 推送命令事件
 */

import type { ServerResponse } from "node:http";
import type { Request } from "@bb-browser/shared";
import { SSE_HEARTBEAT_INTERVAL } from "@bb-browser/shared";

/**
 * SSE 连接管理器
 */
export class SSEManager {
  private connection: ServerResponse | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;

  /**
   * 检查是否有活跃连接
   */
  get isConnected(): boolean {
    return this.connection !== null && !this.connection.writableEnded;
  }

  /**
   * 建立 SSE 连接
   */
  connect(res: ServerResponse): void {
    // 关闭旧连接
    if (this.connection) {
      this.disconnect();
    }

    // 设置 SSE 响应头
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "Access-Control-Allow-Origin": "*",
    });

    this.connection = res;

    // 发送 connected 事件
    this.sendEvent("connected", { time: Date.now() });

    // 启动心跳
    this.startHeartbeat();

    // 监听连接关闭
    res.on("close", () => {
      this.cleanupConnection();
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.stopHeartbeat();

    if (this.connection && !this.connection.writableEnded) {
      this.connection.end();
    }

    this.connection = null;
  }

  /**
   * 发送命令给扩展
   */
  sendCommand(request: Request): boolean {
    return this.sendEvent("command", request);
  }

  /**
   * 发送 SSE 事件
   */
  private sendEvent(eventType: string, data: unknown): boolean {
    if (!this.connection || this.connection.writableEnded) {
      return false;
    }

    try {
      this.connection.write(`event: ${eventType}\n`);
      this.connection.write(`data: ${JSON.stringify(data)}\n\n`);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 启动心跳定时器
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      const sent = this.sendEvent("heartbeat", { time: Date.now() });
      if (!sent) {
        this.cleanupConnection();
      }
    }, SSE_HEARTBEAT_INTERVAL);
  }

  /**
   * 停止心跳定时器
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 清理连接
   */
  private cleanupConnection(): void {
    this.stopHeartbeat();
    this.connection = null;
  }
}
