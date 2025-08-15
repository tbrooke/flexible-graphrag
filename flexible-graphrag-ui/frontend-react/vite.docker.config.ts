import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Docker-specific configuration
const CMIS_BASE_URL = 'http://host.docker.internal:8080';  // Docker networking
const ALFRESCO_BASE_URL = 'http://host.docker.internal:8080';  // Docker networking

export default defineConfig({
  plugins: [react()],
  base: '/ui/react/',
  server: {
    port: 3000,
    host: '0.0.0.0',
    // No proxy needed - nginx handles API routing
  },
  define: {
    'import.meta.env.VITE_CMIS_BASE_URL': JSON.stringify(CMIS_BASE_URL),
    'import.meta.env.VITE_ALFRESCO_BASE_URL': JSON.stringify(ALFRESCO_BASE_URL),
  }
});
