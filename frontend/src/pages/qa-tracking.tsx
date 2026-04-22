import { FileSearchOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useTableScrolly } from '@/components/use-table-scrolly';
import { Button, Card, Input, Space, Table, Tooltip, Typography, theme } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { customAxiosInstance } from '@/api/api.base';

type QaPayload = {
  total: number;
  field_keys: string[];
  records: Record<string, string>[];
};

export default function QaTracking() {
  const { token } = theme.useToken();
  const [loading, setLoading] = useState(false);
  const [payload, setPayload] = useState<QaPayload | null>(null);
  const [keyword, setKeyword] = useState('');
  const { ref: tableWrapRef, scrollY } = useTableScrolly();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await customAxiosInstance<QaPayload>({ url: '/api/bitable/qa-tracking-records', method: 'GET' });
      setPayload(d);
    } catch {
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!payload?.records) return [];
    if (!keyword.trim()) return payload.records;
    const kw = keyword.trim().toLowerCase();
    return payload.records.filter((r) =>
      Object.values(r).some((v) => v != null && String(v).toLowerCase().includes(kw)),
    );
  }, [payload, keyword]);

  const columns: ColumnsType<Record<string, string>> = useMemo(() => {
    if (!payload?.field_keys?.length) return [];
    return payload.field_keys.map((key) => ({
      title: key === 'feedback_id' ? '反馈ID' : key,
      dataIndex: key,
      key,
      ellipsis: true,
      width: key === 'feedback_id' ? 180 : key.includes('描述') ? 320 : 200,
      render: (value?: string) => {
        const text = value != null ? String(value) : '-';
        return (
          <Tooltip title={text} placement="topLeft">
            <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{text}</div>
          </Tooltip>
        );
      },
    }));
  }, [payload]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflow: 'hidden' }}>
      <Card size="small" style={{ borderRadius: token.borderRadiusLG, flexShrink: 0 }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <FileSearchOutlined style={{ fontSize: 20, color: token.colorPrimary }} />
            <Typography.Title level={5} style={{ margin: 0 }}>
              问题原因表
            </Typography.Title>
          </Space>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>
            刷新
          </Button>
        </Space>
        <Space style={{ marginTop: 12 }} wrap>
          <Input
            size="small"
            placeholder="搜索关键字（全字段模糊匹配）"
            prefix={<SearchOutlined style={{ color: token.colorTextQuaternary }} />}
            allowClear
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ width: 260 }}
          />
        </Space>
      </Card>

      <Card
        size="small"
        style={{
          borderRadius: token.borderRadiusLG,
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        styles={{ body: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', paddingTop: 0 } }}
        title={`共 ${filtered.length} 条`}
      >
        <div ref={tableWrapRef} style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          <Table<Record<string, string>>
            rowKey="feedback_id"
            loading={loading}
            columns={columns}
            dataSource={filtered}
            tableLayout="fixed"
            pagination={{ pageSize: 20, showSizeChanger: true, size: 'small' }}
            scroll={{ x: 'max-content', y: `calc(${scrollY}px - 96px)` }}
          />
        </div>
      </Card>
    </div>
  );
}
