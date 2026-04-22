import { BgColorsOutlined, CheckOutlined, HeartOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined, SmileOutlined, UserOutlined } from '@ant-design/icons';
import { Avatar, Breadcrumb, Dropdown, Layout, Menu, type MenuProps, Switch, theme, Tooltip } from 'antd';
import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router';
import { toBreadcrumbMap, toMenuItems, toRoutableSet } from '@/router/helper';
import { routes } from '@/router/routes';
import logoImg from '@/assets/imgs/logo.png';
import { setFeatureToggle, useFeatureToggles } from '@/hooks/use-feature-toggles';
import { setThemePrimary, useThemePrimary } from '@/hooks/use-theme-primary';
import { THEME_PRESETS } from '@/config/theme';

const { Header, Sider, Content } = Layout;

const menuItems = toMenuItems(routes);
const breadcrumbNameMap = toBreadcrumbMap(routes);
const routablePaths = toRoutableSet(routes);

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();

  const onMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key);
  };

  const pathSnippets = location.pathname.split('/').filter(Boolean);
  const breadcrumbItems =
    pathSnippets.length === 0
      ? [{ title: '首页', key: '/' }]
      : pathSnippets.map((_, index) => {
          const url = `/${pathSnippets.slice(0, index + 1).join('/')}`;
          return {
            title: breadcrumbNameMap[url] ?? url,
            ...(routablePaths.has(url) ? { href: `#${url}` } : {}),
            key: url,
          };
        });

  const toggles = useFeatureToggles();
  const primary = useThemePrimary();

  const toggleLabel = (text: string, checked: boolean) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24, minWidth: 140 }}>
      <span>{text}</span>
      <Switch size="small" checked={checked} />
    </div>
  );

  const themeLabel = (
    <div
      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, minWidth: 180 }}
      onClick={(e) => e.stopPropagation()}
    >
      <span>主题色</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {THEME_PRESETS.map((preset) => {
          const active = preset.color.toLowerCase() === primary.toLowerCase();
          return (
            <Tooltip key={preset.key} title={preset.label} mouseEnterDelay={0.2}>
              <span
                role="button"
                aria-label={preset.label}
                onClick={(e) => {
                  e.stopPropagation();
                  setThemePrimary(preset.color);
                }}
                style={{
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  background: preset.color,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: active ? `0 0 0 2px ${token.colorBgContainer}, 0 0 0 3px ${preset.color}` : 'none',
                  transition: 'transform 0.15s',
                }}
              >
                {active && <CheckOutlined style={{ color: '#fff', fontSize: 10 }} />}
              </span>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );

  const userMenuItems: MenuProps['items'] = [
    { key: 'theme', icon: <BgColorsOutlined />, label: themeLabel },
    { type: 'divider' },
    { key: 'sakura', icon: <HeartOutlined />, label: toggleLabel('樱花飘落', toggles.sakura) },
    { key: 'live2d', icon: <SmileOutlined />, label: toggleLabel('Live2D 看板娘', toggles.live2d) },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const onUserMenuClick: MenuProps['onClick'] = ({ key, domEvent }) => {
    if (key === 'sakura' || key === 'live2d') {
      domEvent?.preventDefault?.();
      setFeatureToggle(key, !toggles[key]);
      return;
    }
    if (key === 'theme') {
      domEvent?.preventDefault?.();
      return;
    }
    if (key === 'logout') {
      setUserMenuOpen(false);
      navigate('/login');
    }
  };

  const selectedKeys = [location.pathname === '/' ? '/' : location.pathname];
  const openKeys = menuItems
    ?.filter((item): item is Extract<typeof item, { children: unknown }> => !!(item && 'children' in item))
    .filter((item) => (item.children as MenuProps['items'])?.some((child) => child && 'key' in child && selectedKeys.includes(child.key as string)))
    .map((item) => item.key as string) ?? [];

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      <Sider
        theme="light"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={220}
        style={{ borderRight: `1px solid ${token.colorBorderSecondary}` }}
      >
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 20px',
            gap: 8,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          {/* <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: token.colorPrimary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 700,
              fontSize: 12,
              flexShrink: 0,
            }}
          >
            元芳
          </div> */}
          <img src={logoImg} alt="logo" style={{ width: 28, height: 28 }} className='rounded-md' />
          {!collapsed && <span style={{ fontWeight: 600, fontSize: 15, whiteSpace: 'nowrap' }}>工单平台</span>}
        </div>

        <Menu
          mode="inline"
          selectedKeys={selectedKeys}
          defaultOpenKeys={openKeys}
          items={menuItems}
          onClick={onMenuClick}
          style={{ border: 'none', padding: '8px 0' }}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            height: 56,
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span onClick={() => setCollapsed(!collapsed)} style={{ cursor: 'pointer', fontSize: 16, display: 'flex' }}>
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </span>
            <Breadcrumb items={breadcrumbItems} />
          </div>

          <Dropdown
            menu={{ items: userMenuItems, onClick: onUserMenuClick }}
            placement="bottomRight"
            open={userMenuOpen}
            onOpenChange={setUserMenuOpen}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} />
              <span style={{ fontSize: 14 }}>Admin</span>
            </div>
          </Dropdown>
        </Header>

        <Content style={{ padding: 16, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
