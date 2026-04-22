import dayjs from 'dayjs';
import { Tag, Tooltip } from 'antd';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { MessageItem } from './types';
import { PRIORITY_COLOR } from './constants';

/** 格式化反馈时间：优先用 feedback_time，否则用 create_time（毫秒时间戳） */
export const formatFeedbackTime = (feedbackTime: string | undefined, createTime?: string | number | null): string => {
  if (feedbackTime && String(feedbackTime).trim()) return feedbackTime.trim();
  if (createTime == null || createTime === '') return '-';
  const ms = typeof createTime === 'number' ? createTime : Number(createTime);
  if (!Number.isFinite(ms)) return '-';
  const d = dayjs(ms);
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : '-';
};

const FIELD_VALUE_MAX_LEN = 4;

export const getParsedFieldMap = (message?: MessageItem | null): Record<string, string> => {
  const parsedContent = message?.ext?.parsedContent;
  if (Array.isArray(parsedContent)) {
    return parsedContent.reduce<Record<string, string>>((acc, item) => {
      if (item?.key) {
        acc[item.key] = item.value ?? '';
      }
      return acc;
    }, {});
  }
  if (parsedContent && typeof parsedContent === 'object') {
    return Object.entries(parsedContent).reduce<Record<string, string>>((acc, [key, value]) => {
      acc[key] = value == null ? '' : String(value);
      return acc;
    }, {});
  }
  return {};
};

export const getParsedText = (message?: MessageItem | null): string => {
  const parsedContent = message?.ext?.parsedContent;
  if (typeof parsedContent === 'string') {
    return parsedContent;
  }
  if (Array.isArray(parsedContent)) {
    return parsedContent
      .map((item) => item?.value?.trim())
      .filter(Boolean)
      .join('\n');
  }
  if (parsedContent && typeof parsedContent === 'object') {
    return Object.values(parsedContent)
      .map((value) => (value == null ? '' : String(value).trim()))
      .filter(Boolean)
      .join('\n');
  }
  return '';
};

export const renderReplyContent = (message?: MessageItem | null, isAppCard?: boolean) => {
  const botReply = message?.ext?.botReplyContent;
  if (isAppCard && typeof botReply === 'string' && botReply) {
    return (
      <div className="bot-reply-md" style={{ padding: '8px 12px', background: 'rgba(0,0,0,0.04)', borderRadius: 6, fontSize: 13, lineHeight: 1.6 }}>
        <Markdown remarkPlugins={[remarkGfm]}>{botReply}</Markdown>
      </div>
    );
  }
  if (isAppCard && (!botReply || botReply === '')) {
    return (
      <div style={{ padding: '8px 12px', background: 'rgba(0,0,0,0.02)', borderRadius: 6, fontSize: 13, color: 'rgba(0,0,0,0.35)', fontStyle: 'italic' }}>
        机器人暂未生成有意义的回复内容
      </div>
    );
  }
  const parsedContent = message?.ext?.parsedContent;
  if ((message?.ext?.typeDetail === 'reply_interactive' || message?.ext?.typeDetail === 'reply_post') && typeof parsedContent === 'string') {
    return <div dangerouslySetInnerHTML={{ __html: parsedContent }} />;
  }
  const text = getParsedText(message) || '-';
  if (text) {
    return (
      <div style={{ padding: '8px 12px', background: 'rgba(0,0,0,0.04)', borderRadius: 6, fontSize: 13, lineHeight: 1.6 }}>
        {text}
      </div>
    );
  }
  return text;
};

export const renderFieldValue = (fieldKey: string, value: string) => {
  if (!value) return '-';
  if (fieldKey === 'priority') {
    return <Tag color={PRIORITY_COLOR[value] ?? 'default'}>{value}</Tag>;
  }
  if (fieldKey === 'online_version_url') {
    return <a href={value} target="_blank" rel="noopener noreferrer">点此查看</a>;
  }
  const truncated = value.length > FIELD_VALUE_MAX_LEN
    ? `${value.slice(0, FIELD_VALUE_MAX_LEN)}...`
    : value;
  return (
    <Tooltip title={value}>
      <span style={{ cursor: 'default', whiteSpace: 'nowrap' }}>{truncated}</span>
    </Tooltip>
  );
};
