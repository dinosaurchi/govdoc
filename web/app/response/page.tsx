'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { Send, FileCheck, Download, History, UserCheck, Loader2, CheckCircle2 } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

type RespDoc = {
  id: number;
  title: string;
  state: string;
  analysis?: { summary?: string } | null;
};

export default function ResponsePage() {
  const { role } = useRole();
  const [documents, setDocuments] = useState<RespDoc[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<RespDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchResponses = async () => {
    try {
      const data = await fetchApi('/documents');
      const respDocs = data.filter((d: { state: string }) =>
        ['response_prepared', 'closed'].includes(d.state)
      );
      setDocuments(respDocs);
      setSelectedDoc((prev: RespDoc | null) => prev ?? respDocs[0] ?? null);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await fetchApi('/documents');
        const respDocs = data.filter((d: { state: string }) =>
          ['response_prepared', 'closed'].includes(d.state)
        );
        if (active) {
          setDocuments(respDocs);
          setSelectedDoc((prev: RespDoc | null) => prev ?? respDocs[0] ?? null);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const handleApprove = async () => {
    if (!selectedDoc) return;
    setActionLoading(true);
    try {
      await fetchApi(`/review/${selectedDoc.id}/approve`, { method: 'POST' });
      await fetchResponses();
      const updated = await fetchApi(`/documents/${selectedDoc.id}`);
      setSelectedDoc(updated);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="h-96 flex items-center justify-center"><Loader2 className="animate-spin text-blue-600" size={48} /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Response & Closeout</h1>
          <p className="text-slate-500">Finalize and dispatch official administrative responses.</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <h3 className="font-bold text-sm text-slate-400 uppercase tracking-widest pl-2">Ready for Dispatch</h3>
          {documents.length === 0 ? (
            <div className="p-8 text-center bg-white border border-dashed rounded-2xl text-slate-400">
               <p className="text-xs font-medium">No documents awaiting response finalization.</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') setSelectedDoc(doc);
                }}
                onClick={() => setSelectedDoc(doc)}
                className="rounded-2xl focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
              <Card 
                className={`cursor-pointer transition-all ${selectedDoc?.id === doc.id ? 'border-emerald-500 shadow-md ring-2 ring-emerald-50' : 'hover:border-emerald-200'}`}
              >
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <Badge variant={doc.state === 'closed' ? 'secondary' : 'default'} className={`scale-75 origin-left ${doc.state === 'closed' ? '' : 'bg-emerald-600'}`}>
                      {doc.state.replace(/_/g, ' ')}
                    </Badge>
                    <span className="text-[10px] font-mono text-slate-400">ID: {doc.id}</span>
                  </div>
                  <h4 className="font-bold text-slate-900 leading-tight truncate">{doc.title}</h4>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <UserCheck size={12} /> Status: {doc.state === 'closed' ? 'Dispatched' : 'Pending'}
                  </div>
                </CardContent>
              </Card>
              </div>
            ))
          )}
        </div>

        {selectedDoc ? (
          <Card className="lg:col-span-2">
            <CardHeader className="border-b border-slate-100 flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Review Official Response: {selectedDoc.id}</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono">{selectedDoc.state}</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-8 space-y-6">
              <div className="space-y-4 bg-white p-8 rounded-xl border border-slate-200 shadow-inner min-h-[400px] font-serif relative">
                {selectedDoc.state === 'closed' && (
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[-25deg] opacity-10 pointer-events-none">
                     <div className="border-8 border-emerald-600 rounded-full p-4 flex flex-col items-center justify-center">
                        <CheckCircle2 size={80} className="text-emerald-600" />
                        <span className="text-4xl font-black text-emerald-600 uppercase">ĐÃ BAN HÀNH</span>
                     </div>
                  </div>
                )}
                <div className="flex justify-between items-start border-b border-slate-200 pb-4 mb-8">
                  <div className="text-[10px] font-bold space-y-1 text-slate-900">
                    <p>ỦY BAN NHÂN DÂN THÀNH PHỐ</p>
                    <p className="border-t border-slate-900 pt-1">BỘ PHẬN HÀNH CHÍNH</p>
                  </div>
                  <div className="text-right text-[10px] text-slate-900">
                    <p className="font-bold">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</p>
                    <p className="font-bold border-t border-slate-900 pt-1">Độc lập - Tự do - Hạnh phúc</p>
                  </div>
                </div>

                <div className="text-center space-y-2 py-4">
                  <h2 className="text-lg font-bold uppercase">CÔNG VĂN PHÚC ĐÁP (Baseline Draft)</h2>
                  <p className="text-xs italic">V/v: {selectedDoc.title}</p>
                </div>

                <div className="text-sm space-y-4 text-slate-800 leading-relaxed">
                  <p>Kính gửi: Các phòng ban liên quan</p>
                  <p>
                    Căn cứ vào quá trình rà soát và kết quả tham vấn nội bộ đối với hồ sơ số {selectedDoc.id}. Chúng tôi xin cập nhật trạng thái xử lý cuối cùng cho văn bản này.
                  </p>
                  <p>
                    {selectedDoc.analysis?.summary || "Nội dung văn bản đã được AI xử lý và phân loại chính xác."}
                  </p>
                  <p>
                    Đề nghị đơn vị thực hiện theo các bước rà soát đã được Supervisor phê duyệt trong workflow.
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4">
                {selectedDoc.state === 'response_prepared' && role === 'Supervisor' && (
                  <button 
                    disabled={actionLoading}
                    onClick={handleApprove}
                    className="px-8 py-3 bg-emerald-600 text-white rounded-xl font-bold hover:bg-emerald-700 transition flex items-center gap-2 shadow-lg shadow-emerald-100 disabled:opacity-50"
                  >
                    {actionLoading ? <Loader2 className="animate-spin" size={18} /> : <CheckCircle2 size={18} />}
                    Approve & Issue Official Dispatch
                  </button>
                )}
                {selectedDoc.state === 'closed' && (
                  <button className="px-8 py-3 bg-slate-100 text-slate-900 rounded-xl font-bold hover:bg-slate-200 transition flex items-center gap-2">
                    <Download size={18} /> Download Archive PDF
                  </button>
                )}
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="lg:col-span-2 h-[600px] bg-slate-50 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center text-slate-400 space-y-4">
             <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center shadow-sm">
                <FileCheck size={32} />
             </div>
             <p className="font-bold">Select a response draft to review</p>
          </div>
        )}
      </div>
    </div>
  );
}
