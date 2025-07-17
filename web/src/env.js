// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { createEnv } from "@t3-oss/env-nextjs";
import { z } from "zod";

/**
 * 在瀏覽器環境中轉換 URL 中的 0.0.0.0 為實際 IP 地址
 * @param {string} url - 原始 URL
 * @returns {string} 轉換後的 URL
 */
function convertZeroIPToActualInBrowser(url) {
  try {
    // 只在瀏覽器環境中進行轉換
    if (typeof window === 'undefined' || !url || !url.includes('0.0.0.0')) {
      return url;
    }

    const hostname = window.location.hostname;
    // 如果不是 localhost，很可能就是本機 IP
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      const convertedUrl = url.replace('0.0.0.0', hostname);
      console.log(`🔄 前端自動轉換 0.0.0.0 為實際 IP: ${url} → ${convertedUrl}`);
      return convertedUrl;
    }

    // 如果是 localhost，使用 localhost 替代
    const convertedUrl = url.replace('0.0.0.0', 'localhost');
    console.log(`🔄 前端使用 localhost 替代 0.0.0.0: ${url} → ${convertedUrl}`);
    return convertedUrl;
  } catch (error) {
    // 如果轉換過程中出錯，返回原始 URL
    console.warn('環境變數轉換時發生錯誤，使用原始 URL:', error);
    return url;
  }
}

// 獲取並處理 API URL
function getProcessedApiUrl() {
  try {
    const rawUrl = process.env.NEXT_PUBLIC_API_URL;
    return rawUrl ? convertZeroIPToActualInBrowser(rawUrl) : undefined;
  } catch (error) {
    console.warn('處理 API URL 時發生錯誤:', error);
    return process.env.NEXT_PUBLIC_API_URL;
  }
}

export const env = createEnv({
  /**
   * Specify your server-side environment variables schema here. This way you can ensure the app
   * isn't built with invalid env vars.
   */
  server: {
    NODE_ENV: z.enum(["development", "test", "production"]),
    AMPLITUDE_API_KEY: z.string().optional(),
    GITHUB_OAUTH_TOKEN: z.string().optional(),
  },

  /**
   * Specify your client-side environment variables schema here. This way you can ensure the app
   * isn't built with invalid env vars. To expose them to the client, prefix them with
   * `NEXT_PUBLIC_`.
   */
  client: {
    NEXT_PUBLIC_API_URL: z.string().optional(),
    NEXT_PUBLIC_STATIC_WEBSITE_ONLY: z.boolean().optional(),
  },

  /**
   * You can't destruct `process.env` as a regular object in the Next.js edge runtimes (e.g.
   * middlewares) or client-side so we need to destruct manually.
   */
  runtimeEnv: {
    NODE_ENV: process.env.NODE_ENV,
    NEXT_PUBLIC_API_URL: getProcessedApiUrl(),
    NEXT_PUBLIC_STATIC_WEBSITE_ONLY:
      process.env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true",
    AMPLITUDE_API_KEY: process.env.AMPLITUDE_API_KEY,
    GITHUB_OAUTH_TOKEN: process.env.GITHUB_OAUTH_TOKEN,
  },
  /**
   * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially
   * useful for Docker builds.
   */
  skipValidation: !!process.env.SKIP_ENV_VALIDATION,
  /**
   * Makes it so that empty strings are treated as undefined. `SOME_VAR: z.string()` and
   * `SOME_VAR=''` will throw an error.
   */
  emptyStringAsUndefined: true,
});
