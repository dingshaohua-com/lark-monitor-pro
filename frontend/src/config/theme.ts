/** 主题色配置，支持运行时切换，首次加载取环境变量或默认粉色 */
const DEFAULT_PRIMARY = '#eb2f96';

export const ENV_PRIMARY = (import.meta.env.PUBLIC_THEME_PRIMARY as string | undefined) ?? DEFAULT_PRIMARY;

export interface ThemePreset {
  key: string;
  label: string;
  color: string;
}

export const THEME_PRESETS: ThemePreset[] = [
  { key: 'pink', label: '樱花粉', color: '#eb2f96' },
  { key: 'red', label: '朱砂红', color: '#f5222d' },
  { key: 'orange', label: '活力橙', color: '#fa8c16' },
  { key: 'gold', label: '暖阳金', color: '#faad14' },
  { key: 'green', label: '自然绿', color: '#52c41a' },
  { key: 'cyan', label: '青碧蓝', color: '#13c2c2' },
  { key: 'blue', label: '科技蓝', color: '#1677ff' },
  { key: 'purple', label: '优雅紫', color: '#722ed1' },
];

export function buildThemeConfig(primary: string) {
  return {
    token: {
      colorPrimary: primary,
    },
  } as const;
}
