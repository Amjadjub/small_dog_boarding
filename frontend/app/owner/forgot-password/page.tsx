"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setLoading(true); setError(""); try { const data = Object.fromEntries(new FormData(event.currentTarget)); const response = await apiFetch("/owner/password-reset/", { method: "POST", body: JSON.stringify(data) }); if (!response.ok) throw new Error(); setSent(true); } catch { setError("לא ניתן לשלוח קישור כרגע."); } finally { setLoading(false); } }
  if (sent) return <main className="narrow-page"><section className="success-card"><span className="success-icon">✉</span><h1>בדקו את הדוא״ל</h1><p>אם קיים חשבון לכתובת הזו, נשלח אליו קישור חד־פעמי לאיפוס הסיסמה.</p><Link className="button primary" href="/owner/login">חזרה לכניסה</Link></section></main>;
  return <main className="narrow-page"><section className="login-card"><span className="eyebrow">שחזור חשבון</span><h1>שכחתי סיסמה</h1><p>נשלח קישור איפוס לכתובת המשויכת לחשבון.</p><form onSubmit={submit}>{error && <div className="form-error">{error}</div>}<label>דוא״ל<input name="email" type="email" autoComplete="email" required /></label><button className="button primary full" disabled={loading}>{loading ? "שולחים..." : "שליחת קישור איפוס"}</button></form></section></main>;
}
