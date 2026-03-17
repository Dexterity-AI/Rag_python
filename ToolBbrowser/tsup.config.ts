import { defineConfig } from "tsup";

export default defineConfig({
  entry: {
    cli: "packages/cli/src/index.ts",
    daemon: "packages/daemon/src/index.ts",
    mcp: "packages/mcp/src/index.ts",
  },
  format: ["esm"],
  dts: false,
  clean: true,
  sourcemap: true,
  target: "node18",
  splitting: true,  // 共享代码会被提取到 chunk
  outDir: "dist",
  banner: {
    js: "#!/usr/bin/env node",
  },
  // 全部 bundle 进去（npx 可用），只保留 ws（CommonJS 动态 require）
  noExternal: [/^(?!ws$).*/],
  external: ["ws"],
});
