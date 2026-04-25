import type { Message } from '@/api/model';

/** 主消息 parsed_data.content 的字段（工单结构化信息） */
export interface ThreadContent {
  uid?: string;
  doc_id?: string;
  module?: string;
  tag_l1?: string;
  tag_l2?: string;
  tag_l3?: string;
  wo_type?: string;
  word_id?: string;
  priority?: string;
  course_id?: string;
  cs_remark?: string;
  school_id?: string;
  class_name?: string;
  extra_info?: string;
  grade_name?: string;
  subject_id?: string;
  app_version?: string;
  client_type?: string;
  content_tag?: string;
  feedback_id?: string;
  payload_url?: string;
  question_id?: string;
  school_name?: string;
  wordbook_id?: string;
  component_id?: string;
  device_model?: string;
  knowledge_id?: string;
  student_name?: string;
  subject_name?: string;
  user_content?: string;
  feedback_time?: string;
  play_timeline?: string;
  word_group_id?: string;
  course_version?: string;
  component_index?: string;
  question_set_id?: string;
  customer_service?: string;
  question_version?: string;
  component_version?: string;
  education_stage_id?: string;
  question_set_version?: string;
  [key: string]: string | undefined;
}

/** 回复消息 parsed_data.content 可能的形态 */
export interface ReplyCardContent {
  title?: string;
  elements?: ReplyCardElement[][];
}

export interface ReplyTextContent {
  text?: string;
}

export type ReplyCardElement =
  | { tag: 'text'; text?: string }
  | { tag: 'a'; text?: string; href?: string }
  | { tag: 'img'; image_key?: string }
  | { tag: 'button'; text?: string; type?: string }
  | { tag: 'hr' }
  | { tag: string; [key: string]: unknown };

export type ReplyContent = ReplyCardContent | ReplyTextContent | Record<string, unknown>;

/** 主消息 parsed_data.qa_tracking（来源：qa_tracking.raw_data 整对象，键是飞书表中文列名） */
export type QaTracking = Record<string, string>;

/** 主消息 parsed_data.bot_processed（来源：bot_reply 表） */
export interface BotProcessed {
  id: string;
  ticket_id: string;
  content: string;
  timestamp: string;
  hidden?: boolean;
  upvoted_by?: string[];
  downvoted_by?: string[];
  problem_category?: string | null;
}

/** raw_data 关注字段（飞书原始消息） */
export interface RawDataSender {
  id?: string;
  id_type?: string;
  tenant_key?: string;
  sender_type?: 'app' | 'user' | string;
}

export interface RawDataMention {
  id?: string;
  key?: string;
  name?: string;
  id_type?: string;
  tenant_key?: string;
}

export interface RawData {
  body?: { content?: string };
  sender?: RawDataSender;
  chat_id?: string;
  deleted?: boolean;
  updated?: boolean;
  msg_type?: string;
  thread_id?: string;
  message_id?: string;
  parent_id?: string;
  root_id?: string;
  create_time?: string;
  update_time?: string;
  mentions?: RawDataMention[];
}

/** 导出常用类型别名，方便业务代码使用 */
export type WorkOrderMessage = Message;
