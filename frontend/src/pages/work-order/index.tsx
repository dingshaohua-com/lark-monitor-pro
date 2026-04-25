import { EyeOutlined, ReloadOutlined, RobotOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Card, Col, Form, Input, Pagination, Row, Select, Table, Tag, theme } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useCallback, useEffect, useState } from 'react';
import { useTableScrolly } from '@/components/use-table-scrolly';
import { queryApiMessageGet } from '@/api/endpoints/work-order';
import type { Message, PageMessage } from '@/api/model';
import { PRIORITY_COLOR, problemCategoryOptions } from './constants';
import { DetailModal } from './detail-modal';
import { formatFeedbackTime, getBotProcessed, getThreadContent } from './utils';

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
  const [detailMessages, setDetailMessages] = useState<Message[]>([]);
  const { ref: tableWrapRef, scrollY } = useTableScrolly();

  const fetchData = useCallback(
    async (
      p: number,
      size: number,
      id?: string,
      keyword?: string,
      problemCategory?: string,
    ) => {
      setLoading(true);
      try {
        if (id) {
          const data = (await queryApiMessageGet({ id, withReply: false })) as Message | null;
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
            keyword: keyword || undefined,
            problemCategory: problemCategory || undefined,
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

  const getFilters = () => {
    const id = (form.getFieldValue('id') as string | undefined)?.trim();
    const keyword = (form.getFieldValue('keyword') as string | undefined)?.trim();
    const problemCategory = form.getFieldValue('problem_category') as string | undefined;
    return { id, keyword, problemCategory };
  };

  const onSearch = () => {
    const { id, keyword, problemCategory } = getFilters();
    fetchData(1, pageSize, id, keyword, problemCategory);
  };

  const onReset = () => {
    form.resetFields();
    fetchData(1, pageSize);
  };

  const onPageChange = (nextPage: number, nextPageSize: number) => {
    setPage(nextPage);
    setPageSize(nextPageSize);
    const { id, keyword, problemCategory } = getFilters();
    fetchData(nextPage, nextPageSize, id, keyword, problemCategory);
  };

  const openDetail = async (msg: Message) => {
    setDetailOpen(true);
    setDetailMessages([msg]);
    setDetailLoading(true);
    try {
      const data = (await queryApiMessageGet({ id: msg.id, withReply: true })) as Message | Message[];
      const list = Array.isArray(data) ? data : data ? [data] : [];
      setDetailMessages(list);
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ColumnsType<Message> = [
    {
      title: '优先级',
      width: 80,
      align: 'center',
      render: (_, record) => {
        const priority = getThreadContent(record).priority;
        if (!priority) return '-';
        return <Tag color={PRIORITY_COLOR[priority] ?? 'default'}>{priority}</Tag>;
      },
    },
    {
      title: '用户原文',
      width: 260,
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
      width: 120,
      ellipsis: true,
      render: (_, record) => getThreadContent(record).client_type || '-',
    },
    {
      title: '反馈时间',
      width: 180,
      render: (_, record) => formatFeedbackTime(record),
    },
   
    {
      title: '机器人处理',
      width: 100,
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
      width: 150,
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
              <Form.Item name="problem_category" label="问题分类" style={{ marginBottom: 0 }}>
                <Select placeholder="全部" allowClear options={problemCategoryOptions} />
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
            onClick={() => {
              const { id, keyword, problemCategory } = getFilters();
              fetchData(page, pageSize, id, keyword, problemCategory);
            }}
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
            scroll={{ x: 1200, y: scrollY }}
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
        messages={detailMessages}
        loading={detailLoading}
      />
    </div>
  );
}
