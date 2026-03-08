'use client';

import { useState } from 'react';
import styles from './AdHocItemForm.module.css';

const QUICK_UNITS = ['ea', 'box', 'bag', 'bunch', 'carton'] as const;
const QUICK_QUANTITIES = ['1', '2', '3'] as const;

type Props = {
  onAdd: (name: string, quantity: number, unit: string, note?: string) => void;
  disabled?: boolean;
  mode?: 'review' | 'trip';
};

export function AdHocItemForm({ onAdd, disabled, mode = 'review' }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [unit, setUnit] = useState('ea');
  const [note, setNote] = useState('');
  const tripMode = mode === 'trip';

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const qty = parseFloat(quantity);
    if (!name.trim() || Number.isNaN(qty) || qty <= 0 || !unit.trim()) return;
    onAdd(name.trim(), qty, unit.trim(), note.trim() || undefined);
    setName('');
    setQuantity('1');
    setUnit('ea');
    setNote('');
    setOpen(false);
  }

  if (!open) {
    return (
      <button
        className={tripMode ? styles.tripAddButton : styles.addButton}
        onClick={() => setOpen(true)}
        disabled={disabled}
        type="button"
      >
        {tripMode ? '+ Quick add trip item' : '+ Add item'}
      </button>
    );
  }

  return (
    <form className={`${styles.form} ${tripMode ? styles.tripForm : ''}`} onSubmit={handleSubmit} aria-label="Add grocery item">
      <div className={styles.fields}>
        <input
          className={`${styles.input} ${styles.name}`}
          placeholder={tripMode ? 'What do you still need?' : 'Item name'}
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
          list="grocery-units"
          placeholder="Unit"
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          aria-label="Unit"
          required
        />
        <datalist id="grocery-units">
          <option value="ea" />
          <option value="box" />
          <option value="bag" />
          <option value="bunch" />
          <option value="lb" />
          <option value="oz" />
          <option value="g" />
          <option value="kg" />
          <option value="cup" />
          <option value="tbsp" />
          <option value="tsp" />
          <option value="carton" />
        </datalist>
      </div>

      <div className={styles.quickRow} aria-label="Quick quantity choices">
        {QUICK_QUANTITIES.map((option) => (
          <button
            key={option}
            className={quantity === option ? styles.quickOptionActive : styles.quickOption}
            type="button"
            disabled={disabled}
            onClick={() => setQuantity(option)}
          >
            {option}
          </button>
        ))}
      </div>

      <div className={styles.quickRow} aria-label="Quick unit choices">
        {QUICK_UNITS.map((option) => (
          <button
            key={option}
            className={unit === option ? styles.quickOptionActive : styles.quickOption}
            type="button"
            disabled={disabled}
            onClick={() => setUnit(option)}
          >
            {option}
          </button>
        ))}
      </div>

      <textarea
        className={`${styles.input} ${styles.note}`}
        placeholder={tripMode ? 'Optional note for the shopper' : 'Optional note for this ad hoc item'}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        aria-label="Ad hoc note"
        rows={2}
      />

      <div className={styles.actions}>
        <button className={styles.saveButton} type="submit" disabled={disabled}>
          {tripMode ? 'Save trip item' : 'Add to list'}
        </button>
        <button
          className={styles.cancelButton}
          type="button"
          disabled={disabled}
          onClick={() => setOpen(false)}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
