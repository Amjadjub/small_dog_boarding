"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

export default function AdminLogin() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await apiFetch("/auth/login/", { method: "POST", body: JSON.stringify(Object.fromEntries(form.entries())) });
      if (!response.ok) {
        const data = await response.json();
        setError(data.detail ?? "הכניסה נכשלה.");
        return;
      }
      router.replace("/admin/requests");
    } catch {
      setError("לא ניתן להתחבר לשרת כרגע.");
    } finally { setLoading(false); }
  }

  return <main className="narrow-page"><section className="login-card"><span className="eyebrow">אזור מאובטח</span><h1>כניסת מנהלים</h1><p>יש להשתמש בחשבון האישי. פעולות אישור ודחייה מתועדות בשם המנהל.</p><form onSubmit={submit}>{error && <div className="form-error" role="alert">{error}</div>}<label>שם משתמש<input name="username" autoComplete="username" required /></label><label>סיסמה<input name="password" type="password" autoComplete="current-password" required /></label><button className="button primary full" disabled={loading}>{loading ? "מתחברים..." : "כניסה"}</button></form></section></main>;
}
