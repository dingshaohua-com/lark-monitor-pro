import { EyeOutlined, ReloadOutlined, RobotOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Card, Col, DatePicker, Form, Input, Pagination, Row, Select, Table, Tag, Tooltip, theme } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTableScrolly } from '@/components/use-table-scrolly';
import { queryApiMessageGet } from '@/api/endpoints/work-order';
import type { Message, MessageWithReplies, PageMessage } from '@/api/model';
import { PRIORITY_COLOR, problemCategoryOptions } from './constants';
import { DetailModal } from './detail-modal';
import {
  formatFeedbackTime,
  getBotProcessed,
  getDutyUser,
  getQaTrackingReason,
  getThreadContent,
} from './utils';

const { RangePicker } = DatePicker;

interface WorkOrderFilters {
  id?: string;
  keyword?: string;
  problemCategory?: string;
  startDate?: string;
  endDate?: string;
  hasBotProcessed?: string;
  dutyUser?: string;
  hasQaTracking?: string;
}

export default function WorkOrder() {
  const { token } = theme.useToken();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<Message[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailMessage, setDetailMessage] = useState<MessageWithReplies | null>(null);
  const { ref: tableWrapRef, scrollY } = useTableScrolly();

  const fetchData = useCallback(
    async (p: number, size: number, filters: WorkOrderFilters = {}) => {
      setLoading(true);
      try {
        if (filters.id) {
          const data = (await queryApiMessageGet({
            id: filters.id,
            withReply: false,
          })) as Message | null;
          if (data && !Array.isArray(data)) {
            setItems([data]);
            setTotal(1);
            setPage(1);
            setPageSize(size);
          } else {
            setItems([]);
            setTotal(0);
          }
        } else {
          const data = (await queryApiMessageGet({
            page: p,
            pageSize: size,
            keyword: filters.keyword || undefined,
            problemCategory: filters.problemCategory || undefined,
            startDate: filters.startDate || undefined,
            endDate: filters.endDate || undefined,
            hasBotProcessed: filters.hasBotProcessed || undefined,
            dutyUser: filters.dutyUser || undefined,
            hasQaTracking: filters.hasQaTracking || undefined,
          })) as PageMessage;
          setItems(data?.items ?? []);
          setTotal(data?.total ?? 0);
          setPage(data?.page ?? p);
          setPageSize(data?.pageSize ?? size);
        }
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    fetchData(1, pageSize);
  }, [fetchData]);

  const getFilters = (): WorkOrderFilters => {
    const dateRange = form.getFieldValue('dateRange') as [Dayjs, Dayjs] | undefined;
    return {
      id: (form.getFieldValue('id') as string | undefined)?.trim() || undefined,
      keyword: (form.getFieldValue('keyword') as string | undefined)?.trim() || undefined,
      problemCategory:
        (form.getFieldValue('problem_category') as string | undefined) || undefined,
      startDate: dateRange?.[0]?.format('YYYY-MM-DD') || undefined,
      endDate: dateRange?.[1]?.format('YYYY-MM-DD') || undefined,
      hasBotProcessed:
        (form.getFieldValue('has_bot_processed') as string | undefined) || undefined,
      dutyUser: (form.getFieldValue('duty_user') as string | undefined)?.trim() || undefined,
      hasQaTracking:
        (form.getFieldValue('has_qa_tracking') as string | undefined) || undefined,
    };
  };

  const onSearch = () => fetchData(1, pageSize, getFilters());

  const onReset = () => {
    form.resetFields();
    fetchData(1, pageSize);
  };

  const onPageChange = (nextPage: number, nextPageSize: number) => {
    setPage(nextPage);
    setPageSize(nextPageSize);
    fetchData(nextPage, nextPageSize, getFilters());
  };

  const openDetail = async (msg: Message) => {
    setDetailOpen(true);
    setDetailMessage(msg);
    setDetailLoading(true);
    try {
      const data = (await queryApiMessageGet({ id: msg.id, withReply: true })) as
        | MessageWithReplies
        | null;
      setDetailMessage(data ?? (msg as MessageWithReplies));
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ColumnsType<Message> = [
    {
      title: '优先级',
      width: 60,
      align: 'center',
      render: (_, record) => {
        const priority = getThreadContent(record).priority;
        if (!priority) return '-';
        return <Tag color={PRIORITY_COLOR[priority] ?? 'default'}>{priority}</Tag>;
      },
    },
    {
      title: '用户原文',
      width: 100,
      ellipsis: true,
      render: (_, record) => getThreadContent(record).user_content || '-',
    },
    // {
    //   title: '标签',
    //   width: 160,
    //   ellipsis: true,
    //   render: (_, record) => {
    //     const c = getThreadContent(record);
    //     const tags = [c.tag_l1, c.tag_l2, c.tag_l3].filter(Boolean);
    //     return tags.join(' / ') || '-';
    //   },
    // },
    {
      title: '客户端',
      width: 80,
      ellipsis: true,
      render: (_, record) => getThreadContent(record).client_type || '-',
    },
    {
      title: '反馈时间',
      width: 100,
      render: (_, record) => formatFeedbackTime(record),
    },
    {
      title: '值班人',
      width: 60,
      ellipsis: true,
      render: (_, record) => {
        const u = getDutyUser(record);
        return u ? u : <span style={{ color: token.colorTextQuaternary }}>-</span>;
      },
    },
    {
      title: '问题原因',
      width: 60,
      ellipsis: true,
      render: (_, record) => {
        const reason = getQaTrackingReason(record);
        if (!reason) return <span style={{ color: token.colorTextQuaternary }}>-</span>;
        return (
          <Tooltip title={reason} placement="topLeft">
            <span>{reason}</span>
          </Tooltip>
        );
      },
    },
    {
      title: '机器人处理',
      width: 60,
      align: 'center',
      render: (_, record) =>
        getBotProcessed(record) ? (
          <Tag icon={<RobotOutlined />} color={token.colorPrimary}>是</Tag>
        ) : (
          <span style={{ color: token.colorTextQuaternary }}>否</span>
        ),
    },
    {
      title: '问题分类',
      width: 100,
      ellipsis: true,
      render: (_, record) => {
        const c = getBotProcessed(record)?.problem_category;
        if (!c) return <span style={{ color: token.colorTextQuaternary }}>-</span>;
        if (c.startsWith('技术问题')) return <Tag color="red">{c}</Tag>;
        if (c.startsWith('非技术问题')) return <Tag color="green">{c}</Tag>;
        if (c === '重复反馈') return <Tag color="orange">{c}</Tag>;
        return <Tag color="blue">{c}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 90,
      fixed: 'right',
      align: 'center',
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          style={{ color: token.colorPrimary }}
          onClick={() => void openDetail(record)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflow: 'hidden' }}>
      <Card size="small" style={{ borderRadius: token.borderRadiusLG, flexShrink: 0 }} className="!py-2">
        <Form form={form} onFinish={onSearch}>
          <Row gutter={[16, 12]} align="bottom">
            <Col span={8}>
              <Form.Item name="id" label="工单ID" style={{ marginBottom: 0 }}>
                <Input placeholder="精确匹配 message.id" allowClear />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="keyword" label="用户原文" style={{ marginBottom: 0 }}>
                <Input placeholder="按用户原文模糊搜索" allowClear />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="dateRange" label="反馈日期" style={{ marginBottom: 0 }}>
                <RangePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="problem_category" label="问题分类" style={{ marginBottom: 0 }}>
                <Select placeholder="全部" allowClear options={problemCategoryOptions} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="has_bot_processed" label="机器人处理" style={{ marginBottom: 0 }}>
                <Select
                  placeholder="全部"
                  allowClear
                  options={[
                    { label: '已处理', value: 'yes' },
                    { label: '未处理', value: 'no' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="duty_user" label="值班人" style={{ marginBottom: 0 }}>
                <Input placeholder="按值班人模糊匹配" allowClear />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="has_qa_tracking" label="问题原因" style={{ marginBottom: 0 }}>
                <Select
                  placeholder="全部"
                  allowClear
                  options={[
                    { label: '已跟进', value: 'yes' },
                    { label: '未跟进', value: 'no' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={24} style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button icon={<ReloadOutlined />} onClick={onReset}>重置</Button>
              <Button icon={<SearchOutlined />} type="primary" htmlType="submit">查询</Button>
            </Col>
          </Row>
        </Form>
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
        className="!py-8"
        title={<span style={{ fontSize: 15, fontWeight: 600 }}>工单列表</span>}
        extra={
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => fetchData(page, pageSize, getFilters())}
          />
        }
      >
        <div ref={tableWrapRef} style={{ flex: 1, minHeight: 0, overflow: 'hidden' }} className="mt-8">
          <Table<Message>
            rowKey="id"
            columns={columns}
            dataSource={items}
            loading={loading}
            tableLayout="fixed"
            scroll={{ x: 1500, y: scrollY }}
            pagination={false}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', flexShrink: 0, paddingTop: 12 }}>
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            size="small"
            showSizeChanger
            showTotal={(t) => `共 ${t} 条`}
            pageSizeOptions={[10, 20, 50, 100]}
            onChange={onPageChange}
          />
        </div>
      </Card>

      <DetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        message={detailMessage}
        loading={detailLoading}
      />
    </div>
  );
}
