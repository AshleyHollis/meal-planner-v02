'use client';

import { useEffect, useState } from 'react';
import type { FreshnessBasis, StorageLocation } from '../../_lib/types';
import styles from './AddItemForm.module.css';

export type AddItemValues = {
  name: string;
  quantity: number;
  unit: string;
  location: StorageLocation;
  freshnessBasis: FreshnessBasis;
  expiryDate: string;
  estimatedExpiryDate: string;
  freshnessNote: string;
};

type Props = {
  defaultLocation: StorageLocation;
  onAdd: (values: AddItemValues) => void | Promise<void>;
  disabled?: boolean;
};

export function AddItemForm({ defaultLocation, onAdd, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [unit, setUnit] = useState('');
  const [location, setLocation] = useState<StorageLocation>(defaultLocation);
  const [freshnessBasis, setFreshnessBasis] = useState<FreshnessBasis>('unknown');
  const [expiryDate, setExpiryDate] = useState('');
  const [estimatedExpiryDate, setEstimatedExpiryDate] = useState('');
  const [freshnessNote, setFreshnessNote] = useState('');

  useEffect(() => {
    setLocation(defaultLocation);
  }, [defaultLocation]);

  function resetForm() {
    setName('');
    setQuantity('1');
    setUnit('');
    setLocation(defaultLocation);
    setFreshnessBasis('unknown');
    setExpiryDate('');
    setEstimatedExpiryDate('');
    setFreshnessNote('');
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const qty = parseFloat(quantity);
    if (!name.trim() || Number.isNaN(qty) || qty <= 0 || !unit.trim()) return;

    onAdd({
      name: name.trim(),
      quantity: qty,
      unit: unit.trim(),
      location,
      freshnessBasis,
      expiryDate,
      estimatedExpiryDate,
      freshnessNote: freshnessNote.trim(),
    });
    resetForm();
    setOpen(false);
  }

  if (!open) {
    return (
      <button
        className={styles.addButton}
        onClick={() => setOpen(true)}
        disabled={disabled}
        type="button"
      >
        + Add item
      </button>
    );
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Add inventory item">
      <div className={styles.fields}>
        <input
          className={styles.input}
          placeholder="Item name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-label="Item name"
          required
        />
        <input
          className={`${styles.input} ${styles.qty}`}
          type="number"
          min="0.01"
          step="0.01"
          placeholder="Qty"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          aria-label="Quantity"
          required
        />
        <input
          className={`${styles.input} ${styles.unit}`}
          placeholder="Unit (e.g. g, ml, ea)"
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          aria-label="Unit"
          required
        />
        <select
          className={styles.input}
          value={location}
          onChange={(e) => setLocation(e.target.value as StorageLocation)}
          aria-label="Storage location"
        >
          <option value="pantry">Pantry</option>
          <option value="fridge">Fridge</option>
          <option value="freezer">Freezer</option>
          <option value="leftovers">Leftovers</option>
        </select>
      </div>

      <div className={styles.fields}>
        <select
          className={styles.input}
          value={freshnessBasis}
          onChange={(e) => setFreshnessBasis(e.target.value as FreshnessBasis)}
          aria-label="Freshness basis"
        >
          <option value="unknown">Freshness unknown</option>
          <option value="known">Exact expiry date known</option>
          <option value="estimated">Estimated expiry</option>
        </select>

        {freshnessBasis === 'known' && (
          <input
            className={styles.input}
            type="date"
            value={expiryDate}
            onChange={(e) => setExpiryDate(e.target.value)}
            aria-label="Expiry date"
          />
        )}

        {freshnessBasis === 'estimated' && (
          <input
            className={styles.input}
            type="date"
            value={estimatedExpiryDate}
            onChange={(e) => setEstimatedExpiryDate(e.target.value)}
            aria-label="Estimated expiry date"
          />
        )}
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.helpText} htmlFor="freshness-note">
          Optional freshness note
        </label>
        <input
          id="freshness-note"
          className={styles.input}
          placeholder="e.g. opened yesterday, store estimate"
          value={freshnessNote}
          onChange={(e) => setFreshnessNote(e.target.value)}
          aria-label="Freshness note"
        />
      </div>

      <div className={styles.actions}>
        <button className={styles.saveButton} type="submit">
          Save
        </button>
        <button
          className={styles.cancelButton}
          type="button"
          onClick={() => {
            resetForm();
            setOpen(false);
          }}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
