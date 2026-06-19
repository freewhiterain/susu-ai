import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 部署：输出独立运行包（含最小 node_modules），镜像更小。
  // 仅在 Docker 构建时启用——standalone 在 Windows 本地构建需符号链接权限（EPERM），
  // 故用 DOCKER_BUILD 环境变量隔离，保证本地 `pnpm build` 也能通过。
  output: process.env.DOCKER_BUILD === "1" ? "standalone" : undefined,
  // 后端 API 反向代理：前端调用 /api/* 透传到后端，避免浏览器 CORS。
  async rewrites() {
    const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
