import type { ReactNode } from 'react';
import dayjs from 'dayjs';
import { Tag, Tooltip } from 'antd';
import type { Message } from '@/api/model';
import type {
  BotProcessed,
  QaTracking,
  RawData,
  ReplyCardContent,
  ReplyCardElement,
  ReplyContent,
  ReplyTextContent,
  ThreadContent,
} from './types';
import { PRIORITY_COLOR } from './constants';

/** qa_tracking 中"问题原因 + 解决方案"列名（旧表保留） */
const QA_TRACKING_REASON_KEY = '问题原因&解决方案';

export const getThreadContent = (msg?: Message | null): ThreadContent => {
  return ((msg?.parsed_data as Record<string, unknown> | undefined)?.content as ThreadContent) ?? {};
};

export const getBotProcessed = (msg?: Message | null): BotProcessed | null => {
  return ((msg?.parsed_data as Record<string, unknown> | undefined)?.bot_processed as BotProcessed | null) ?? null;
};

export const getDutyUser = (msg?: Message | null): string => {
  return ((msg?.parsed_data as Record<string, unknown> | undefined)?.duty_user as string) ?? '';
};

export const getQaTracking = (msg?: Message | null): QaTracking | null => {
  return ((msg?.parsed_data as Record<string, unknown> | undefined)?.qa_tracking as QaTracking | null) ?? null;
};

export const getQaTrackingReason = (msg?: Message | null): string => {
  const qt = getQaTracking(msg);
  if (!qt) return '';
  return String(qt[QA_TRACKING_REASON_KEY] ?? '').trim();
};

export const getReplyContent = (msg?: Message | null): ReplyContent => {
  return ((msg?.parsed_data as Record<string, unknown> | undefined)?.content as ReplyContent) ?? {};
};

export const getRawData = (msg?: Message | null): RawData => {
  return (msg?.raw_data as RawData) ?? {};
};

/** 格式化反馈时间：优先 parsed_data.content.feedback_time，否则 raw_data.create_time（毫秒时间戳字符串） */
export const formatFeedbackTime = (msg?: Message | null): string => {
  const fb = getThreadContent(msg).feedback_time;
  if (fb && fb.trim()) return fb.trim();
  return formatTimestampMs(getRawData(msg).create_time);
};

/** 格式化任意时间戳（毫秒字符串/数字） */
export const formatTimestampMs = (ms?: string | number | null): string => {
  if (ms == null || ms === '') return '-';
  const n = typeof ms === 'number' ? ms : Number(ms);
  if (!Number.isFinite(n)) return '-';
  const d = dayjs(n);
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : '-';
};

/** 回复消息纯文本预览 */
export const getReplyPreview = (msg?: Message | null): string => {
  const c = getReplyContent(msg);
  if (!c) return '';
  const text = (c as ReplyTextContent).text;
  if (typeof text === 'string') return text;
  const card = c as ReplyCardContent;
  if (Array.isArray(card.elements)) {
    const parts: string[] = [];
    for (const row of card.elements) {
      if (!Array.isArray(row)) continue;
      for (const el of row) {
        if (!el || typeof el !== 'object') continue;
        if (el.tag === 'text' || el.tag === 'a') {
          parts.push(String((el as { text?: string }).text ?? ''));
        }
      }
    }
    return parts.filter(Boolean).join(' ').trim();
  }
  return '';
};

/** 主消息字段渲染 */
export const renderFieldValue = (fieldKey: string, value: string | undefined): ReactNode => {
  if (!value) return '-';
  if (fieldKey === 'priority') {
    return <Tag color={PRIORITY_COLOR[value] ?? 'default'}>{value}</Tag>;
  }
  if (fieldKey === 'payload_url' && value.startsWith('http')) {
    return (
      <a href={value} target="_blank" rel="noopener noreferrer">点此查看</a>
    );
  }
  const MAX = 10;
  if (value.length > MAX) {
    return (
      <Tooltip title={value}>
        <span style={{ cursor: 'default', whiteSpace: 'nowrap' }}>{`${value.slice(0, MAX)}...`}</span>
      </Tooltip>
    );
  }
  return <span style={{ whiteSpace: 'nowrap' }}>{value}</span>;
};

/** 渲染回复消息正文（卡片/文本） */
export const renderReplyBody = (msg: Message): ReactNode => {
  const content = getReplyContent(msg);
  const text = (content as ReplyTextContent).text;
  if (typeof text === 'string') {
    return <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{text || '-'}</div>;
  }
  const card = content as ReplyCardContent;
  const lines: ReactNode[] = [];
  if (card.title) {
    lines.push(
      <div key="__title" style={{ fontWeight: 600, marginBottom: 4 }}>
        {card.title}
      </div>,
    );
  }
  if (Array.isArray(card.elements)) {
    card.elements.forEach((row, ri) => {
      if (!Array.isArray(row)) return;
      const children: ReactNode[] = [];
      row.forEach((el: ReplyCardElement, ei) => {
        if (!el || typeof el !== 'object') return;
        if (el.tag === 'text') {
          const t = (el as { text?: string }).text ?? '';
          if (t) children.push(<span key={ei}>{t}</span>);
        } else if (el.tag === 'a') {
          const a = el as { text?: string; href?: string };
          children.push(
            <a key={ei} href={a.href} target="_blank" rel="noopener noreferrer">
              {a.text ?? a.href}
            </a>,
          );
        } else if (el.tag === 'img') {
          children.push(
            <span key={ei} style={{ color: 'rgba(0,0,0,0.45)', fontSize: 12 }}>[图片]</span>,
          );
        } else if (el.tag === 'button') {
          const b = el as { text?: string };
          children.push(
            <span key={ei} style={{ color: 'rgba(0,0,0,0.45)', fontSize: 12 }}>[按钮: {b.text ?? ''}]</span>,
          );
        } else if (el.tag === 'hr') {
          children.push(
            <hr key={ei} style={{ border: 0, borderTop: '1px dashed rgba(0,0,0,0.1)', margin: '4px 0' }} />,
          );
        }
      });
      if (children.length > 0) {
        lines.push(
          <div key={ri} style={{ marginBottom: 2 }}>
            {children}
          </div>,
        );
      }
    });
  }
  if (lines.length === 0) return <div>-</div>;
  return <div>{lines}</div>;
};
