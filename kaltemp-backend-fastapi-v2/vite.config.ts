import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // Reenvía /api/* al backend FastAPI (puerto 8000) -- necesario porque
      // DataSyncModal.tsx usa fetch('/api/...') con ruta relativa (heredado
      // del proyecto Express original, donde Vite y el servidor compartían
      // el mismo puerto). El resto de la app usa VITE_API_BASE_URL directo
      // vía src/services/api.ts y no depende de este proxy.
      proxy: {
        '/api': {
          target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify: file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      // Se excluye kaltemp_matrix*.duckdb explícitamente: es un archivo binario
      // grande que el backend/scripts de sync abren y bloquean en Windows -- si
      // Vite intenta vigilarlo y lo encuentra bloqueado (EBUSY), el proceso de
      // "npm run dev" completo se cae. Un binario de base de datos no necesita
      // hot-reload nunca, así que se ignora siempre, con o sin DISABLE_HMR.
      watch:
        process.env.DISABLE_HMR === 'true'
          ? null
          : { ignored: ['**/*.duckdb', '**/*.duckdb.bak', '**/kaltemp_matrix*'] },
    },
  };
});
