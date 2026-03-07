'use client';

import type { StorageLocation } from '../../_lib/types';
import styles from './LocationTabs.module.css';

const TABS: { location: StorageLocation; label: string; icon: string }[] = [
  { location: 'pantry', label: 'Pantry', icon: '🗄️' },
  { location: 'fridge', label: 'Fridge', icon: '🧊' },
  { location: 'freezer', label: 'Freezer', icon: '❄️' },
  { location: 'leftovers', label: 'Leftovers', icon: '🍱' },
];

type Props = {
  active: StorageLocation;
  onChange: (location: StorageLocation) => void;
};

export function LocationTabs({ active, onChange }: Props) {
  return (
    <div className={styles.tabs} role="tablist" aria-label="Storage location">
      {TABS.map(({ location, label, icon }) => (
        <button
          key={location}
          role="tab"
          aria-selected={active === location}
          className={`${styles.tab} ${active === location ? styles.active : ''}`}
          onClick={() => onChange(location)}
          type="button"
        >
          <span aria-hidden="true">{icon}</span>
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}
