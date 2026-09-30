"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

type StayRequest = { id: number; contact_name: string; phone: string; email: string; dog_name: string; dog_age: string | null; care_notes: string; service_label: string; start_date: string; end_date: string; status: "pending" | "approved" | "rejected"; status_label: string; reviewed_by_name: string | null; reviewed_at: string | null; owner_email: string | null };
type StayUpdate = { id: number; kind_label: string; message: string; visible_to_owner: boolean; created_at: string };
type InternalNote = { id: number; note: string; created_by_name: string; created_at: string };
type Booking = { id: number; dog: number | null; dog_name: string | null; owner_email: string | null; service_label: string; start_date: string; end_date: string; status: string; status_label: string; updates: StayUpdate[]; internal_notes: InternalNote[] };

export default function AdminRequests() {
  const router = useRouter();
  const [requests, setRequests] = useState<StayRequest[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [working, setWorking] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const session = await apiFetch("/auth/session/");
      if (!session.ok) { router.replace("/admin/login"); return; }
      setUsername((await session.json()).username);
      const [requestResponse, bookingResponse] = await Promise.all([apiFetch("/management/stay-requests/"), apiFetch("/management/bookings/")]);
      if (!requestResponse.ok || !bookingResponse.ok) throw new Error();
      setRequests(await requestResponse.json()); setBookings(await bookingResponse.json());
    } catch { setError("לא ניתן לטעון את נתוני הניהול."); }
    finally { setLoading(false); }
  }, [router]);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  async function decide(id: number, decision: "approved" | "rejected") {
    setWorking(id); setError("");
    const response = await apiFetch(`/management/stay-requests/${id}/decision/`, { method: "POST", body: JSON.stringify({ decision }) });
    if (!response.ok) { const data = await response.json(); setError(data.detail ?? "הפעולה נכשלה."); }
    await load(); setWorking(null);
  }

  async function changeBookingStatus(id: number, status: string) {
    setWorking(id); const response = await apiFetch(`/management/bookings/${id}/status/`, { method: "POST", body: JSON.stringify({ status }) });
    if (!response.ok) setError("עדכון סטטוס ההזמנה נכשל."); await load(); setWorking(null);
  }

  async function addUpdate(event: FormEvent<HTMLFormElement>, id: number) {
    event.preventDefault(); setWorking(id);
    const form = event.currentTarget; const raw = Object.fromEntries(new FormData(form));
    const body = { kind: raw.kind, message: raw.message, visible_to_owner: raw.visible_to_owner === "on" };
    const response = await apiFetch(`/management/bookings/${id}/updates/`, { method: "POST", body: JSON.stringify(body) });
    if (!response.ok) setError("שמירת העדכון נכשלה."); else form.reset(); await load(); setWorking(null);
  }

  async function addInternalNote(event: FormEvent<HTMLFormElement>, dogId: number) {
    event.preventDefault(); setWorking(dogId);
    const form = event.currentTarget; const note = String(new FormData(form).get("note") ?? "");
    const response = await apiFetch(`/management/dogs/${dogId}/internal-notes/`, { method: "POST", body: JSON.stringify({ note }) });
    if (!response.ok) setError("שמירת ההערה הפנימית נכשלה."); else form.reset(); await load(); setWorking(null);
  }

  async function signOut() { await apiFetch("/auth/logout/", { method: "POST" }); router.replace("/admin/login"); }

  return <main className="admin-page"><div className="admin-heading"><div><span className="eyebrow">ניהול פנסיון</span><h1>מרכז הפעילות</h1><p>{username && `מחובר/ת: ${username}`}</p></div><button className="text-button" onClick={signOut}>יציאה</button></div>{error && <div className="form-error" role="alert">{error}</div>}{loading ? <div className="empty-state">טוענים נתונים...</div> : <>
    <section className="admin-section"><h2>בקשות אירוח</h2>{requests.length === 0 ? <div className="empty-state"><p>עדיין אין בקשות.</p></div> : <div className="request-list">{requests.map(item => <article className="request-card" key={item.id}><div className="request-card-head"><div><span className={`status ${item.status}`}>{item.status_label}</span><h2>{item.dog_name}</h2><p>{item.service_label} · {formatDate(item.start_date)}–{formatDate(item.end_date)}</p></div><span className="request-number">#{item.id}</span></div><dl><div><dt>בעלים</dt><dd>{item.contact_name}</dd></div><div><dt>טלפון</dt><dd><a href={`tel:${item.phone}`}>{item.phone}</a></dd></div><div><dt>חשבון</dt><dd>{item.owner_email ?? "אורח"}</dd></div><div><dt>גיל</dt><dd>{item.dog_age ?? "לא צוין"}</dd></div></dl>{item.care_notes && <div className="notes"><strong>מידע חשוב</strong><p>{item.care_notes}</p></div>}{item.status === "pending" ? <div className="decision-actions"><button className="button approve" disabled={working === item.id} onClick={() => decide(item.id, "approved")}>אישור ויצירת הזמנה</button><button className="button reject" disabled={working === item.id} onClick={() => decide(item.id, "rejected")}>דחיית הבקשה</button></div> : <p className="audit">טופלה על ידי {item.reviewed_by_name} {item.reviewed_at && `בתאריך ${formatDateTime(item.reviewed_at)}`}</p>}</article>)}</div>}</section>
    <section className="admin-section"><h2>הזמנות ועדכוני שהות</h2>{bookings.length === 0 ? <div className="empty-state"><p>אישור בקשה ייצור כאן הזמנה.</p></div> : <div className="request-list">{bookings.map(booking => <article className="request-card booking-card" key={booking.id}><div className="request-card-head"><div><span className={`status ${booking.status === "active" ? "approved" : "pending"}`}>{booking.status_label}</span><h2>{booking.dog_name ?? "ללא כרטיס כלב"}</h2><p>{booking.service_label} · {formatDate(booking.start_date)}–{formatDate(booking.end_date)}</p><p>{booking.owner_email ?? "בקשת אורח — אין אזור אישי מקושר"}</p></div><select aria-label="סטטוס הזמנה" value={booking.status} disabled={working === booking.id} onChange={event => changeBookingStatus(booking.id, event.target.value)}><option value="upcoming">עתידית</option><option value="active">פעילה</option><option value="completed">הסתיימה</option><option value="canceled">בוטלה</option></select></div><form className="update-form" onSubmit={event => addUpdate(event, booking.id)}><h3>עדכון חדש מהשהות</h3><div className="two-columns"><label>סוג<select name="kind" defaultValue="general"><option value="general">עדכון כללי</option><option value="meal">אוכל ושתייה</option><option value="walk">טיול</option><option value="medication">תרופה</option></select></label><label className="checkbox-label"><input name="visible_to_owner" type="checkbox" defaultChecked />גלוי לבעלים</label></div><label>תוכן העדכון<textarea name="message" rows={3} required maxLength={2000} /></label><button className="button primary" disabled={working === booking.id}>פרסום עדכון</button></form>{booking.updates.length > 0 && <div className="admin-updates">{booking.updates.map(update => <p key={update.id}><strong>{update.kind_label}:</strong> {update.message} <small>{update.visible_to_owner ? "גלוי לבעלים" : "פנימי"}</small></p>)}</div>}{booking.dog && <form className="internal-note-form" onSubmit={event => addInternalNote(event, booking.dog!)}><h3>הערת טיפול פנימית</h3><label>הערה שאינה מוצגת לבעלים<textarea name="note" rows={2} required maxLength={2000} /></label><button className="button secondary" disabled={working === booking.dog}>שמירת הערה פנימית</button>{booking.internal_notes.map(note => <p key={note.id}><strong>{note.created_by_name}:</strong> {note.note}</p>)}</form>}</article>)}</div>}</section>
  </>}</main>;
}

function formatDate(value: string) { return new Intl.DateTimeFormat("he-IL", { day: "numeric", month: "numeric", year: "2-digit" }).format(new Date(`${value}T12:00:00`)); }
function formatDateTime(value: string) { return new Intl.DateTimeFormat("he-IL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); }
