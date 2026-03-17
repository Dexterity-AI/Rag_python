/**
 * @bb-browser/shared
 * 共享类型和工具函数
 */

export {
  type ActionType,
  type DaemonStatus,
  type Request,
  type Response,
  type ResponseData,
  type SSEEvent,
  type SSEEventType,
  generateId,
} from "./protocol.js";

export {
  COMMAND_TIMEOUT,
  DAEMON_BASE_URL,
  DAEMON_HOST,
  DAEMON_PORT,
  SSE_HEARTBEAT_INTERVAL,
  SSE_MAX_RECONNECT_ATTEMPTS,
  SSE_RECONNECT_DELAY,
} from "./constants.js";
