"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiFetch } from "@/lib/api";

type Errors = Record<string, string[] | string>;

const labels: Record<string, string> = {
  contact_name: "שם מלא", phone: "טלפון", email: "דוא״ל", dog_name: "שם הכלב", dog_age: "גיל הכלב", dog_sex: "מין", care_notes: "מידע חשוב", service: "שירות", start_date: "תאריך התחלה", end_date: "תאריך סיום",
};

export default function RequestPage() {
  const [submitting, setSubmitting] = useState(false);
  const [successId, setSuccessId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Errors>({});

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrors({});
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(form.entries());
    if (!body.dog_age) delete body.dog_age;
    try {
      const response = await apiFetch("/stay-requests/", { method: "POST", body: JSON.stringify(body) });
      const data = await response.json();
      if (!response.ok) {
        setErrors(data);
        return;
      }
      setSuccessId(data.id);
    } catch {
      setErrors({ general: "לא הצלחנו לשלוח את הבקשה. ודאו שהשרת פועל ונסו שוב." });
    } finally {
      setSubmitting(false);
    }
  }

  if (successId) {
    return (
      <main className="narrow-page">
        <section className="success-card" role="status">
          <span className="success-icon" aria-hidden="true">✓</span>
          <p className="eyebrow">בקשה מספר {successId}</p>
          <h1>הבקשה נקלטה וממתינה לבדיקה</h1>
          <p>זו עדיין אינה הזמנה מאושרת. מנהל יעבור על הפרטים ויצור קשר לאחר בדיקת הבקשה.</p>
          <Link className="button primary" href="/">חזרה לדף הבית</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="form-page">
      <div className="form-intro">
        <span className="eyebrow">בקשת אירוח</span>
        <h1>נכיר אתכם ואת הכלב</h1>
        <p>מלאו את הפרטים הראשוניים. שליחת הטופס אינה אישור הזמנה; כל בקשה נבדקת ומאושרת ידנית.</p>
        <div className="info-box"><strong>לפני שמתחילים</strong><p>אין צורך לשלוח מידע רפואי מפורט או מסמכים בשלב הזה. ניתן לציין בקצרה צרכים שחשוב שנדע.</p></div>
      </div>
      <form className="request-form" onSubmit={submit} noValidate>
        {errors.general && <div className="form-error" role="alert">{String(errors.general)}</div>}
        {errors.non_field_errors && <div className="form-error" role="alert">{String(errors.non_field_errors)}</div>}
        <fieldset><legend>פרטי קשר</legend>
          <Field name="contact_name" label="שם מלא" required errors={errors} autoComplete="name" />
          <Field name="phone" label="טלפון" required errors={errors} type="tel" autoComplete="tel" inputMode="tel" />
          <Field name="email" label="דוא״ל (לא חובה)" errors={errors} type="email" autoComplete="email" />
        </fieldset>
        <fieldset><legend>פרטי הכלב</legend>
          <div className="two-columns">
            <Field name="dog_name" label="שם הכלב" required errors={errors} />
            <Field name="dog_age" label="גיל (לא חובה)" errors={errors} type="number" min="0" max="30" step="0.1" />
          </div>
          <label>מין<select name="dog_sex" defaultValue="unknown"><option value="unknown">לא צוין</option><option value="female">נקבה</option><option value="male">זכר</option></select>{errorFor(errors, "dog_sex")}</label>
          <label>מידע חשוב על טיפול, רגישויות או התנהגות (לא חובה)<textarea name="care_notes" rows={4} maxLength={2000} placeholder="למשל: רגישה לרעש, נוטלת תרופה, מסתדרת עם כלבים..." />{errorFor(errors, "care_notes")}</label>
        </fieldset>
        <fieldset><legend>האירוח המבוקש</legend>
          <label>שירות<select name="service" required defaultValue=""><option value="" disabled>בחרו שירות</option><option value="overnight">לינה</option><option value="daycare">אירוח יומי</option><option value="transport">איסוף והחזרה</option></select>{errorFor(errors, "service")}</label>
          <div className="two-columns">
            <Field name="start_date" label="תאריך התחלה" required errors={errors} type="date" />
            <Field name="end_date" label="תאריך סיום" required errors={errors} type="date" />
          </div>
        </fieldset>
        <p className="form-note">בלחיצה על הכפתור הבקשה תישלח לבדיקה ותישמר בסטטוס ״ממתינה״.</p>
        <button className="button primary full" disabled={submitting}>{submitting ? "שולחים..." : "שליחת בקשה לבדיקה"}</button>
      </form>
    </main>
  );
}

function Field({ name, label, errors, ...props }: { name: string; label: string; errors: Errors } & React.InputHTMLAttributes<HTMLInputElement>) {
  return <label>{label}<input name={name} {...props} />{errorFor(errors, name)}</label>;
}

function errorFor(errors: Errors, name: string) {
  if (!errors[name]) return null;
  const message = Array.isArray(errors[name]) ? errors[name][0] : errors[name];
  return <span className="field-error" role="alert">{labels[name]}: {message}</span>;
}
