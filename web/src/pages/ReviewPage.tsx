import { useEffect, useState } from 'react';
import { Card } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { Search, Filter, ChevronRight, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiGet } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

type DocListItem = {
  id: string;
  title: string;
  doc_number: string | null;
  status: string;
  security_level: string;
  urgency: string;
  created_at: string;
};

export default function ReviewPage() {
  const { role } = useRole();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await apiGet<DocListItem[]>('/documents/', role);
        if (active) setDocuments(data);
      } catch (err) {
        console.error(err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [role]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Review Queue</h1>
          <p className="text-slate-500">Manage and route incoming administrative documents.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Search documents..."
              className="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none w-64"
            />
          </div>
          <button className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-50">
            <Filter size={18} className="text-slate-600" />
          </button>
        </div>
      </div>

      <Card>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-12 flex flex-col items-center justify-center text-slate-400 gap-4">
              <Loader2 className="animate-spin" size={32} />
              <p className="font-medium">Fetching documents from SecureFlow API...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              <p className="font-medium">No documents in queue.</p>
              <p className="text-xs">Upload documents via Intake page to populate the review queue.</p>
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold">
                <tr>
                  <th className="px-6 py-4">Title</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Urgency</th>
                  <th className="px-6 py-4">Security</th>
                  <th className="px-6 py-4">Created</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    role="link"
                    tabIndex={0}
                    onClick={() => navigate(`/documents/${doc.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        navigate(`/documents/${doc.id}`);
                      }
                    }}
                    className="cursor-pointer hover:bg-blue-50/50 focus:bg-blue-50 focus:outline-none transition-colors group"
                    data-testid="review-row"
                    data-doc-id={doc.id}
                  >
                    <td className="px-6 py-4 font-bold text-slate-900 group-hover:text-blue-800">{doc.title}</td>
                    <td className="px-6 py-4">
                      <Badge variant="secondary" className="capitalize">
                        {doc.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge className={`capitalize text-[10px] ${
                        doc.urgency === 'critical' ? 'bg-red-600' :
                        doc.urgency === 'urgent' ? 'bg-orange-500' :
                        'bg-slate-400'
                      }`}>
                        {doc.urgency}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 capitalize">{doc.security_level.replace(/_/g, ' ')}</td>
                    <td className="px-6 py-4 text-xs text-slate-400">{new Date(doc.created_at).toLocaleDateString()}</td>
                    <td className="px-6 py-4 text-right">
                      <ChevronRight
                        size={18}
                        className="inline-block text-slate-300 group-hover:text-blue-600 transition-colors"
                        aria-label="Open document"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
