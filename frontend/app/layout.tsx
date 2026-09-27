import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "פנסיון ביתי לכלבים קטנים | גרסת המחשה",
  description: "בקשת אירוח לכלב קטן בסביבה ביתית — גרסת מערכת ראשונית.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="he" dir="rtl">
      <body>
        <header className="site-header">
          <Link className="brand" href="/" aria-label="דף הבית">
            <span className="brand-mark" aria-hidden="true">🐾</span>
            <span>פנסיון קטן בבית</span>
          </Link>
          <nav aria-label="ניווט ראשי">
            <Link href="/#services">שירותים</Link>
            <Link className="nav-cta" href="/request">שליחת בקשה</Link>
          </nav>
        </header>
        {children}
        <footer>
          <p>גרסת מערכת ראשונית — שם העסק, הפרטים והתוכן עדיין לא סופיים.</p>
          <Link href="/admin/login">כניסת מנהלים</Link>
        </footer>
      </body>
    </html>
  );
}
