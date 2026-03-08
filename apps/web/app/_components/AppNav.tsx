'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useSession } from '../_hooks/useSession';
import styles from './AppNav.module.css';

const NAV_ITEMS = [
  { href: '/inventory', label: 'Inventory', icon: '🥫' },
  { href: '/planner', label: 'Planner', icon: '📅' },
  { href: '/grocery', label: 'Grocery', icon: '🛒' },
] as const;

export function AppNav() {
  const pathname = usePathname();
  const { user, session } = useSession();

  return (
    <nav className={styles.nav} aria-label="Main navigation">
      <Link href="/" className={styles.brand} aria-label="Meal Planner home">
        <span className={styles.brandIcon}>🍽️</span>
        <span className={styles.brandName}>Meal Planner</span>
      </Link>

      <ul className={styles.navList} role="list">
        {NAV_ITEMS.map(({ href, label, icon }) => (
          <li key={href}>
            <Link
              href={href}
              className={`${styles.navLink} ${
                pathname?.startsWith(href) ? styles.active : ''
              }`}
              aria-current={pathname?.startsWith(href) ? 'page' : undefined}
            >
              <span className={styles.navIcon} aria-hidden="true">
                {icon}
              </span>
              <span>{label}</span>
            </Link>
          </li>
        ))}
      </ul>

      <div className={styles.userArea}>
        {(session.status === 'loading' || session.status === 'retrying') && (
          <span className={styles.userLoading}>Loading…</span>
        )}
        {session.status === 'authenticated' && user && (
          <>
            <span className={styles.userLabel}>Signed in</span>
            <span className={styles.userName} title={user.email}>
              {user.displayName}
            </span>
          </>
        )}
        {session.status === 'unauthenticated' && (
          <span className={styles.userGuest}>Not signed in</span>
        )}
        {session.status === 'unauthorized' && (
          <span className={styles.userError}>⚠ Access blocked</span>
        )}
        {session.status === 'error' && (
          <span className={styles.userError}>⚠ Session error</span>
        )}
      </div>
    </nav>
  );
}
