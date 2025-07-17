#!/usr/bin/env node

/**
 * 測試 API 連接和 URL 構建
 */

import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('🔍 測試 API 連接...\n');

// 載入環境變數
const envPath = join(__dirname, '../../.env');
const result = dotenv.config({ path: envPath });

if (result.parsed) {
    console.log('✅ 環境變數載入成功');
    console.log(`📋 NEXT_PUBLIC_API_URL: ${result.parsed.NEXT_PUBLIC_API_URL}`);
} else {
    console.log('⚠️  無法載入 .env 檔案');
    process.exit(1);
}

// 模擬 resolveServiceURL 函數
function resolveServiceURL(path) {
    let BASE_URL = result.parsed.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/";
    if (!BASE_URL.endsWith("/")) {
        BASE_URL += "/";
    }
    return new URL(path, BASE_URL).toString();
}

// 測試 URL 構建
console.log('\n🧪 測試 URL 構建:');
const configUrl = resolveServiceURL('config');
console.log(`🔗 config → ${configUrl}`);

// 測試連接（如果可能）
console.log('\n🌐 測試 API 連接:');

async function testAPI() {
    try {
        const response = await fetch(configUrl, {
            signal: AbortSignal.timeout(3000)
        });

        if (response.ok) {
            console.log(`✅ API 連接成功: ${response.status}`);
            const data = await response.json();
            console.log('📋 配置數據:', JSON.stringify(data, null, 2));
        } else {
            console.log(`⚠️  API 返回錯誤: ${response.status} ${response.statusText}`);
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('⏰ 連接超時');
        } else {
            console.log(`❌ 連接失敗: ${error.message}`);
        }
    }
}

testAPI().then(() => {
    console.log('\n🎉 測試完成！');
}); 