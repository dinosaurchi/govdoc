/** Static demo downloads served from `web/public/demo/` (copied from paths under `./data` for shipping). */

export type DemoSampleFile = {
  href: string;
  filename: string;
  title: string;
  /** Corresponding path in the local full data pack (not in git). */
  dataPackSource: string;
  description: string;
};

export const DEMO_SAMPLE_FILES: DemoSampleFile[] = [
  {
    href: '/demo/sample-cong-van-dong-nai.pdf',
    filename: 'sample-cong-van-dong-nai.pdf',
    title: 'Công văn (Đồng Nai — mẫu)',
    dataPackSource: 'data/incoming/cong-van/cong-van_dong-nai_mau-cong-van-di.pdf',
    description: 'Official-style letter PDF from the incoming corpus.',
  },
  {
    href: '/demo/sample-bao-cao-dong-nai.pdf',
    filename: 'sample-bao-cao-dong-nai.pdf',
    title: 'Báo cáo (Đồng Nai — văn thư)',
    dataPackSource: 'data/incoming/bao-cao/bao-cao_dong-nai_cong-tac-van-thu-luu-tru.pdf',
    description: 'Periodic report PDF suitable for extraction and routing demos.',
  },
];
