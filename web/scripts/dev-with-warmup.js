#!/usr/bin/env node

/**
 * 前端開發服務器啟動腳本 - 根據環境變數配置啟動 Next.js 開發服務器
 * 整合預熱功能，避免首次訪問時的編譯等待時間
 * 
 * 功能：
 * 1. 根據環境變數配置啟動 Next.js 開發服務器
 * 2. 自動檢測服務器就緒狀態
 * 3. 執行路由預熱功能
 * 4. 智能處理 IP 地址配置
 */

import { spawn } from 'child_process';
import http from 'http';
import { loadEnvConfig, getAppConfigFromEnv, getLocalIP } from './warmup-utils.js';

// 預熱相關常數
const WARMUP_DELAY = 3000; // 等待 3 秒讓開發服務器完全啟動
const MAX_RETRIES = 10;
const RETRY_INTERVAL = 1000;

/**
 * 預熱路由
 * @param {string} url - 要預熱的 URL
 * @param {number} retries - 重試次數
 * @returns {Promise<void>}
 */
function warmUpRoute(url, retries = 0) {
    return new Promise((resolve, reject) => {
        const req = http.get(url, (res) => {
            console.log(`✅ 預熱成功: ${url} (狀態碼: ${res.statusCode})`);
            // 消費響應數據以避免記憶體洩漏
            res.on('data', () => { });
            res.on('end', () => resolve(undefined));
        });

        req.on('error', (err) => {
            if (retries < MAX_RETRIES) {
                console.log(`⏳ 重試預熱 ${url} (第 ${retries + 1} 次)...`);
                setTimeout(() => {
                    warmUpRoute(url, retries + 1).then(resolve).catch(reject);
                }, RETRY_INTERVAL);
            } else {
                console.error(`❌ 預熱失敗: ${url}`, err.message);
                reject(err);
            }
        });

        req.setTimeout(10000, () => {
            req.destroy();
            if (retries < MAX_RETRIES) {
                console.log(`⏳ 超時重試預熱 ${url} (第 ${retries + 1} 次)...`);
                setTimeout(() => {
                    warmUpRoute(url, retries + 1).then(resolve).catch(reject);
                }, RETRY_INTERVAL);
            } else {
                reject(new Error('預熱超時'));
            }
        });
    });
}

/**
 * 執行預熱功能
 * @param {Object} appConfig - 應用配置
 */
async function executeWarmup(appConfig) {
    console.log('🚀 開始預熱 Next.js 路由...');
    console.log(`📋 應用配置: ${appConfig.host}:${appConfig.port}${appConfig.path}`);

    // 等待開發服務器啟動
    await new Promise(resolve => setTimeout(resolve, WARMUP_DELAY));

    // 取得本機 IP
    const localIP = getLocalIP();
    console.log(`🔍 檢測到本機 IP: ${localIP || '未找到'}`);

    // 根據環境配置構建主機列表
    const hosts = [
        `${appConfig.host}:${appConfig.port}`,
    ];

    // 如果配置的主機不是 localhost，也加入 localhost 選項
    if (appConfig.host !== 'localhost') {
        hosts.push(`localhost:${appConfig.port}`);
        hosts.push(`127.0.0.1:${appConfig.port}`);
    }

    // 如果找到本機 IP 且與配置的主機不同，加入主機列表
    if (localIP && localIP !== appConfig.host) {
        hosts.push(`${localIP}:${appConfig.port}`);
    }

    // 嘗試找到可用的主機
    let activeHost = null;
    for (const host of hosts) {
        console.log(`🔍 檢測服務器: ${host}`);
        try {
            await new Promise((resolve, reject) => {
                const req = http.get(`http://${host}`, (res) => {
                    console.log(`✅ 服務器響應: ${host} (狀態碼: ${res.statusCode})`);
                    activeHost = host;
                    res.on('data', () => { }); // 消費響應數據
                    res.on('end', () => resolve(undefined));
                });
                req.on('error', (err) => {
                    console.log(`❌ 連接失敗: ${host} - ${err.message}`);
                    reject(err);
                });
                req.setTimeout(3000, () => {
                    console.log(`⏰ 連接超時: ${host}`);
                    req.destroy();
                    reject(new Error('timeout'));
                });
            });
            break;
        } catch (err) {
            // 繼續嘗試下一個主機
            console.log(`⚠️  主機 ${host} 不可用，嘗試下一個...`);
        }
    }

    if (!activeHost) {
        console.log('⚠️  無法找到活躍的開發服務器，跳過預熱');
        return false;
    }

    console.log(`🎯 找到活躍的開發服務器: ${activeHost}`);

    const routes = [
        `http://${activeHost}/chat`,
        `http://${activeHost}/`, // 也預熱主頁
    ];

    try {
        for (const route of routes) {
            await warmUpRoute(route);
        }
        console.log('🎉 所有路由預熱完成！');
        return true;
    } catch (error) {
        console.error('❌ 預熱過程中發生錯誤:', error instanceof Error ? error.message : String(error));
        return false;
    }
}

console.log('🚀 啟動 DeerFlow Web UI 開發服務器（根據環境配置 + 整合預熱功能）...\n');

// 載入環境配置
const env = loadEnvConfig();

// 獲取應用配置
const appConfig = getAppConfigFromEnv(env);
console.log(`📋 應用配置: ${appConfig.host}:${appConfig.port}${appConfig.path}`);

// 構建 Next.js 啟動命令
const nextArgs = ['dev', '--turbo'];

// 使用 0.0.0.0 作為 hostname，讓 Next.js 自動檢測網路介面
// 這樣 Local 會顯示 localhost，Network 會顯示實際 IP
nextArgs.push('--hostname', '0.0.0.0');

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
        setTimeout(async () => {
            const success = await executeWarmup(appConfig);
            warmupCompleted = true;

            if (success) {
                console.log(`\n✅ 預熱完成！您現在可以訪問 http://${appConfig.host}:${appConfig.port}${appConfig.path}\n`);
            } else {
                console.log('\n⚠️  預熱過程中出現問題，但開發服務器仍在運行\n');
            }
        }, 2000);
    }
});

nextProcess.stderr.on('data', (data) => {
    console.error(data.toString());
});

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