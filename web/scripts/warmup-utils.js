#!/usr/bin/env node

/**
 * 預熱工具模組
 * 包含開發腳本中使用的共用函數
 */

import { networkInterfaces } from 'os';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const require = createRequire(import.meta.url);

/**
 * 取得本機 IP 地址
 * @returns {string|null} 本機 IP 地址或 null
 */
export function getLocalIP() {
    const nets = networkInterfaces();
    for (const name of Object.keys(nets)) {
        const interfaces = nets[name];
        if (interfaces) {
            for (const net of interfaces) {
                // 跳過內部地址和非 IPv4 地址
                if (net.family === 'IPv4' && !net.internal) {
                    return net.address;
                }
            }
        }
    }
    return null;
}

/**
 * 轉換 URL 中的 0.0.0.0 為實際 IP 地址
 * @param {string} url - 原始 URL
 * @returns {string} 轉換後的 URL
 */
export function convertZeroIPToActual(url) {
    if (!url || !url.includes('0.0.0.0')) {
        return url;
    }

    const localIP = getLocalIP();
    if (localIP) {
        const convertedUrl = url.replace('0.0.0.0', localIP);
        console.log(`🔄 自動轉換 0.0.0.0 為實際 IP: ${url} → ${convertedUrl}`);
        return convertedUrl;
    } else {
        const convertedUrl = url.replace('0.0.0.0', 'localhost');
        console.log(`⚠️  無法檢測本機 IP，使用 localhost: ${url} → ${convertedUrl}`);
        return convertedUrl;
    }
}

/**
 * 載入環境配置，自動轉換 0.0.0.0 為實際 IP
 * @returns {Record<string, string>} 環境變數對象
 */
export function loadEnvConfig() {
    /** @type {Record<string, string>} */
    let env = {};
    try {
        const dotenv = require('dotenv');
        const result = dotenv.config({ path: join(__dirname, '../../.env') });
        if (result.parsed && Object.keys(result.parsed).length > 0) {
            console.log('✅ 成功載入 .env 檔案');
            env = result.parsed;

            // 自動轉換關鍵的 URL 配置
            if (env.NEXT_PUBLIC_API_URL) {
                env.NEXT_PUBLIC_API_URL = convertZeroIPToActual(env.NEXT_PUBLIC_API_URL);
            }
            if (env.DEER_FLOW_URL) {
                env.DEER_FLOW_URL = convertZeroIPToActual(env.DEER_FLOW_URL);
            }
        } else {
            console.log('⚠️  無法載入 .env 檔案，使用預設配置');
        }
    } catch (error) {
        console.log('⚠️  dotenv 模組載入失敗，使用預設配置');
        console.log('   錯誤:', error instanceof Error ? error.message : String(error));
    }
    return env;
}

/**
 * 從環境變數中獲取應用配置
 * @param {Record<string, string>} env - 環境變數對象
 * @returns {{host: string, port: number, path: string}} 應用配置
 */
export function getAppConfigFromEnv(env) {
    // Extract host, port and path from DEER_FLOW_URL environment variable.
    let deerFlowUrl = env.DEER_FLOW_URL || process.env.DEER_FLOW_URL;

    // 自動轉換 0.0.0.0 為實際 IP（如果還沒轉換）
    if (deerFlowUrl) {
        deerFlowUrl = convertZeroIPToActual(deerFlowUrl);
    }

    if (deerFlowUrl) {
        try {
            const url = new URL(deerFlowUrl);
            let host = url.hostname || "localhost";
            const port = parseInt(url.port) || 3000;
            const path = url.pathname || "/chat";

            return { host, port, path };
        } catch (error) {
            console.warn(`無法解析 DEER_FLOW_URL: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    return { host: "localhost", port: 3000, path: "/chat" };
}

/**
 * 從環境變數中獲取應用配置（用於 warm-up 腳本）
 * @returns {{host: string, port: number, path: string}} 應用配置
 */
export function getAppConfigFromProcessEnv() {
    // 優先使用從父進程傳遞的環境變數
    const deerFlowHost = process.env.DEER_FLOW_HOST;
    const deerFlowPort = process.env.DEER_FLOW_PORT;
    const deerFlowPath = process.env.DEER_FLOW_PATH;
    let deerFlowUrl = process.env.DEER_FLOW_URL;

    if (deerFlowHost && deerFlowPort) {
        let host = deerFlowHost;

        // 如果配置的是 0.0.0.0，替換為實際 IP
        if (host === '0.0.0.0') {
            const localIP = getLocalIP();
            if (localIP) {
                host = localIP;
                console.log(`🔄 檢測到 0.0.0.0 配置，自動替換為實際 IP: ${localIP}`);
            } else {
                host = 'localhost';
                console.log(`⚠️  無法檢測到本機 IP，使用 localhost`);
            }
        }

        return {
            host: host,
            port: parseInt(deerFlowPort),
            path: deerFlowPath || '/chat'
        };
    }

    // 如果沒有傳遞的變數，嘗試解析 DEER_FLOW_URL
    if (deerFlowUrl) {
        // 自動轉換 0.0.0.0 為實際 IP
        deerFlowUrl = convertZeroIPToActual(deerFlowUrl);

        try {
            const url = new URL(deerFlowUrl);
            let host = url.hostname || "localhost";
            const port = parseInt(url.port) || 3000;
            const path = url.pathname || "/chat";

            return { host, port, path };
        } catch (error) {
            console.warn(`無法解析 DEER_FLOW_URL: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    return { host: 'localhost', port: 3000, path: '/chat' };
}

/**
 * 獲取處理過的 API URL（自動轉換 0.0.0.0）
 * @returns {string} 處理後的 API URL
 */
export function getProcessedApiUrl() {
    // 首先嘗試從環境變數獲取
    let apiUrl = process.env.NEXT_PUBLIC_API_URL;

    if (!apiUrl) {
        // 如果沒有設置，使用預設值
        apiUrl = "http://localhost:8000/api";
    }

    // 自動轉換 0.0.0.0
    return convertZeroIPToActual(apiUrl);
} 