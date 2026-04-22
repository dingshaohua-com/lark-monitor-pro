import { CheckCircleOutlined, RobotOutlined } from '@ant-design/icons';
import { Button, Card, Descriptions, Modal, Space, Tag, Timeline, theme } from 'antd';
import type { MessageItem } from './types';
import { MSG_TYPE_MAP, TAG_KEYS } from './constants';
import { getParsedFieldMap, renderFieldValue, renderReplyContent } from './utils';

function renderProblemCategoryTag(c?: string) {
  const v = c || '待人工确认';
  if (v.startsWith('技术问题')) return <Tag color="red">{v}</Tag>;
  if (v.startsWith('非技术问题')) return <Tag color="green">{v}</Tag>;
  if (v === '重复反馈') return <Tag color="orange">{v}</Tag>;
  return <Tag color="blue">{v}</Tag>;
}

interface DetailModalProps {
  open: boolean;
  onClose: () => void;
  detail: MessageItem | null;
  loading: boolean;
  workOrderDict: Record<string, string>;
}

export function DetailModal({ open, onClose, detail, loading, workOrderDict }: DetailModalProps) {
  const { token } = theme.useToken();
  const detailFields = getParsedFieldMap(detail);
  const detailReplies = detail?.replies ?? [];

  const detailFieldEntries = (() => {
    let entries: [string, string][] = [];
    if (Object.keys(workOrderDict).length > 0) {
      entries = Object.entries(workOrderDict)
        .filter(([, fieldKey]) => fieldKey !== 'user_content' && !TAG_KEYS.includes(fieldKey) && Boolean(detailFields[fieldKey]));
    } else if (detail?.ext?.parsedContent && Array.isArray(detail.ext.parsedContent)) {
      const parsedContent = detail.ext.parsedContent;
      entries = parsedContent
        .filter((item) => item?.key && item.key !== 'user_content' && !TAG_KEYS.includes(item.key ?? '') && item.value)
        .map((item) => [item.label ?? item.key ?? '', item.key ?? ''] as [string, string]);
    }
    const tagsMerged = [detailFields.tag_l1, detailFields.tag_l2, detailFields.tag_l3].filter(Boolean).join(' / ');
    if (tagsMerged) {
      entries.push(['标签', '__tags']);
    }
    return entries;
  })();

  // const detailTitle = detailFields.user_content || '工单详情';

  return (
    <Modal
      title=''
      open={open}
      onCancel={onClose}
      footer={<Button onClick={onClose}>关闭</Button>}
      width={800}
      destroyOnClose
      styles={{
        body: {
          height: '70vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
        },
      }}
    >
      {detail && (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden', gap: 16, padding: 24 }}>
          {detailFieldEntries.length > 0 && (
            <div style={{ flexShrink: 0, maxHeight: '40%', overflowY: 'auto', padding: 24, paddingBottom: 12, borderRadius: token.borderRadiusLG, boxShadow: '0 0 12px rgba(0,0,0,0.1)' }}>
              <Descriptions
                className="work-order-detail-descriptions"
                column={3}
                size="small"
                bordered
                labelStyle={{ whiteSpace: 'nowrap', width: 92 }}
              >
                <Descriptions.Item label="工单ID" span={3}>
                  <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{detail.message_id}</span>
                </Descriptions.Item>
                {detailFieldEntries.map(([label, fieldKey]) => (
                  <Descriptions.Item key={fieldKey} label={label} span={fieldKey === 'cs_remark' ? 3 : 1}>
                    {renderFieldValue(
                      fieldKey,
                      fieldKey === '__tags'
                        ? [detailFields.tag_l1, detailFields.tag_l2, detailFields.tag_l3].filter(Boolean).join(' / ')
                        : detailFields[fieldKey],
                    )}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </div>
          )}

          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '24px', borderRadius: token.borderRadiusLG, boxShadow: '0 0 12px rgba(0,0,0,0.1)' }}>
            <Card size="small" title="处理信息" style={{ borderRadius: token.borderRadiusLG, marginBottom: 20 }}>
              <Descriptions column={2} size="small" labelStyle={{ width: 88 }}>
                <Descriptions.Item label="值班人">
                  {detail.ext?.dutyUser || <span style={{ color: token.colorTextQuaternary }}>-</span>}
                </Descriptions.Item>
                <Descriptions.Item label="问题分类">
                  {renderProblemCategoryTag(detail.ext?.problemCategory)}
                </Descriptions.Item>
                <Descriptions.Item label="机器人参与">
                  {detail.ext?.isRepliedByBot ? (
                    <Tag icon={<RobotOutlined />} color={token.colorPrimary}>是</Tag>
                  ) : (
                    <span style={{ color: token.colorTextQuaternary }}>否</span>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="机器人处理">
                  {!detail.ext?.isRepliedByBot ? (
                    <span style={{ color: token.colorTextQuaternary }}>-</span>
                  ) : detail.ext?.isBotProcessed ? (
                    <Tag icon={<CheckCircleOutlined />} color="success">已处理</Tag>
                  ) : (
                    <Tag color="default">未处理</Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="问题原因" style={{ borderRadius: token.borderRadiusLG, marginBottom: 20 }}>
              {detail.ext?.qaTracking ? (
                <Descriptions column={1} size="small" bordered labelStyle={{ width: 140, whiteSpace: 'nowrap' }}>
                  {Object.entries(detail.ext.qaTracking)
                    .filter(([, v]) => v != null && String(v).trim() !== '')
                    .map(([k, v]) => (
                      <Descriptions.Item key={k} label={k}>
                        <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{String(v)}</div>
                      </Descriptions.Item>
                    ))}
                </Descriptions>
              ) : (
                <div style={{ color: token.colorTextQuaternary, textAlign: 'center', padding: 8 }}>未跟进</div>
              )}
            </Card>

            <Card size="small" title="用户原文" style={{ borderRadius: token.borderRadiusLG, marginBottom: 20 }}>
              <div style={{ maxHeight: 160, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', lineHeight: 1.8 }}>
                {typeof detail.ext?.parsedContent === 'string' ? (
                  <div dangerouslySetInnerHTML={{ __html: detail.ext.parsedContent }} />
                ) : (
                  detailFields.user_content || detailFields.text || '-'
                )}
              </div>
            </Card>
            <Card
              size="small"
              title={`回复 (${detailReplies.length})`}
              style={{ borderRadius: token.borderRadiusLG }}
            >
              {loading ? (
                <div style={{ textAlign: 'center', padding: 16, color: token.colorTextQuaternary }}>加载中...</div>
              ) : detailReplies.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 16, color: token.colorTextQuaternary }}>暂无回复</div>
              ) : (
                <Timeline
                  items={detailReplies.map((reply) => ({
                    children: (
                      <div>
                        <Space size={8} style={{ marginBottom: 4 }}>
                          <Tag color={reply.sender?.sender_type === 'user' ? token.colorPrimary : 'default'}>
                            {reply.sender?.sender_type ?? '-'}
                          </Tag>
                          <Tag color={MSG_TYPE_MAP[reply.msg_type ?? '']?.color ?? 'default'}>
                            {MSG_TYPE_MAP[reply.msg_type ?? '']?.label ?? reply.msg_type ?? '-'}
                          </Tag>
                          <span style={{ fontFamily: 'monospace', fontSize: 12, color: token.colorTextSecondary }}>
                            {reply.create_time}
                          </span>
                        </Space>
                        <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', lineHeight: 1.6 }}>
                          {renderReplyContent(reply, reply.msg_type === 'interactive' && reply.sender?.sender_type === 'app')}
                        </div>
                      </div>
                    ),
                  }))}
                />
              )}
            </Card>
          </div>
        </div>
      )}
    </Modal>
  );
}
