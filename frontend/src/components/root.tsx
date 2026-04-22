import { ConfigProvider, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Suspense, useEffect, useMemo } from 'react';
import { Outlet } from 'react-router';
import { buildThemeConfig } from '@/config/theme';
import SakuraEffect from '@/components/sakura-effect';
import { useFeatureToggles } from '@/hooks/use-feature-toggles';
import { useThemePrimary } from '@/hooks/use-theme-primary';
import { disableLive2d, enableLive2d } from '@/live2d';

const fallback = (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
    <Spin size="large" />
  </div>
);

export default function Root(): React.JSX.Element {
  const { sakura, live2d } = useFeatureToggles();
  const primary = useThemePrimary();
  const themeConfig = useMemo(() => buildThemeConfig(primary), [primary]);

  useEffect(() => {
    if (live2d) {
      void enableLive2d();
    } else {
      disableLive2d();
    }
  }, [live2d]);

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <div className="app-with-sakura" style={{ position: 'relative', minHeight: '100vh' }}>
        {sakura && <SakuraEffect />}
        <div style={{ position: 'relative', zIndex: 1 }}>
          <Suspense fallback={fallback}>
            <Outlet />
          </Suspense>
        </div>
      </div>
    </ConfigProvider>
  );
}
