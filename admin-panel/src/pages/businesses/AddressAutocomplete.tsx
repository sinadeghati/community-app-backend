import { useCallback, useEffect, useId, useRef, useState } from "react";
import { fetchAddressSuggestions } from "./fetchAddressSuggestions";
import {
  nominatimResultsToSuggestions,
  type ParsedAddressSelection,
} from "./nominatimAddress";

const DEBOUNCE_MS = 350;
const MIN_QUERY_LENGTH = 3;

type Props = {
  onSelect: (selection: ParsedAddressSelection) => void;
  disabled?: boolean;
};

export default function AddressAutocomplete({ onSelect, disabled = false }: Props) {
  const inputId = useId();
  const listId = `${inputId}-listbox`;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const [suggestions, setSuggestions] = useState<
    { id: string; label: string; selection: ParsedAddressSelection }[]
  >([]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const closeList = useCallback(() => {
    setOpen(false);
    setActiveIndex(-1);
  }, []);

  const runSearch = useCallback(async (value: string) => {
    abortRef.current?.abort();
    if (value.trim().length < MIN_QUERY_LENGTH) {
      setSuggestions([]);
      setLoading(false);
      setError("");
      setOpen(false);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError("");

    try {
      const results = await fetchAddressSuggestions(value, controller.signal);
      const next = nominatimResultsToSuggestions(results);
      setSuggestions(next);
      setOpen(true);
      setActiveIndex(next.length > 0 ? 0 : -1);
      if (next.length === 0) {
        setError("");
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      setSuggestions([]);
      setOpen(true);
      setActiveIndex(-1);
      setError(e instanceof Error ? e.message : "Address search failed.");
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      void runSearch(query);
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, runSearch]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        closeList();
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [closeList]);

  const pickSuggestion = (index: number) => {
    const item = suggestions[index];
    if (!item) return;
    onSelect(item.selection);
    setQuery(item.label);
    closeList();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      if (suggestions.length > 0) {
        setOpen(true);
        setActiveIndex(0);
      }
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeList();
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (suggestions.length === 0) return;
      setActiveIndex((current) => (current + 1) % suggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (suggestions.length === 0) return;
      setActiveIndex((current) =>
        current <= 0 ? suggestions.length - 1 : current - 1
      );
      return;
    }

    if (event.key === "Enter" && open && activeIndex >= 0) {
      event.preventDefault();
      pickSuggestion(activeIndex);
    }
  };

  const showNoResults =
    open && !loading && !error && query.trim().length >= MIN_QUERY_LENGTH && suggestions.length === 0;

  const panelVisible =
    open && (loading || Boolean(error) || showNoResults || suggestions.length > 0);

  return (
    <div
      className={`form-field span-2 address-autocomplete${panelVisible ? " is-open" : ""}`}
      ref={rootRef}
    >
      <label htmlFor={inputId}>
        <span>Search address</span>
      </label>
      <div className="address-autocomplete-control">
        <input
          id={inputId}
          type="search"
          role="combobox"
          aria-expanded={panelVisible}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={
            activeIndex >= 0 ? `${inputId}-option-${activeIndex}` : undefined
          }
          autoComplete="off"
          disabled={disabled}
          value={query}
          placeholder="Start typing a street address…"
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (suggestions.length > 0 || loading || error) setOpen(true);
          }}
          onKeyDown={handleKeyDown}
        />

        {panelVisible ? (
          <ul
            id={listId}
            role="listbox"
            className="address-autocomplete-list"
            aria-label="Address suggestions"
          >
            {loading ? (
              <li className="address-autocomplete-status" role="status">Searching…</li>
            ) : null}
            {error ? (
              <li className="address-autocomplete-status error" role="alert">{error}</li>
            ) : null}
            {showNoResults ? (
              <li className="address-autocomplete-status" role="status">No matching addresses.</li>
            ) : null}
            {!loading && !error
              ? suggestions.map((item, index) => (
                  <li
                    key={item.id}
                    id={`${inputId}-option-${index}`}
                    role="option"
                    aria-selected={index === activeIndex}
                    className={index === activeIndex ? "active" : undefined}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => pickSuggestion(index)}
                  >
                    {item.label}
                  </li>
                ))
              : null}
          </ul>
        ) : null}
      </div>
      <small className="muted address-autocomplete-hint">
        Select a suggestion to fill street, city, state, ZIP, and coordinates. Fields stay editable.
      </small>
    </div>
  );
}
