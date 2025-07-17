#!/usr/bin/env node

/**
 * 測試 JSON 解析改進
 */

import { parse } from 'best-effort-json-parser';

console.log('🧪 測試 JSON 解析改進...\n');

// 模擬 parseJSON 函數
function parseJSON(json, fallback) {
    if (!json) {
        return fallback;
    }
    try {
        const raw = json
            .trim()
            .replace(/^```json\s*/, "")
            .replace(/^```js\s*/, "")
            .replace(/^```ts\s*/, "")
            .replace(/^```plaintext\s*/, "")
            .replace(/^```\s*/, "")
            .replace(/\s*```$/, "");
        return parse(raw);
    } catch {
        return fallback;
    }
}

// 測試案例
const testCases = [
    {
        name: '正常的 JSON 陣列',
        input: '[{"url": "https://example.com", "title": "Example"}]',
        expected: 'array with 1 item'
    },
    {
        name: '不完整的 JSON（缺少結尾括號）',
        input: '[{"url": "https://example.com", "title": "Example"',
        expected: 'best effort parsed'
    },
    {
        name: '包含額外 tokens 的 JSON',
        input: 'Published: 2016-11-03\\ntitle: Development of a DepL..ion compared to the previous MTJ/CMOS full adder. [{"url": "https://example.com"}]',
        expected: 'extracted JSON portion'
    },
    {
        name: '空字串',
        input: '',
        expected: 'fallback value'
    },
    {
        name: '純文本（無 JSON）',
        input: 'This is just plain text with no JSON',
        expected: 'fallback value'
    },
    {
        name: 'Code block 包裝的 JSON',
        input: '```json\n[{"url": "https://example.com"}]\n```',
        expected: 'extracted from code block'
    }
];

testCases.forEach((testCase, index) => {
    console.log(`\n📋 測試案例 ${index + 1}: ${testCase.name}`);
    console.log(`📥 輸入: ${testCase.input.substring(0, 100)}${testCase.input.length > 100 ? '...' : ''}`);

    try {
        const result = parseJSON(testCase.input, null);

        if (result === null) {
            console.log(`📤 結果: null (fallback)`);
        } else if (Array.isArray(result)) {
            console.log(`📤 結果: Array with ${result.length} items`);
            if (result.length > 0) {
                console.log(`   第一項: ${JSON.stringify(result[0])}`);
            }
        } else if (typeof result === 'object') {
            console.log(`📤 結果: Object with keys: ${Object.keys(result).join(', ')}`);
        } else {
            console.log(`📤 結果: ${typeof result} - ${result}`);
        }

        console.log(`✅ 解析成功`);
    } catch (error) {
        console.log(`❌ 解析失敗: ${error.message}`);
    }
});

// 測試新的 URL 提取邏輯
console.log('\n🔗 測試 URL 提取邏輯...');

function extractUrls(result) {
    const links = new Set();

    if (!result) return links;

    let searchResults = [];

    if (Array.isArray(result)) {
        searchResults = result;
    } else if (result && typeof result === 'object') {
        if (Array.isArray(result.results)) {
            searchResults = result.results;
        } else if (result.url) {
            searchResults = [result];
        }
    }

    searchResults.forEach((r) => {
        if (r && typeof r === 'object') {
            if (typeof r.url === 'string' && r.url.trim()) {
                links.add(r.url);
            }
            if (typeof r.image_url === 'string' && r.image_url.trim()) {
                links.add(r.image_url);
            }
        }
    });

    return links;
}

const urlTestCases = [
    {
        name: '直接陣列格式',
        data: [
            { url: 'https://example.com', title: 'Example' },
            { image_url: 'https://example.com/image.jpg', type: 'image' }
        ]
    },
    {
        name: '包含 results 的物件',
        data: {
            results: [
                { url: 'https://test.com', title: 'Test' }
            ]
        }
    },
    {
        name: '單一物件',
        data: { url: 'https://single.com', title: 'Single' }
    }
];

urlTestCases.forEach((testCase, index) => {
    console.log(`\n📋 URL 測試 ${index + 1}: ${testCase.name}`);
    const urls = extractUrls(testCase.data);
    console.log(`🔗 提取到 ${urls.size} 個 URL:`);
    urls.forEach(url => console.log(`   - ${url}`));
});

console.log('\n🎉 測試完成！'); 