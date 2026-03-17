/**
 * HTTP 服务器
 *
 * 提供 REST API 端点：
 * - POST /command: CLI 发送命令
 * - GET /sse: 扩展订阅命令流
 * - POST /result: 扩展回传结果
 * - GET /status: 查询状态
 */

import { createServer, type Server, type IncomingMessage, type ServerResponse } from "node:http";
import type { Request, Response } from "@bb-browser/shared";
import { DAEMON_PORT } from "@bb-browser/shared";
import { SSEManager } from "./sse-manager.js";
import { RequestManager } from "./request-manager.js";

export interface HttpServerOptions {
  host?: string;
  port?: number;
  onShutdown?: () => void;
}

/**
 * HTTP 服务器
 */
export class HttpServer {
  private server: Server | null = null;
  private host: string;
  private port: number;
  private startTime: number = 0;
  private onShutdown?: () => void;

  readonly sseManager = new SSEManager();
  readonly requestManager = new RequestManager();

  constructor(options: HttpServerOptions = {}) {
    this.host = options.host ?? "127.0.0.1";
    this.port = options.port ?? DAEMON_PORT;
    this.onShutdown = options.onShutdown;
  }

  /**
   * 启动服务器
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = createServer((req, res) => {
        this.handleRequest(req, res);
      });

      this.server.on("error", (error) => {
        reject(error);
      });

      this.server.listen(this.port, this.host, () => {
        this.startTime = Date.now();
        resolve();
      });
    });
  }

  /**
   * 停止服务器
   */
  async stop(): Promise<void> {
    // 清理 pending 请求
    this.requestManager.clear();

    // 断开 SSE 连接
    this.sseManager.disconnect();

    // 关闭服务器
    if (this.server) {
      return new Promise((resolve) => {
        this.server!.close(() => {
          resolve();
        });
      });
    }
  }

  /**
   * 获取运行时间（秒）
   */
  get uptime(): number {
    if (this.startTime === 0) {
      return 0;
    }
    return Math.floor((Date.now() - this.startTime) / 1000);
  }

  /**
   * 路由请求
   */
  private handleRequest(req: IncomingMessage, res: ServerResponse): void {
    // CORS 支持
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    const url = req.url ?? "/";

    if (req.method === "POST" && url === "/command") {
      this.handleCommand(req, res);
    } else if (req.method === "GET" && url === "/sse") {
      this.handleSSE(req, res);
    } else if (req.method === "POST" && url === "/result") {
      this.handleResult(req, res);
    } else if (req.method === "GET" && url === "/status") {
      this.handleStatus(req, res);
    } else if (req.method === "POST" && url === "/shutdown") {
      this.handleShutdown(req, res);
    } else {
      this.sendJson(res, 404, { error: "Not found" });
    }
  }

  /**
   * POST /command - CLI 发送命令
   */
  private async handleCommand(req: IncomingMessage, res: ServerResponse): Promise<void> {
    try {
      const body = await this.readBody(req);
      const request = JSON.parse(body) as Request;

      // 检查扩展是否连接
      if (!this.sseManager.isConnected) {
        this.sendJson(res, 503, {
          id: request.id,
          success: false,
          error: "Extension not connected",
        });
        return;
      }

      // 创建 Promise 等待响应
      const responsePromise = new Promise<Response>((resolve, reject) => {
        this.requestManager.add(request.id, resolve, reject);
      });

      // 推送命令给扩展
      const sent = this.sseManager.sendCommand(request);
      if (!sent) {
        // 移除 pending 请求
        this.requestManager.resolve(request.id, {
          id: request.id,
          success: false,
          error: "Failed to send command to extension",
        });
        this.sendJson(res, 503, {
          id: request.id,
          success: false,
          error: "Failed to send command to extension",
        });
        return;
      }

      // 等待响应
      try {
        const response = await responsePromise;
        this.sendJson(res, 200, response);
      } catch (error) {
        // 超时或其他错误
        this.sendJson(res, 408, {
          id: request.id,
          success: false,
          error: error instanceof Error ? error.message : "Unknown error",
        });
      }
    } catch (error) {
      this.sendJson(res, 400, {
        success: false,
        error: error instanceof Error ? error.message : "Invalid request",
      });
    }
  }

  /**
   * GET /sse - 扩展订阅命令流
   */
  private handleSSE(_req: IncomingMessage, res: ServerResponse): void {
    this.sseManager.connect(res);
  }

  /**
   * POST /result - 扩展回传结果
   */
  private async handleResult(req: IncomingMessage, res: ServerResponse): Promise<void> {
    try {
      const body = await this.readBody(req);
      const result = JSON.parse(body) as Response;

      // 匹配 pending 请求
      const resolved = this.requestManager.resolve(result.id, result);

      if (resolved) {
        this.sendJson(res, 200, { code: 0, message: "ok" });
      } else {
        // 找不到对应请求（可能已超时）
        this.sendJson(res, 200, { code: 1, message: "Request not found or already expired" });
      }
    } catch (error) {
      this.sendJson(res, 400, {
        code: -1,
        message: error instanceof Error ? error.message : "Invalid request",
      });
    }
  }

  /**
   * GET /status - 查询状态
   */
  private handleStatus(_req: IncomingMessage, res: ServerResponse): void {
    this.sendJson(res, 200, {
      running: true,
      extensionConnected: this.sseManager.isConnected,
      pendingRequests: this.requestManager.pendingCount,
      uptime: this.uptime,
    });
  }

  /**
   * POST /shutdown - 关闭服务器
   */
  private handleShutdown(_req: IncomingMessage, res: ServerResponse): void {
    this.sendJson(res, 200, { code: 0, message: "Shutting down" });
    
    // 延迟关闭，确保响应发送完成
    setTimeout(() => {
      if (this.onShutdown) {
        this.onShutdown();
      }
    }, 100);
  }

  /**
   * 读取请求体
   */
  private readBody(req: IncomingMessage): Promise<string> {
    return new Promise((resolve, reject) => {
      const chunks: Buffer[] = [];

      req.on("data", (chunk: Buffer) => {
        chunks.push(chunk);
      });

      req.on("end", () => {
        resolve(Buffer.concat(chunks).toString("utf-8"));
      });

      req.on("error", (error) => {
        reject(error);
      });
    });
  }

  /**
   * 发送 JSON 响应
   */
  private sendJson(res: ServerResponse, status: number, data: unknown): void {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify(data));
  }
}
