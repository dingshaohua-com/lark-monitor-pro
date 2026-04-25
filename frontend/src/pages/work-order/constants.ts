export const PRIORITY_COLOR: Record<string, string> = {
  P0: 'red',
  P1: 'volcano',
  P2: 'orange',
  P3: 'blue',
  P4: 'default',
};

export const MSG_TYPE_MAP: Record<string, { label: string; color: string }> = {
  text: { label: '文本', color: 'blue' },
  post: { label: '富文本', color: 'purple' },
  interactive: { label: '卡片', color: 'orange' },
  image: { label: '图片', color: 'green' },
};

export const TAG_KEYS = ['tag_l1', 'tag_l2', 'tag_l3'];

export const priorityOptions = [
  { label: 'P0', value: 'P0' },
  { label: 'P1', value: 'P1' },
  { label: 'P2', value: 'P2' },
  { label: 'P3', value: 'P3' },
  { label: 'P4', value: 'P4' },
];

/** 机器人问题分类筛选项（与 BotReply.problem_category 数据库值保持一致） */
export const problemCategoryOptions = [
  { label: '非技术问题-元芳排查正确', value: '非技术问题-元芳排查正确' },
  { label: '非技术问题-元芳排查有误', value: '非技术问题-元芳排查有误' },
  { label: '技术问题-转bug，元芳排查正确', value: '技术问题-转bug，元芳排查正确' },
  { label: '技术问题-转bug，元芳排查有误', value: '技术问题-转bug，元芳排查有误' },
  { label: '待人工确认', value: '待人工确认' },
  { label: '重复反馈', value: '重复反馈' },
];

/** 主消息 parsed_data.content 字段 -> 中文 label（详情字段区展示顺序） */
export const FIELD_LABELS: Record<string, string> = {
  priority: '优先级',
  wo_type: '分类',
  module: '模块',
  content_tag: '内容标签',
  feedback_id: '反馈ID',
  feedback_time: '反馈时间',
  client_type: '客户端',
  app_version: '版本号',
  device_model: '设备型号',
  customer_service: '所属客服',
  cs_remark: '客服备注',
  student_name: '姓名',
  uid: '用户ID',
  school_name: '学校',
  school_id: '学校ID',
  grade_name: '年级',
  class_name: '班级',
  subject_name: '学科',
  subject_id: '学科ID',
  education_stage_id: '学段ID',
  course_id: '课程ID',
  course_version: '课程版本',
  question_set_id: '题集ID',
  question_set_version: '题集版本',
  question_id: '题目ID',
  question_version: '题目版本',
  knowledge_id: '知识点ID',
  wordbook_id: '词书ID',
  word_group_id: '单词组ID',
  word_id: '单词ID',
  component_id: '组件ID',
  component_version: '组件版本',
  component_index: '组件索引',
  doc_id: '文档ID',
  play_timeline: '播放时间线',
  payload_url: '载荷链接',
  extra_info: '扩展信息',
};
