"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

type Dog = { id: number; name: string; birth_date: string | null; sex: string; feeding_instructions: string; allergies: string; medications: string; behavior_notes: string; veterinarian_name: string; veterinarian_phone: string; emergency_contact?: { name: string; phone: string; relationship: string } | null };
type StayUpdate = { id: number; kind_label: string; message: string; created_at: string };
type Booking = { id: number; dog_name: string | null; service_label: string; start_date: string; end_date: string; status: string; status_label: string; updates: StayUpdate[] };
type StayRequest = { id: number; dog_name: string; service_label: string; start_date: string; end_date: string; status: string; status_label: string };
type Notification = { id: number; title: string; message: string; created_at: string; is_read: boolean };

export default function OwnerDashboard() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [dogs, setDogs] = useState<Dog[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [requests, setRequests] = useState<StayRequest[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDogForm, setShowDogForm] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const session = await apiFetch("/owner/session/");
      if (!session.ok) { router.replace("/owner/login"); return; }
      setName((await session.json()).name);
      const [dogResponse, dashboardResponse, notificationResponse] = await Promise.all([apiFetch("/owner/dogs/"), apiFetch("/owner/dashboard/"), apiFetch("/notifications/")]);
      if (!dogResponse.ok || !dashboardResponse.ok || !notificationResponse.ok) throw new Error();
      setDogs(await dogResponse.json());
      const dashboard = await dashboardResponse.json();
      setBookings(dashboard.bookings); setRequests(dashboard.requests);
      setNotifications(await notificationResponse.json());
    } catch { setError("לא ניתן לטעון את האזור האישי."); }
    finally { setLoading(false); }
  }, [router]);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  async function addDog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const raw = Object.fromEntries(new FormData(event.currentTarget));
    const body = { name: raw.name, birth_date: raw.birth_date || null, sex: raw.sex, feeding_instructions: raw.feeding_instructions, allergies: raw.allergies, medications: raw.medications, behavior_notes: raw.behavior_notes, veterinarian_name: raw.veterinarian_name, veterinarian_phone: raw.veterinarian_phone, emergency_contact: raw.emergency_name && raw.emergency_phone ? { name: raw.emergency_name, phone: raw.emergency_phone, relationship: raw.emergency_relationship } : null };
    const response = await apiFetch("/owner/dogs/", { method: "POST", body: JSON.stringify(body) });
    if (!response.ok) { const data = await response.json(); setError(Object.values(data).flat().join(" ")); return; }
    setShowDogForm(false); await load();
  }

  async function signOut() { await apiFetch("/owner/logout/", { method: "POST" }); router.replace("/owner/login"); }
  async function markRead(id: number) { await apiFetch(`/notifications/${id}/read/`, { method: "POST" }); setNotifications(items => items.map(item => item.id === id ? { ...item, is_read: true } : item)); }

  if (loading) return <main className="owner-page"><div className="empty-state">טוענים את האזור האישי...</div></main>;
  return <main className="owner-page"><div className="portal-heading"><div><span className="eyebrow">האזור האישי</span><h1>שלום {name || "וברוכים הבאים"}</h1><p>כרטיסי הכלבים, הבקשות והעדכונים שלך במקום אחד.</p></div><button className="text-button" onClick={signOut}>יציאה</button></div>{error && <div className="form-error" role="alert">{error}</div>}
    <section className="portal-section"><div className="portal-section-head"><div><h2>הכלבים שלי</h2><p>המידע עוזר לצוות להכיר את הצרכים של כל כלב.</p></div><button className="button secondary" onClick={() => setShowDogForm(!showDogForm)}>{showDogForm ? "סגירה" : "הוספת כלב"}</button></div>
      {showDogForm && <form className="dog-form" onSubmit={addDog}><div className="two-columns"><label>שם הכלב<input name="name" required /></label><label>תאריך לידה<input name="birth_date" type="date" /></label></div><label>מין<select name="sex" defaultValue="unknown"><option value="unknown">לא צוין</option><option value="female">נקבה</option><option value="male">זכר</option></select></label><div className="two-columns"><label>הוראות האכלה<textarea name="feeding_instructions" rows={3} /></label><label>אלרגיות ורגישויות<textarea name="allergies" rows={3} /></label><label>תרופות והוראות<textarea name="medications" rows={3} /></label><label>מידע התנהגותי<textarea name="behavior_notes" rows={3} /></label></div><div className="two-columns"><label>שם הווטרינר<input name="veterinarian_name" /></label><label>טלפון וטרינר<input name="veterinarian_phone" type="tel" /></label></div><h3>איש קשר לחירום</h3><div className="three-columns"><label>שם<input name="emergency_name" /></label><label>טלפון<input name="emergency_phone" type="tel" /></label><label>קרבה<input name="emergency_relationship" /></label></div><button className="button primary">שמירת כרטיס הכלב</button></form>}
      {dogs.length === 0 ? <div className="empty-state compact"><p>עדיין לא נוסף כרטיס כלב.</p></div> : <div className="dog-grid">{dogs.map(dog => <article className="dog-card" key={dog.id}><span className="dog-avatar" aria-hidden="true">🐾</span><div><h3>{dog.name}</h3><p>{dog.allergies ? `רגישויות: ${dog.allergies}` : "לא צוינו רגישויות"}</p></div></article>)}</div>}
    </section>
    <section className="portal-section"><div className="portal-section-head"><div><h2>בקשות והזמנות</h2><p>בקשה ממתינה אינה הזמנה מאושרת.</p></div><Link className="button primary" href="/request">בקשת אירוח חדשה</Link></div>
      {requests.length === 0 && bookings.length === 0 ? <div className="empty-state compact"><p>עדיין אין בקשות או הזמנות בחשבון.</p></div> : <div className="owner-request-list">{requests.map(item => <article className="owner-request" key={`request-${item.id}`}><span className={`status ${item.status}`}>{item.status_label}</span><div><strong>{item.dog_name} · {item.service_label}</strong><p>{formatDate(item.start_date)}–{formatDate(item.end_date)}</p></div></article>)}</div>}
    </section>
    <section className="portal-section"><div className="portal-section-head"><div><h2>התראות</h2><p>אישורים, דחיות ועדכונים מהשהות נשמרים כאן.</p></div></div>{notifications.length === 0 ? <div className="empty-state compact"><p>אין התראות חדשות.</p></div> : <div className="notification-list">{notifications.map(item => <article className={item.is_read ? "notification" : "notification unread"} key={item.id}><div><strong>{item.title}</strong><p>{item.message}</p><time>{formatDateTime(item.created_at)}</time></div>{!item.is_read && <button className="text-button" onClick={() => markRead(item.id)}>סימון כנקראה</button>}</article>)}</div>}</section>
    {bookings.map(booking => <section className="portal-section stay-timeline" key={booking.id}><div className="portal-section-head"><div><span className={`status ${booking.status === "active" ? "approved" : "pending"}`}>{booking.status_label}</span><h2>{booking.dog_name ?? "הזמנה"} · {booking.service_label}</h2><p>{formatDate(booking.start_date)}–{formatDate(booking.end_date)}</p></div></div>{booking.updates.length === 0 ? <div className="empty-state compact"><p>עדיין אין עדכונים מהשהות.</p></div> : <div className="timeline">{booking.updates.map(update => <article key={update.id}><span className="timeline-dot" /><div><strong>{update.kind_label}</strong><time>{new Intl.DateTimeFormat("he-IL", { dateStyle: "short", timeStyle: "short" }).format(new Date(update.created_at))}</time><p>{update.message}</p></div></article>)}</div>}</section>)}
  </main>;
}

function formatDate(value: string) { return new Intl.DateTimeFormat("he-IL", { day: "numeric", month: "numeric", year: "numeric" }).format(new Date(`${value}T12:00:00`)); }
function formatDateTime(value: string) { return new Intl.DateTimeFormat("he-IL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); }
