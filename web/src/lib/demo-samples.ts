/** Demo PDFs are served by GET `/api/v1/demo/sample-files/{filename}` so nginx proxies them with correct headers. */

import { API_BASE_URL } from '@/lib/api';

export type DemoSampleFile = {
  filename: string;
  title: string;
  /** Corresponding path in the local full data pack (not in git). */
  dataPackSource: string;
  description: string;
};

export function demoSampleFileUrl(filename: string): string {
  return `${API_BASE_URL}/demo/sample-files/${encodeURIComponent(filename)}`;
}

export const DEMO_SAMPLE_FILES: DemoSampleFile[] = [
  {
    filename: 'sample-cong-van-dong-nai.pdf',
    title: 'Công văn (Đồng Nai — mẫu)',
    dataPackSource: 'data/incoming/cong-van/cong-van_dong-nai_mau-cong-van-di.pdf',
    description: 'Official-style letter PDF from the incoming corpus.',
  },
  {
    filename: 'sample-bao-cao-dong-nai.pdf',
    title: 'Báo cáo (Đồng Nai — văn thư)',
    dataPackSource: 'data/incoming/bao-cao/bao-cao_dong-nai_cong-tac-van-thu-luu-tru.pdf',
    description: 'Periodic report PDF suitable for extraction and routing demos.',
  },
];
