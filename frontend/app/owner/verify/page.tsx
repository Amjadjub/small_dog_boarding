"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function VerifyEmailPage() {
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("מאמתים את כתובת הדוא״ל...");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) { const timer = window.setTimeout(() => { setState("error"); setMessage("קישור האימות חסר או אינו תקין."); }, 0); return () => window.clearTimeout(timer); }
    void apiFetch("/owner/verify-email/", { method: "POST", body: JSON.stringify({ token }) })
      .then(async response => { const body = await response.json(); setMessage(body.detail); setState(response.ok ? "success" : "error"); })
      .catch(() => { setState("error"); setMessage("לא ניתן לאמת את החשבון כרגע."); });
  }, []);

  return <main className="narrow-page"><section className="success-card"><span className="success-icon">{state === "success" ? "✓" : state === "error" ? "!" : "…"}</span><h1>{state === "loading" ? "רק רגע" : state === "success" ? "החשבון אומת" : "האימות נכשל"}</h1><p>{message}</p>{state !== "loading" && <Link className="button primary" href="/owner/login">לעמוד הכניסה</Link>}</section></main>;
}
