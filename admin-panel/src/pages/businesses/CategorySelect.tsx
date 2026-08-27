import { useEffect, useState } from "react";
import { apiFetch } from "../../api";
import {
  BUSINESS_CATEGORIES,
  loadBusinessCategories,
  toCategoryOptions,
  type CategoryOption,
} from "./businessCategories";

type Props = {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  id?: string;
};

export default function CategorySelect({ value, onChange, error, id }: Props) {
  const [options, setOptions] = useState<CategoryOption[]>(
    toCategoryOptions(BUSINESS_CATEGORIES)
  );

  useEffect(() => {
    let active = true;
    loadBusinessCategories((path) => apiFetch<CategoryOption[]>(path)).then((loaded) => {
      if (active) setOptions(loaded);
    });
    return () => {
      active = false;
    };
  }, []);

  const hasCurrentValue = !value || options.some((option) => option.value === value);

  return (
    <label className="form-field">
      <span>Category</span>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Select a category</option>
        {!hasCurrentValue ? <option value={value}>{value} (legacy)</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error ? <small className="field-error">{error}</small> : null}
    </label>
  );
}
