#!/usr/bin/env node

/**
 * 測試環境變數轉換功能
 */

// 模擬瀏覽器環境
global.window = {
    location: {
        hostname: '192.168.31.180'
    }
};

// 模擬 process.env
process.env.NEXT_PUBLIC_API_URL = 'http://0.0.0.0:8001/api';

console.log('🧪 測試前端環境變數轉換功能...\n');

/**
 * 在瀏覽器環境中轉換 URL 中的 0.0.0.0 為實際 IP 地址
 */
function convertZeroIPToActualInBrowser(url) {
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
}

// 測試不同的場景
const testCases = [
    {
        name: '正常轉換：0.0.0.0 → 實際 IP',
        url: 'http://0.0.0.0:8001/api',
        hostname: '192.168.31.180',
        expected: 'http://192.168.31.180:8001/api'
    },
    {
        name: 'localhost 場景：0.0.0.0 → localhost',
        url: 'http://0.0.0.0:8001/api',
        hostname: 'localhost',
        expected: 'http://localhost:8001/api'
    },
    {
        name: '不需要轉換：已經是正確的 URL',
        url: 'http://192.168.31.180:8001/api',
        hostname: '192.168.31.180',
        expected: 'http://192.168.31.180:8001/api'
    }
];

testCases.forEach((testCase, index) => {
    console.log(`\n📋 測試案例 ${index + 1}: ${testCase.name}`);

    // 設定測試環境
    global.window.location.hostname = testCase.hostname;

    // 執行轉換
    const result = convertZeroIPToActualInBrowser(testCase.url);

    // 驗證結果
    if (result === testCase.expected) {
        console.log(`✅ 通過: ${result}`);
    } else {
        console.log(`❌ 失敗: 期望 ${testCase.expected}，實際 ${result}`);
    }
});

// 測試服務器端環境（沒有 window 物件）
console.log(`\n📋 測試案例: 服務器端環境`);
delete global.window;
const serverResult = convertZeroIPToActualInBrowser('http://0.0.0.0:8001/api');
if (serverResult === 'http://0.0.0.0:8001/api') {
    console.log(`✅ 通過: 服務器端不進行轉換 ${serverResult}`);
} else {
    console.log(`❌ 失敗: 服務器端應該不進行轉換，實際 ${serverResult}`);
}

console.log('\n🎉 測試完成！'); 