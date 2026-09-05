/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'REACT_APP_');
  const processEnv = {};
  Object.keys(env).forEach((key) => {
    processEnv[`process.env.${key}`] = JSON.stringify(env[key]);
  });

  return {
    plugins: [react(), basicSsl()],
    define: {
      ...processEnv,
      'process.env.NODE_ENV': JSON.stringify(mode),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      https: process.env.VITE_HTTPS === 'off' ? false : true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
        },
      },
    },
    build: {
      outDir: 'build',
      sourcemap: false,
      chunkSizeWarningLimit: 600,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['src/setupTests.js'],
    },
  };
});
