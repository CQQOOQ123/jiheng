#!/usr/bin/env node
/**
 * 客户端插件静态契约检查（不依赖浏览器）：
 * 注册 id/slot、策略项、主题 token、必要文案、无硬编码颜色。
 */
import { readFileSync } from 'node:fs';

const text = readFileSync(new URL('./client.js', import.meta.url), 'utf8');
let pass = 0;
let fail = 0;

function ok(name, condition, detail = '') {
  if (condition) {
    pass += 1;
    console.log(`ok   ${name.padEnd(46)} ${detail}`);
  } else {
    fail += 1;
    console.log(`FAIL ${name.padEnd(46)} ${detail}`);
  }
}

ok('module loader id', text.includes("__ModuleLoader__.load") && text.includes("'@local/jiheng'"));
ok('settings.section slot', text.includes("settings.section"));
ok('policy options', ['always', 'complex', 'auto', 'never', 'custom'].every((item) => text.includes(`'${item}'`)));
ok('section labels', ['状态', '使用策略', '限额', '公式与能力包'].every((label) => text.includes(label)));
ok('uses theme tokens', (text.match(/--dsw-/g) || []).length >= 5);
ok('no hardcoded hex colors', !/#[0-9a-fA-F]{3,8}\b/.test(text));
ok('no rgb()/hsl() colors', !/\b(rgb|hsl)a?\(/.test(text));
ok('fetch routes are same-origin', ['/calc/status', '/calc/policy', '/calc/limits', '/calc/packs'].every((p) => text.includes(`'${p}'`)));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
