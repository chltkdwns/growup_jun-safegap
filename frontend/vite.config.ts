import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 폰은 개발 서버 주소 하나만 열 수 있어서, /ws 요청은 백엔드(8000)로 넘겨 준다
    proxy: { '/ws': { target: 'ws://localhost:8000', ws: true } },
    // 터널(cloudflared) 주소로 들어오는 요청을 허용한다. 그 밖의 낯선 주소는 Vite가 막는다
    allowedHosts: ['.trycloudflare.com'],
  },
})
