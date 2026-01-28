import Papa from 'papaparse';

export interface ParsedHistory {
  data: Record<string, any>[];
  format: 'json' | 'csv';
  message?: string;
}

const isObjectArray = (value: any): value is Record<string, any>[] =>
  Array.isArray(value) && value.every((item) => item && typeof item === 'object');

export const parseHistoryInput = (raw: string): ParsedHistory => {
  const text = (raw || '').trim();
  if (!text) return { data: [], format: 'json', message: '未提供历史数据' };

  // Try JSON first
  try {
    const parsed = JSON.parse(text);
    if (isObjectArray(parsed)) {
      return { data: parsed, format: 'json', message: `已解析 JSON，长度 ${parsed.length}` };
    }
  } catch (err) {
    // fallback to csv
  }

  // Try CSV
  const result = Papa.parse<Record<string, any>>(text, {
    header: true,
    skipEmptyLines: true,
  });
  if (result.errors?.length) {
    throw new Error(result.errors[0]?.message || 'CSV 解析失败');
  }
  const data = (result.data || []).filter((row) => Object.keys(row || {}).length > 0);
  if (!data.length) {
    throw new Error('无法识别文本为 JSON 或 CSV');
  }
  return { data, format: 'csv', message: `已解析 CSV，长度 ${data.length}` };
};
