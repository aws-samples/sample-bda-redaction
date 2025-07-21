/*
 * © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 *
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement
 * available at http://aws.amazon.com/agreement or other written agreement between
 * Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
// export default defineConfig({
//   plugins: [react()],
// })

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, process.cwd(), "");
  const {VITE_BASE, VITE_APIGW, VITE_API_PATH} = env;
  const APIPATH = `${VITE_BASE}${VITE_API_PATH}`;

  process.env.VITE_APIPATH = APIPATH;

  const proxy = {
    [APIPATH]: {
      target: VITE_APIGW ,
      changeOrigin: true,
    }
  };

  const vite_base = VITE_BASE.trim() == "" ? undefined : VITE_BASE;

  return {
      plugins: [react()],
      base: vite_base,
      server: {
          proxy: proxy,
      },
      assetsInclude: ['**/*.png'],
      build: {
          assetsInlineLimit: 122880,  // 120kb for logo
      },
  };
});