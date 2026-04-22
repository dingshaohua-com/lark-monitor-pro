import { CalendarOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useTableScrolly } from '@/components/use-table-scrolly';
import { Button, Card, DatePicker, Input, Space, Table, Tooltip, Typography, theme } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useCallback, useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { customAxiosInstance } from '@/api/api.base';

const { RangePicker } = DatePicker;

type DutyRecord = { 日期: string; 值班人: string };

type DutyPayload = {
  total: number;
  field_keys: string[];
  records: DutyRecord[];
};

export default function Duty() {
  const { token } = theme.useToken();
  const [loading, setLoading] = useState(false);
  const [payload, setPayload] = useState<DutyPayload | null>(null);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [nameFilter, setNameFilter] = useState('');
  const { ref: tableWrapRef, scrollY } = useTableScrolly();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await customAxiosInstance<DutyPayload>({ url: '/api/bitable/duty-records', method: 'GET' });
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
    let list = payload.records;
    if (dateRange) {
      const start = dateRange[0].format('YYYY-MM-DD');
      const end = dateRange[1].format('YYYY-MM-DD');
      list = list.filter((r) => r['日期'] >= start && r['日期'] <= end);
    }
    if (nameFilter.trim()) {
      const kw = nameFilter.trim().toLowerCase();
      list = list.filter((r) => (r['值班人'] ?? '').toLowerCase().includes(kw));
    }
    return list;
  }, [payload, dateRange, nameFilter]);

  const columns: ColumnsType<DutyRecord> = [
    {
      title: '日期',
      dataIndex: '日期',
      key: '日期',
      width: 140,
      sorter: (a, b) => (a['日期'] > b['日期'] ? 1 : -1),
      defaultSortOrder: 'descend',
    },
    {
      title: '值班人',
      dataIndex: '值班人',
      key: '值班人',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span>{text || '-'}</span>
        </Tooltip>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflow: 'hidden' }}>
      <Card size="small" style={{ borderRadius: token.borderRadiusLG, flexShrink: 0 }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <CalendarOutlined style={{ fontSize: 20, color: token.colorPrimary }} />
            <Typography.Title level={5} style={{ margin: 0 }}>
              值班表
            </Typography.Title>
          </Space>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>
            刷新
          </Button>
        </Space>
        <Space style={{ marginTop: 12 }} wrap>
          <RangePicker
            size="small"
            value={dateRange}
            onChange={(v) => setDateRange(v as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            allowClear
            placeholder={['开始日期', '结束日期']}
          />
          <Input
            size="small"
            placeholder="搜索值班人"
            prefix={<SearchOutlined style={{ color: token.colorTextQuaternary }} />}
            allowClear
            value={nameFilter}
            onChange={(e) => setNameFilter(e.target.value)}
            style={{ width: 160 }}
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
          <Table<DutyRecord>
            rowKey="日期"
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
