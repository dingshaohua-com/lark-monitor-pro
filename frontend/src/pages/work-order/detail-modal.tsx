import { RobotOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Card, Descriptions, Modal, Space, Tag, Timeline, theme } from 'antd';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, MessageWithReplies } from '@/api/model';
import { FIELD_LABELS, MSG_TYPE_MAP, TAG_KEYS } from './constants';
import {
  formatTimestampMs,
  getBotProcessed,
  getDutyUser,
  getQaTracking,
  getRawData,
  getThreadContent,
  renderFieldValue,
  renderReplyBody,
} from './utils';

function renderProblemCategoryTag(c?: string | null) {
  if (!c) return null;
  if (c.startsWith('技术问题')) return <Tag color="red">{c}</Tag>;
  if (c.startsWith('非技术问题')) return <Tag color="green">{c}</Tag>;
  if (c === '重复反馈') return <Tag color="orange">{c}</Tag>;
  return <Tag color="blue">{c}</Tag>;
}

interface DetailModalProps {
  open: boolean;
  onClose: () => void;
  /** 主消息 + 嵌套的 replies 字段 */
  message: MessageWithReplies | null;
  loading: boolean;
}

export function DetailModal({ open, onClose, message, loading }: DetailModalProps) {
  const { token } = theme.useToken();
  const thread = message;
  const replies = message?.replies ?? [];
  const content = getThreadContent(thread);
  const botProcessed = getBotProcessed(thread);
  const dutyUser = getDutyUser(thread);
  const qaTracking = getQaTracking(thread);
  const qaEntries = qaTracking
    ? Object.entries(qaTracking).filter(
        ([k, v]) => k !== 'record_id' && v != null && String(v).trim() !== '',
      )
    : [];

  const fieldEntries = Object.entries(FIELD_LABELS)
    .filter(([k]) => !TAG_KEYS.includes(k) && content[k])
    .map(([k, label]) => [k, label] as [string, string]);
  const tagsMerged = [content.tag_l1, content.tag_l2, content.tag_l3].filter(Boolean).join(' / ');
  if (tagsMerged) fieldEntries.push(['__tags', '标签']);

  return (
    <Modal
      title=""
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
      {thread && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minHeight: 0,
            overflow: 'hidden',
            gap: 16,
            padding: 24,
          }}
        >
          {fieldEntries.length > 0 && (
            <div
              style={{
                flexShrink: 0,
                maxHeight: '40%',
                overflowY: 'auto',
                padding: 24,
                paddingBottom: 12,
                borderRadius: token.borderRadiusLG,
                boxShadow: '0 0 12px rgba(0,0,0,0.1)',
              }}
            >
              <Descriptions
                className="work-order-detail-descriptions"
                column={3}
                size="small"
                bordered
                labelStyle={{ whiteSpace: 'nowrap', width: 92 }}
              >
                <Descriptions.Item label="工单ID" span={3}>
                  <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{thread.id}</span>
                </Descriptions.Item>
                {fieldEntries.map(([k, label]) => (
                  <Descriptions.Item key={k} label={label} span={k === 'cs_remark' ? 3 : 1}>
                    {k === '__tags' ? tagsMerged : renderFieldValue(k, content[k])}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </div>
          )}

          <div
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              padding: 24,
              borderRadius: token.borderRadiusLG,
              boxShadow: '0 0 12px rgba(0,0,0,0.1)',
            }}
          >
            <Card size="small" title="处理信息" style={{ borderRadius: token.borderRadiusLG, marginBottom: 16 }}>
              <Descriptions column={2} size="small" labelStyle={{ width: 88 }}>
                <Descriptions.Item label="值班人">
                  {dutyUser || <span style={{ color: token.colorTextQuaternary }}>-</span>}
                </Descriptions.Item>
                <Descriptions.Item label="问题分类">
                  {renderProblemCategoryTag(botProcessed?.problem_category) ?? (
                    <span style={{ color: token.colorTextQuaternary }}>-</span>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="机器人处理">
                  {botProcessed ? (
                    <Tag icon={<RobotOutlined />} color={token.colorPrimary}>是</Tag>
                  ) : (
                    <span style={{ color: token.colorTextQuaternary }}>否</span>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="问题原因跟进">
                  {qaTracking ? (
                    <Tag color="success">已跟进</Tag>
                  ) : (
                    <span style={{ color: token.colorTextQuaternary }}>未跟进</span>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="问题原因" style={{ borderRadius: token.borderRadiusLG, marginBottom: 16 }}>
              {qaEntries.length === 0 ? (
                <div style={{ color: token.colorTextQuaternary, textAlign: 'center', padding: 8 }}>未跟进</div>
              ) : (
                <Descriptions column={1} size="small" bordered labelStyle={{ width: 140, whiteSpace: 'nowrap' }}>
                  {qaEntries.map(([k, v]) => (
                    <Descriptions.Item key={k} label={k}>
                      <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{String(v)}</div>
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              )}
            </Card>

            <Card size="small" title="用户原文" style={{ borderRadius: token.borderRadiusLG, marginBottom: 16 }}>
              <div
                style={{
                  maxHeight: 160,
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  lineHeight: 1.8,
                }}
              >
                {content.user_content || '-'}
              </div>
            </Card>

            {botProcessed && (
              <Card
                size="small"
                title={
                  <Space>
                    <RobotOutlined style={{ color: token.colorPrimary }} />
                    <span>机器人处理</span>
                  </Space>
                }
                extra={renderProblemCategoryTag(botProcessed.problem_category)}
                style={{ borderRadius: token.borderRadiusLG, marginBottom: 16 }}
              >
                <div className="bot-reply-md" style={{ fontSize: 13, lineHeight: 1.7 }}>
                  <Markdown remarkPlugins={[remarkGfm]}>{botProcessed.content || ''}</Markdown>
                </div>
                <div style={{ marginTop: 8, color: token.colorTextSecondary, fontSize: 12 }}>
                  <Space split={<span style={{ color: token.colorBorder }}>·</span>}>
                    <span>时间：{formatTimestampMs(botProcessed.timestamp)}</span>
                    <span>👍 {botProcessed.upvoted_by?.length ?? 0}</span>
                    <span>👎 {botProcessed.downvoted_by?.length ?? 0}</span>
                  </Space>
                </div>
              </Card>
            )}

            <Card
              size="small"
              title={`回复 (${replies.length})`}
              style={{ borderRadius: token.borderRadiusLG }}
            >
              {loading ? (
                <div style={{ textAlign: 'center', padding: 16, color: token.colorTextQuaternary }}>加载中...</div>
              ) : replies.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 16, color: token.colorTextQuaternary }}>暂无回复</div>
              ) : (
                <Timeline
                  items={replies.map((r) => {
                    const rd = getRawData(r);
                    const isBot = rd.sender?.sender_type === 'app';
                    return {
                      dot: isBot ? (
                        <RobotOutlined style={{ color: token.colorPrimary }} />
                      ) : (
                        <UserOutlined />
                      ),
                      children: (
                        <div>
                          <Space size={8} style={{ marginBottom: 4 }}>
                            <Tag color={isBot ? token.colorPrimary : 'default'}>
                              {isBot ? '机器人' : '用户'}
                            </Tag>
                            <Tag color={MSG_TYPE_MAP[rd.msg_type ?? '']?.color ?? 'default'}>
                              {MSG_TYPE_MAP[rd.msg_type ?? '']?.label ?? rd.msg_type ?? '-'}
                            </Tag>
                            <span
                              style={{
                                fontFamily: 'monospace',
                                fontSize: 12,
                                color: token.colorTextSecondary,
                              }}
                            >
                              {formatTimestampMs(rd.create_time)}
                            </span>
                          </Space>
                          <div
                            style={{
                              padding: '8px 12px',
                              background: 'rgba(0,0,0,0.04)',
                              borderRadius: 6,
                              fontSize: 13,
                              lineHeight: 1.6,
                            }}
                          >
                            {renderReplyBody(r)}
                          </div>
                        </div>
                      ),
                    };
                  })}
                />
              )}
            </Card>
          </div>
        </div>
      )}
    </Modal>
  );
}
