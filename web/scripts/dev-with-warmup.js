#!/usr/bin/env node

/**
 * 前端開發服務器啟動腳本 - 根據環境變數配置啟動 Next.js 開發服務器
 * 這個腳本會從環境變數中讀取配置，並啟動相應的前端開發服務器
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const require = createRequire(import.meta.url);

// 嘗試載入 dotenv 來讀取環境變數
let env = {};
try {
    const dotenv = require('dotenv');
    const result = dotenv.config({ path: join(__dirname, '../../.env') });
    if (result.parsed && Object.keys(result.parsed).length > 0) {
        env = result.parsed;
        console.log('✅ 成功載入 .env 檔案');
    } else {
        console.log('⚠️  無法載入 .env 檔案，使用預設配置');
    }
} catch (error) {
    console.log('⚠️  dotenv 模組載入失敗，使用預設配置');
    console.log('   錯誤:', error instanceof Error ? error.message : String(error));
}

function get_app_config_from_env() {
    // Extract host, port and path from DEER_FLOW_URL environment variable.
    const deerFlowUrl = env.DEER_FLOW_URL || process.env.DEER_FLOW_URL;
    if (deerFlowUrl) {
        try {
            const url = new URL(deerFlowUrl);
            const host = url.hostname || "localhost";
            const port = url.port || 3000;
            const path = url.pathname || "/chat";
            return { host, port, path };
        } catch (error) {
            console.warn(`無法解析 DEER_FLOW_URL: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    return { host: "localhost", port: 3000, path: "/chat" };
}

console.log('🚀 啟動 DeerFlow Web UI 開發服務器（根據環境配置 + 預熱功能）...\n');

// 獲取應用配置
const appConfig = get_app_config_from_env();
console.log(`📋 應用配置: ${appConfig.host}:${appConfig.port}${appConfig.path}`);

// 構建 Next.js 啟動命令
const nextArgs = ['dev', '--turbo'];
if (appConfig.host !== 'localhost') {
    nextArgs.push('--hostname', appConfig.host);
}
if (appConfig.port !== 3000) {
    nextArgs.push('--port', appConfig.port.toString());
}

console.log(`🔧 Next.js 啟動參數: ${nextArgs.join(' ')}`);

// 啟動 Next.js 開發服務器
const nextProcess = spawn('dotenv', ['-e', '../.env', '--', 'next', ...nextArgs], {
    stdio: 'pipe',
    shell: true,
    cwd: process.cwd()
});

let serverReady = false;
let warmupCompleted = false;

// 監聽 Next.js 服務器輸出
nextProcess.stdout.on('data', (data) => {
    const output = data.toString();
    console.log(output);

    // 檢測服務器是否準備就緒
    if (output.includes('Ready in') && !serverReady) {
        serverReady = true;
        console.log('\n🎯 開發服務器已準備就緒，開始預熱...\n');

        // 延遲 2 秒後開始預熱，確保服務器完全啟動
        setTimeout(() => {
            startWarmup();
        }, 2000);
    }
});

nextProcess.stderr.on('data', (data) => {
    console.error(data.toString());
});

// 啟動預熱功能
function startWarmup() {
    const warmupProcess = spawn('node', ['scripts/warm-up.js'], {
        stdio: 'inherit',
        shell: true,
        cwd: process.cwd()
    });

    warmupProcess.on('close', (code) => {
        warmupCompleted = true;
        if (code === 0) {
            console.log(`\n✅ 預熱完成！您現在可以訪問 http://${appConfig.host}:${appConfig.port}${appConfig.path}\n`);
        } else {
            console.log('\n⚠️  預熱過程中出現問題，但開發服務器仍在運行\n');
        }
    });
}

// 處理進程終止
process.on('SIGINT', () => {
    console.log('\n🛑 正在關閉開發服務器...');
    nextProcess.kill('SIGINT');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n🛑 正在關閉開發服務器...');
    nextProcess.kill('SIGTERM');
    process.exit(0);
});

nextProcess.on('close', (code) => {
    console.log(`\n開發服務器已關閉 (代碼: ${code})`);
    process.exit(code);
}); 