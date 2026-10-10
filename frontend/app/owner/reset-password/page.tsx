"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function ResetPasswordPage() {
  const [done, setDone] = useState(false); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setLoading(true); setError(""); const form = new FormData(event.currentTarget); if (form.get("password") !== form.get("confirm")) { setError("הסיסמאות אינן זהות."); setLoading(false); return; } const query = new URLSearchParams(window.location.search); try { const response = await apiFetch("/owner/password-reset/confirm/", { method: "POST", body: JSON.stringify({ uid: query.get("uid"), token: query.get("token"), password: form.get("password") }) }); const body = await response.json(); if (!response.ok) { setError(body.detail ?? Object.values(body).flat().join(" ")); return; } setDone(true); } catch { setError("לא ניתן לאפס את הסיסמה כרגע."); } finally { setLoading(false); } }
  if (done) return <main className="narrow-page"><section className="success-card"><span className="success-icon">✓</span><h1>הסיסמה עודכנה</h1><p>אפשר להתחבר כעת באמצעות הסיסמה החדשה.</p><Link className="button primary" href="/owner/login">כניסה לחשבון</Link></section></main>;
  return <main className="narrow-page"><section className="login-card"><span className="eyebrow">שחזור חשבון</span><h1>סיסמה חדשה</h1><form onSubmit={submit}>{error && <div className="form-error">{error}</div>}<label>סיסמה חדשה<input name="password" type="password" autoComplete="new-password" minLength={12} required /></label><label>אימות סיסמה<input name="confirm" type="password" autoComplete="new-password" minLength={12} required /></label><button className="button primary full" disabled={loading}>{loading ? "שומרים..." : "שמירת סיסמה"}</button></form></section></main>;
}
