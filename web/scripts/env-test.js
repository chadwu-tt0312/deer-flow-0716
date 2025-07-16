#!/usr/bin/env node

/**
 * 環境變數測試腳本 - 診斷 .env 檔案載入問題
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { createRequire } from 'module';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const require = createRequire(import.meta.url);

console.log('🔍 環境變數載入測試...\n');

// 測試 .env 檔案路徑
const envPath = join(__dirname, '../../.env');

console.log('📁 檢查 .env 檔案路徑:');
const exists = existsSync(envPath);
console.log(`  ${envPath} - ${exists ? '✅ 存在' : '❌ 不存在'}`);

console.log('\n📋 嘗試載入 .env 檔案:');

// 嘗試載入 dotenv
try {
    const dotenv = require('dotenv');
    console.log('✅ dotenv 模組載入成功');

    if (exists) {
        try {
            const result = dotenv.config({ path: envPath });
            if (result.parsed && Object.keys(result.parsed).length > 0) {
                console.log(`✅ 載入成功，包含 ${Object.keys(result.parsed).length} 個變數`);
                console.log('   變數列表:', Object.keys(result.parsed));
            } else {
                console.log(`⚠️  載入失敗: 檔案為空或格式錯誤`);
            }
        } catch (error) {
            console.log(`❌ 載入錯誤:`, error instanceof Error ? error.message : String(error));
        }
    } else {
        console.log('❌ .env 檔案不存在');
    }

} catch (error) {
    console.log('❌ dotenv 模組載入失敗:', error instanceof Error ? error.message : String(error));
}

console.log('\n🌐 當前環境變數:');
console.log('  NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL || '未設定');
console.log('  DEER_FLOW_URL:', process.env.DEER_FLOW_URL || '未設定');

console.log('\n📂 當前工作目錄:', process.cwd());
console.log('📂 腳本目錄:', __dirname); 