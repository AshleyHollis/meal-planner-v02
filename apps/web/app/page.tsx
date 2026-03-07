import Link from 'next/link';
import styles from './page.module.css';

export default function HomePage() {
  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <h1 className={styles.heading}>Meal Planner</h1>
        <p className={styles.sub}>
          Plan your week, manage what you have, and shop with confidence.
        </p>
      </section>

      <nav className={styles.cards} aria-label="Feature areas">
        <Link href="/inventory" className={styles.card}>
          <span className={styles.cardIcon} aria-hidden="true">🥫</span>
          <span className={styles.cardTitle}>Inventory</span>
          <span className={styles.cardDesc}>
            Track what&apos;s in your pantry, fridge, and freezer.
          </span>
        </Link>

        <Link href="/planner" className={styles.card}>
          <span className={styles.cardIcon} aria-hidden="true">📅</span>
          <span className={styles.cardTitle}>Planner</span>
          <span className={styles.cardDesc}>
            Review AI suggestions, edit slots, and confirm your week.
          </span>
        </Link>

        <Link href="/grocery" className={styles.card}>
          <span className={styles.cardIcon} aria-hidden="true">🛒</span>
          <span className={styles.cardTitle}>Grocery</span>
          <span className={styles.cardDesc}>
            Shop from a derived list that knows what you already have.
          </span>
        </Link>
      </nav>
    </div>
  );
}
