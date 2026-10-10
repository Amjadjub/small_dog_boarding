"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function OwnerRegister() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [created, setCreated] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const response = await apiFetch("/owner/register/", { method: "POST", body: JSON.stringify(data) });
      if (!response.ok) { const body = await response.json(); setError(Object.values(body).flat().join(" ")); return; }
      setCreated(true);
    } catch { setError("לא ניתן ליצור חשבון כרגע."); }
    finally { setLoading(false); }
  }

  if (created) return <main className="narrow-page"><section className="success-card"><span className="success-icon">✉</span><h1>בדקו את הדוא״ל</h1><p>שלחנו קישור אימות. לאחר האימות תוכלו להתחבר ולראות מידע פרטי.</p><Link className="button primary" href="/owner/login">לעמוד הכניסה</Link></section></main>;
  return <main className="narrow-page"><section className="login-card"><span className="eyebrow">חשבון חדש</span><h1>יצירת חשבון בעלים</h1><p>החשבון מאפשר לנהל כרטיסי כלבים ולראות רק את הבקשות והעדכונים שלך.</p><form onSubmit={submit}>{error && <div className="form-error" role="alert">{error}</div>}<label>שם מלא<input name="full_name" autoComplete="name" required /></label><label>טלפון<input name="phone" type="tel" autoComplete="tel" required /></label><label>דוא״ל<input name="email" type="email" autoComplete="email" required /></label><label>סיסמה<input name="password" type="password" autoComplete="new-password" minLength={12} required /><small>לפחות 12 תווים; לא סיסמה נפוצה או מספרית בלבד.</small></label><button className="button primary full" disabled={loading}>{loading ? "יוצרים חשבון..." : "יצירת חשבון"}</button></form><p className="auth-switch">כבר יש חשבון? <Link href="/owner/login">כניסה</Link></p></section></main>;
}
