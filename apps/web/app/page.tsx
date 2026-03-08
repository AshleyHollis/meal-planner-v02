import Link from 'next/link';
import styles from './page.module.css';

export default function HomePage() {
  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.eyebrow}>Household control center</span>
          <h1 className={styles.heading}>Plan meals with trustworthy inventory and a cleaner shopping flow.</h1>
          <p className={styles.sub}>
            Review what is on hand, shape the week with clear planning states, and confirm a grocery list that reads well on desktop and phone.
          </p>
          <div className={styles.heroActions}>
            <Link href="/planner" className={styles.primaryAction}>
              Open planner
            </Link>
            <Link href="/grocery" className={styles.secondaryAction}>
              Review grocery list
            </Link>
          </div>
        </div>
        <div className={styles.heroPanel}>
          <h2 className={styles.panelTitle}>This week at a glance</h2>
          <ul className={styles.heroList}>
            <li>Keep confirmed plans distinct from drafts and suggestions.</li>
            <li>Review inventory freshness and history before you change trust data.</li>
            <li>Use a confirmed grocery snapshot as the stable shopping handoff.</li>
          </ul>
        </div>
      </section>

      <nav className={styles.cards} aria-label="Feature areas">
        <Link href="/inventory" className={styles.card}>
          <span className={styles.cardIcon} aria-hidden="true">🥫</span>
          <span className={styles.cardTitle}>Inventory</span>
          <span className={styles.cardDesc}>
            Track what&apos;s in your pantry, fridge, and freezer.
          </span>
          <span className={styles.cardHint}>Review quantity, freshness, and correction history.</span>
        </Link>

        <Link href="/planner" className={styles.card}>
          <span className={styles.cardIcon} aria-hidden="true">📅</span>
          <span className={styles.cardTitle}>Planner</span>
          <span className={styles.cardDesc}>
            Review AI suggestions, edit slots, and confirm your week.
          </span>
          <span className={styles.cardHint}>Keep confirmed plans visible while replacement drafts are under review.</span>
        </Link>

        <Link href="/grocery" className={styles.card}>
          <span className={styles.cardIcon} aria-hidden="true">🛒</span>
          <span className={styles.cardTitle}>Grocery</span>
          <span className={styles.cardDesc}>
            Shop from a derived list that knows what you already have.
          </span>
          <span className={styles.cardHint}>Preserve traceability, overrides, and trip-ready confirmations.</span>
        </Link>
      </nav>
    </div>
  );
}
