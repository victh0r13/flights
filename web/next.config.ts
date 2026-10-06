import type { NextConfig } from "next";

// O navegador sempre chama /api/... no próprio Next, que repassa para a API em Python
// (FastAPI). Assim front e API parecem um só site e não há problema de CORS.
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  devIndicators: false, // esconde o botão "N" do Next: a interface abre como aplicativo
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
