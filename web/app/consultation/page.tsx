'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { Send, User, MessageCircle, Loader2, Info } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

export default function ConsultationPage() {
  const { role } = useRole();
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  const fetchConsultations = async () => {
    try {
      const data = await fetchApi('/documents');
      // Filter for documents that have consultations or are in consultation states
      const consultDocs = data.filter((d: any) => 
        d.state.includes('consultation') || d.consultations.length > 0
      );
      setDocuments(consultDocs);
      if (consultDocs.length > 0 && !selectedDoc) {
        setSelectedDoc(consultDocs[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConsultations();
  }, []);

  const handleSendMessage = async () => {
    if (!message.trim() || !selectedDoc) return;
    setSending(true);
    try {
      await fetchApi(`/consultation/${selectedDoc.id}/note`, {
        method: 'POST',
        body: JSON.stringify({ content: message })
      });
      setMessage('');
      // Refresh selected doc
      const updated = await fetchApi(`/documents/${selectedDoc.id}`);
      setSelectedDoc(updated);
      fetchConsultations();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSending(false);
    }
  };

  if (loading) return <div className="h-96 flex items-center justify-center"><Loader2 className="animate-spin text-blue-600" size={48} /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Internal Consultation</h1>
          <p className="text-slate-500">Cross-departmental collaboration on complex cases.</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <h3 className="font-bold text-sm text-slate-400 uppercase tracking-widest pl-2">Active Requests</h3>
          {documents.length === 0 ? (
             <div className="p-8 text-center bg-white border border-dashed rounded-2xl text-slate-400">
                <p className="text-xs font-medium">No documents currently in consultation.</p>
             </div>
          ) : (
            documents.map((doc) => (
              <Card 
                key={doc.id} 
                className={`cursor-pointer transition-all ${selectedDoc?.id === doc.id ? 'border-blue-500 shadow-md ring-2 ring-blue-50' : 'hover:border-blue-200'}`}
                onClick={() => setSelectedDoc(doc)}
              >
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <Badge variant={doc.state === 'consultation_completed' ? 'secondary' : 'default'} className="scale-75 origin-left">
                      {doc.state.replace(/_/g, ' ')}
                    </Badge>
                    <span className="text-[10px] font-mono text-slate-400">ID: {doc.id}</span>
                  </div>
                  <h4 className="font-bold text-slate-900 leading-tight truncate">{doc.title}</h4>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <MessageCircle size={12} /> {doc.consultations.length} total notes
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {selectedDoc ? (
          <Card className="lg:col-span-2 flex flex-col h-[600px]">
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Thread: {selectedDoc.title}</span>
                <span className="text-xs text-slate-400 font-mono">DOC ID: {selectedDoc.id}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-6 space-y-6">
              {selectedDoc.consultations.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
                  <Info size={24} />
                  <p className="text-sm font-medium">No notes yet. Be the first to comment.</p>
                </div>
              )}
              {selectedDoc.consultations.map((note: any) => (
                <ChatMessage 
                  key={note.id} 
                  sender={`Role ID: ${note.author_role_id}`} 
                  message={note.content} 
                  time={new Date(note.created_at).toLocaleTimeString('vi-VN')} 
                  isMe={false} // Would need real actor ID tracking to differentiate
                />
              ))}
            </CardContent>
            <div className="p-4 border-t border-slate-100 bg-slate-50">
              <div className="flex items-center gap-2">
                <input 
                  type="text" 
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Type your official consultation note..." 
                  className="flex-1 bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
                <button 
                  disabled={sending || !message.trim()}
                  onClick={handleSendMessage}
                  className="p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-50"
                >
                  {sending ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                </button>
              </div>
            </div>
          </Card>
        ) : (
          <div className="lg:col-span-2 h-[600px] bg-slate-50 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center text-slate-400 space-y-4">
             <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center shadow-sm">
                <MessageCircle size={32} />
             </div>
             <p className="font-bold">Select a thread to start collaborating</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ChatMessage({ sender, message, time, isMe, isSystem }: { sender: string, message: string, time: string, isMe?: boolean, isSystem?: boolean }) {
  if (isSystem) {
    return <div className="text-center text-[10px] text-slate-400 uppercase font-black tracking-widest">{message} ({time})</div>;
  }
  
  return (
    <div className={`flex flex-col ${isMe ? 'items-end' : 'items-start'} space-y-1`}>
      <div className="flex items-center gap-2 px-2">
        <span className="text-[10px] font-bold text-slate-400">{sender}</span>
        <span className="text-[10px] text-slate-300">{time}</span>
      </div>
      <div className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm ${isMe ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white border border-slate-200 text-slate-900 rounded-tl-none'}`}>
        {message}
      </div>
    </div>
  );
}
