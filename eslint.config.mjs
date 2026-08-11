import pluginVue from 'eslint-plugin-vue'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['apps/**/*.{ts,vue}', 'packages/**/*.{ts,vue}'],
  },
  {
    name: 'app/files-to-ignore',
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/unpackage/**',
      '**/src-tauri/**',
      '**/*.d.ts',
      'backend/**',
    ],
  },
  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,
  skipFormatting,
  {
    rules: {
      // uni-app 单文件页面依赖多词组件名规则之外的命名（pages/index/index 等）
      'vue/multi-word-component-names': 'off',
      // 错误日志是有意保留的运维通道；调试 log 仍需清理
      'no-console': ['warn', { allow: ['error', 'warn'] }],
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
    },
  },
  {
    // 测试里用 as any 构造异常输入是刻意的契约探测
    files: ['**/test/**', '**/*.test.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  {
    // CLI 启动脚本：console 即用户界面
    files: ['scripts/**/*.mjs'],
    rules: {
      'no-console': 'off',
    },
  },
)
