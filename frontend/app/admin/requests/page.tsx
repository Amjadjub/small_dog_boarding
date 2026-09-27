"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

type StayRequest = { id: number; contact_name: string; phone: string; email: string; dog_name: string; dog_age: string | null; dog_sex: string; care_notes: string; service_label: string; start_date: string; end_date: string; status: "pending" | "approved" | "rejected"; status_label: string; created_at: string; reviewed_by_name: string | null; reviewed_at: string | null };

export default function AdminRequests() {
  const router = useRouter();
  const [requests, setRequests] = useState<StayRequest[]>([]);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [working, setWorking] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const session = await apiFetch("/auth/session/");
      if (!session.ok) { router.replace("/admin/login"); return; }
      setUsername((await session.json()).username);
      const response = await apiFetch("/management/stay-requests/");
      if (!response.ok) throw new Error();
      setRequests(await response.json());
    } catch { setError("לא ניתן לטעון את הבקשות."); }
    finally { setLoading(false); }
  }, [router]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function decide(id: number, decision: "approved" | "rejected") {
    setWorking(id); setError("");
    const response = await apiFetch(`/management/stay-requests/${id}/decision/`, { method: "POST", body: JSON.stringify({ decision }) });
    if (!response.ok) { const data = await response.json(); setError(data.detail ?? "הפעולה נכשלה."); }
    await load(); setWorking(null);
  }

  async function signOut() { await apiFetch("/auth/logout/", { method: "POST" }); router.replace("/admin/login"); }

  return <main className="admin-page"><div className="admin-heading"><div><span className="eyebrow">ניהול פנסיון</span><h1>בקשות אירוח</h1><p>{username && `מחובר/ת: ${username}`}</p></div><button className="text-button" onClick={signOut}>יציאה</button></div>{error && <div className="form-error" role="alert">{error}</div>}{loading ? <div className="empty-state">טוענים בקשות...</div> : requests.length === 0 ? <div className="empty-state"><h2>עדיין אין בקשות</h2><p>בקשות חדשות שיוגשו באתר יופיעו כאן.</p></div> : <div className="request-list">{requests.map((item) => <article className="request-card" key={item.id}><div className="request-card-head"><div><span className={`status ${item.status}`}>{item.status_label}</span><h2>{item.dog_name}</h2><p>{item.service_label} · {formatDate(item.start_date)}–{formatDate(item.end_date)}</p></div><span className="request-number">#{item.id}</span></div><dl><div><dt>בעלים</dt><dd>{item.contact_name}</dd></div><div><dt>טלפון</dt><dd><a href={`tel:${item.phone}`}>{item.phone}</a></dd></div>{item.email && <div><dt>דוא״ל</dt><dd>{item.email}</dd></div>}<div><dt>גיל</dt><dd>{item.dog_age ?? "לא צוין"}</dd></div></dl>{item.care_notes && <div className="notes"><strong>מידע חשוב</strong><p>{item.care_notes}</p></div>}{item.status === "pending" ? <div className="decision-actions"><button className="button approve" disabled={working === item.id} onClick={() => decide(item.id, "approved")}>אישור הבקשה</button><button className="button reject" disabled={working === item.id} onClick={() => decide(item.id, "rejected")}>דחיית הבקשה</button></div> : <p className="audit">טופלה על ידי {item.reviewed_by_name} בתאריך {item.reviewed_at ? new Intl.DateTimeFormat("he-IL", { dateStyle: "short", timeStyle: "short" }).format(new Date(item.reviewed_at)) : "—"}</p>}</article>)}</div>}</main>;
}

function formatDate(value: string) { return new Intl.DateTimeFormat("he-IL", { day: "numeric", month: "numeric", year: "2-digit" }).format(new Date(`${value}T12:00:00`)); }
