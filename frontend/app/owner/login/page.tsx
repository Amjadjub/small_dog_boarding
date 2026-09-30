"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

export default function OwnerLogin() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const response = await apiFetch("/owner/login/", { method: "POST", body: JSON.stringify(data) });
      if (!response.ok) { const body = await response.json(); setError(body.detail ?? "הכניסה נכשלה."); return; }
      router.replace("/owner/dashboard");
    } catch { setError("לא ניתן להתחבר לשרת כרגע."); }
    finally { setLoading(false); }
  }

  return <main className="narrow-page"><section className="login-card"><span className="eyebrow">האזור האישי</span><h1>כניסה לבעלי כלבים</h1><p>כאן אפשר לראות בקשות, הזמנות ועדכונים מהשהות.</p><form onSubmit={submit}>{error && <div className="form-error" role="alert">{error}</div>}<label>דוא״ל<input name="email" type="email" autoComplete="email" required /></label><label>סיסמה<input name="password" type="password" autoComplete="current-password" required /></label><button className="button primary full" disabled={loading}>{loading ? "מתחברים..." : "כניסה"}</button></form><p className="auth-switch">עדיין אין חשבון? <Link href="/owner/register">יצירת חשבון</Link></p></section></main>;
}
