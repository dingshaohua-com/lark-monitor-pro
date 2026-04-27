import { BarChartOutlined, CheckOutlined, DownloadOutlined } from '@ant-design/icons';
import { Button, Card, Checkbox, DatePicker, Space, theme } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { customAxiosInstance } from '@/api/api.base';
import { listMessagesApiMessageGet } from '@/api/endpoints/work-order';
import type { PageMessageWithReplies } from '@/api/model';

const { RangePicker } = DatePicker;

interface PeriodStats {
  total: number;
  bot_processed: number;
  correct_count: number;
  incorrect_count: number;
  problem_category_counts: Record<string, number>;
}

interface StatsResponse {
  current: PeriodStats;
  previous: PeriodStats;
  period_days: number;
}

function triggerDownload(data: unknown, filename: string) {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Export() {
  const { token } = theme.useToken();
  const today = dayjs();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>([today.subtract(6, 'day'), today]);
  const [withStats, setWithStats] = useState(true);
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<{ count: number; replyCount: number; filename: string } | null>(null);

  const canExport = !!(dateRange?.[0] && dateRange?.[1]);

  const handleExport = async () => {
    if (!canExport) return;
    setLoading(true);
    setLastResult(null);
    try {
      const startDate = dateRange[0].format('YYYY-MM-DD');
      const endDate = dateRange[1].format('YYYY-MM-DD');

      // 不传 pageSize → 后端不分页，一次返回全部
      const res = (await listMessagesApiMessageGet({
        withReply: true,
        startDate,
        endDate,
      })) as PageMessageWithReplies;
      const items = res?.items ?? [];
      const replyCount = items.reduce((acc, m) => acc + (m.replies?.length ?? 0), 0);

      let exportData: unknown = items;
      if (withStats) {
        const stats = await customAxiosInstance<{ data: StatsResponse }>({
          url: '/api/message/stats',
          method: 'GET',
          params: { start_date: startDate, end_date: endDate },
        });
        exportData = { statistics: stats, items };
      }

      const filename = `工单导出_${startDate}_${endDate}.json`;
      triggerDownload(exportData, filename);
      setLastResult({ count: items.length, replyCount, filename });
    } catch {
      /* handled by interceptor */
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', overflow: 'auto' }}>
      <Card style={{ borderRadius: token.borderRadiusLG, width: '100%', maxWidth: 480 }}>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>导出工单数据</div>

        <Space direction="vertical" size={20} style={{ width: '100%' }}>
          <div>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>
              选择日期范围 <span style={{ color: token.colorError }}>*</span>
            </div>
            <RangePicker
              value={dateRange}
              onChange={(v) => setDateRange(v as [dayjs.Dayjs, dayjs.Dayjs] | null)}
              style={{ width: '100%' }}
              allowClear={false}
            />
          </div>

          <Checkbox
            checked={withStats}
            onChange={(e) => setWithStats(e.target.checked)}
          >
            <Space size={4}>
              <BarChartOutlined />
              <span>导出统计信息</span>
            </Space>
          </Checkbox>

          <Button
            type="primary"
            size="large"
            icon={<DownloadOutlined />}
            loading={loading}
            disabled={!canExport}
            onClick={handleExport}
            style={{ width: '100%' }}
          >
            {loading ? '正在导出...' : '导出 JSON'}
          </Button>

          {lastResult && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 12px',
                borderRadius: token.borderRadiusLG,
                background: token.colorSuccessBg,
                color: token.colorSuccess,
                fontSize: 13,
              }}
            >
              <CheckOutlined />
              <span>
                已导出 {lastResult.count} 条工单
                {lastResult.replyCount > 0 ? `（含 ${lastResult.replyCount} 条回复）` : ''} → {lastResult.filename}
              </span>
            </div>
          )}
        </Space>
      </Card>
    </div>
  );
}
