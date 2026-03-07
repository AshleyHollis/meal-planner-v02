'use client';

import { useState } from 'react';
import styles from './AdHocItemForm.module.css';

type Props = {
  onAdd: (name: string, quantity: number, unit: string) => void;
  disabled?: boolean;
};

export function AdHocItemForm({ onAdd, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [unit, setUnit] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const qty = parseFloat(quantity);
    if (!name.trim() || isNaN(qty) || qty <= 0 || !unit.trim()) return;
    onAdd(name.trim(), qty, unit.trim());
    setName('');
    setQuantity('1');
    setUnit('');
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
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Add grocery item">
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
          placeholder="Unit"
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          aria-label="Unit"
          required
        />
      </div>
      <div className={styles.actions}>
        <button className={styles.saveButton} type="submit">
          Add to list
        </button>
        <button
          className={styles.cancelButton}
          type="button"
          onClick={() => setOpen(false)}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
