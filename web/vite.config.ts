import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const customer = mode === 'customer';
  return {
    root: resolve(webRoot, customer ? 'customer' : 'support'),
    plugins: [react()],
    server: { host: '127.0.0.1', port: customer ? 5174 : 5173, strictPort: true },
    preview: { host: '127.0.0.1', port: customer ? 4174 : 4173, strictPort: true },
    build: { outDir: resolve(webRoot, 'dist', customer ? 'customer' : 'support'), emptyOutDir: true },
  };
});
