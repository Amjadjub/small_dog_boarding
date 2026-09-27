import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">פנסיון ביתי לכלבים קטנים</span>
          <h1>אירוח קטן, שקט וביתי</h1>
          <p>מקום להכיר, לשאול ולשלוח בקשת אירוח. כל בקשה נבדקת באופן אישי ורק אישור מפורש הופך אותה להזמנה.</p>
          <div className="hero-actions">
            <Link className="button primary" href="/request">שליחת בקשת אירוח</Link>
            <a className="button secondary" href="#services">לשירותים</a>
          </div>
          <p className="notice">האתר בהרצה: התוכן והפרטים המוצגים הם להמחשה בלבד.</p>
        </div>
        <figure className="hero-image">
          <Image src="/images/small-dogs-home-placeholder.png" alt="שני כלבים קטנים נחים בבית — תמונת המחשה" fill priority sizes="(max-width: 800px) 100vw, 50vw" />
          <figcaption>תמונת המחשה שנוצרה עבור גרסת הפיתוח</figcaption>
        </figure>
      </section>

      <section className="services" id="services" aria-labelledby="services-heading">
        <div className="section-heading">
          <span className="eyebrow">מה מתוכנן</span>
          <h2 id="services-heading">שירותים בהתאמה לכלב</h2>
          <p>הזמינות, המחירים ואזור האיסוף יפורסמו לאחר שייקבעו.</p>
        </div>
        <div className="service-grid">
          <article><span aria-hidden="true">☾</span><h3>לינה</h3><p>אירוח לילי בסביבה ביתית. פרטי השהות יתואמו רק לאחר אישור הבקשה.</p></article>
          <article><span aria-hidden="true">☀</span><h3>אירוח יומי</h3><p>שהות במהלך היום לכלבים קטנים, בהתאם לזמינות ולהיכרות מוקדמת.</p></article>
          <article><span aria-hidden="true">⌁</span><h3>איסוף והחזרה</h3><p>שירות מתוכנן; אזורי השירות והתנאים עדיין לא נקבעו.</p></article>
        </div>
      </section>

      <section className="how-it-works">
        <div><span>1</span><h3>שולחים בקשה</h3><p>ממלאים פרטי קשר, פרטי הכלב והתאריכים המבוקשים.</p></div>
        <div><span>2</span><h3>הבקשה נבדקת</h3><p>מנהל בוחן התאמה וזמינות. בשלב הזה זו עדיין לא הזמנה.</p></div>
        <div><span>3</span><h3>מקבלים החלטה</h3><p>רק אישור מפורש של מנהל הופך את הבקשה למאושרת.</p></div>
      </section>
    </main>
  );
}
