import { CalendarOutlined, DatabaseOutlined, DeleteOutlined, FileSearchOutlined, RobotOutlined, SyncOutlined } from '@ant-design/icons';
import { Alert, Button, Card, DatePicker, Modal, Radio, Space, Spin, Tag, theme } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import * as rawMsgApi from "@/api/endpoints/work-order"
import { customAxiosInstance } from '@/api/api.base';


const { RangePicker } = DatePicker;

type TaskMode = 'idle' | 'running' | 'done' | 'error';

function useTaskRunner() {
  const [mode, setMode] = useState<TaskMode>('idle');
  const [error, setError] = useState('');

  const start = () => {
    setMode('running');
    setError('');
  };
  const done = () => setMode('done');
  const fail = (msg: string) => {
    setError(msg);
    setMode('error');
  };
  const reset = () => {
    setMode('idle');
    setError('');
  };

  return { mode, error, start, done, fail, reset };
}

interface RawMsgStatus {
  total: number;
  last_sync_at: string | null;
}

const MOCK_STATUS: RawMsgStatus = {
  total: 12483,
  last_sync_at: '2026-03-12T10:15:32',
};

const formatTime = (v: string | null | undefined) => {
  if (!v) return '暂无记录';
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

function BitableSyncCard({ title, icon, apiPath, busy: parentBusy, description = '从飞书多维表格拉取最新数据同步到本地数据库' }: { title: string; icon: React.ReactNode; apiPath: string; busy: boolean; description?: string }) {
  const task = useTaskRunner();
  const [syncedCount, setSyncedCount] = useState<number | null>(null);

  const handleSync = async () => {
    task.start();
    setSyncedCount(null);
    try {
      const res = await customAxiosInstance<{ synced: number }>({ url: apiPath, method: 'POST' });
      setSyncedCount((res as { synced: number }).synced);
      task.done();
    } catch (e: unknown) {
      const err = e as { message?: string };
      task.fail(err?.message || '同步失败');
    }
  };

  const running = task.mode === 'running';

  return (
    <Card
      title={<Space>{icon}<span style={{ fontWeight: 600 }}>{title}</span></Space>}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <span style={{ color: '#888', fontSize: 13 }}>{description}</span>
        <Button
          type="primary"
          icon={<SyncOutlined spin={running} />}
          loading={running}
          disabled={parentBusy || running}
          size="small"
          onClick={handleSync}
        >
          同步
        </Button>
      </div>
      {running && (
        <Spin size="small" style={{ marginTop: 16, display: 'block' }}>
          <Alert type="info" message="正在同步，请稍候…" style={{ marginTop: 12 }} />
        </Spin>
      )}
      {task.mode === 'error' && <Alert type="error" showIcon message={task.error} style={{ marginTop: 12 }} />}
      {task.mode === 'done' && <Alert type="success" showIcon message={`同步完成，共 ${syncedCount ?? 0} 条记录`} style={{ marginTop: 12 }} />}
    </Card>
  );
}


export default function Sync() {
  const { token } = theme.useToken();
  const today = dayjs();

  const [syncMode, setSyncMode] = useState<'continue' | 'range'>('range');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([today, today]);

  const syncTask = useTaskRunner();
  const [status, setStatus] = useState<RawMsgStatus | null>(null);
  const [clearing, setClearing] = useState(false);

  const busy = syncTask.mode === 'running' || clearing;

  const fetchStatus = useCallback(async () => {
    // TODO: 替换为真实接口
    setStatus(MOCK_STATUS);
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleSync = async () => {
    syncTask.start();
    try {
      const _params: { mode: string; start?: string; end?: string } = { mode: syncMode };
      if (syncMode === 'range') {
        _params.start = dateRange[0].format('YYYY-MM-DD');
        _params.end = dateRange[1].format('YYYY-MM-DD');
      }
      await rawMsgApi.syncApiMessageSyncPost(undefined, {data:_params});
      syncTask.done();
      fetchStatus();
    } catch (e: unknown) {
      const err = e as { message?: string };
      syncTask.fail(err?.message || '同步失败');
    }
  };

  const handleClear = () => {
    Modal.confirm({
      title: '确认清空原始数据',
      content: '此操作将删除所有原始消息数据，不可恢复。',
      okText: '确认清空',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setClearing(true);
        try {
          // await rawMsgApi.clearAllApiRawMsgAllDelete();
          fetchStatus();
        } finally {
          setClearing(false);
        }
      },
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflow: 'auto' }}>
      {/* ========== 原始数据 ========== */}
      <Card
        title={
          <Space>
            <DatabaseOutlined style={{ color: token.colorPrimary }} />
            <span style={{ fontWeight: 600 }}>原始数据</span>
            {/* <Statistic value={status?.total ?? '-'} suffix={status ? '条' : undefined} styles={{ content: { fontSize: 14, fontWeight: 600, color: token.colorPrimary, lineHeight: 'inherit' } }} style={{ display: 'inline-flex', marginLeft: 4 }} /> */}
          </Space>
        }
        extra={
          <Space>
            <Button danger size="small" icon={<DeleteOutlined />} loading={clearing} disabled={busy} onClick={handleClear}>
              清空
            </Button>
          </Space>
        }
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <Radio.Group
            value={syncMode}
            onChange={(e) => setSyncMode(e.target.value)}
            disabled={busy}
            size="small"
            optionType="button"
            buttonStyle="solid"
            options={[
              // { label: '从上次继续', value: 'continue' },
              { label: '指定时间段', value: 'range' },
            ]}
          />

          {syncMode === 'range' && <RangePicker size="small" value={dateRange} onChange={(v) => v && setDateRange(v as [dayjs.Dayjs, dayjs.Dayjs])} disabled={busy} style={{ maxWidth: 280 }} />}

          {syncMode === 'continue' && status?.last_sync_at && (
            <Tag color="blue" style={{ margin: 0 }}>
              将从 {formatTime(status.last_sync_at)} 开始拉取
            </Tag>
          )}

          <Button type="primary" icon={<SyncOutlined spin={syncTask.mode === 'running'} />} loading={syncTask.mode === 'running'} disabled={busy} size="small" onClick={handleSync}>
            同步
          </Button>
        </div>

        {syncTask.mode === 'running' && (
          <Spin size="small" style={{ marginTop: 16, display: 'block' }}>
            <Alert type="info" title="正在同步数据，请稍候…" style={{ marginTop: 12 }} />
          </Spin>
        )}
        {syncTask.mode === 'error' && <Alert type="error" showIcon title={syncTask.error} style={{ marginTop: 12 }} />}
        {syncTask.mode === 'done' && <Alert type="success" showIcon title="同步完成" style={{ marginTop: 12 }} />}
      </Card>

      {/* ========== 值班表同步 ========== */}
      <BitableSyncCard
        title="值班表"
        icon={<CalendarOutlined style={{ color: token.colorSuccess }} />}
        apiPath="/api/bitable/sync-duty"
        busy={busy}
      />

      {/* ========== 问题原因表同步 ========== */}
      <BitableSyncCard
        title="问题原因表"
        icon={<FileSearchOutlined style={{ color: token.colorWarning }} />}
        apiPath="/api/bitable/sync-qa-tracking"
        busy={busy}
      />

      {/* ========== 机器人回复同步 ========== */}
      <BitableSyncCard
        title="机器人回复"
        icon={<RobotOutlined style={{ color: token.colorInfo }} />}
        apiPath="/api/bot-reply/sync"
        busy={busy}
        description="从 annotation_db 拉取最新机器人回复同步到本地数据库"
      />
    </div>
  );
}
