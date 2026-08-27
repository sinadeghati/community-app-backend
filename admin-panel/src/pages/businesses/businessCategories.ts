/**
 * Canonical Korook business categories.
 * Mirrors CREATE_BUSINESS_CATEGORIES in iranianapp-mobile/lib/discoverySearch.ts
 * and iranapp/listings/categories.py on the backend.
 */
export const BUSINESS_CATEGORIES = [
  "Food",
  "Beauty",
  "Auto",
  "Home Services",
  "Real Estate",
  "Lawyers",
  "Doctors",
  "Insurance",
  "Mortgage",
  "Home Catering",
  "Accounting",
  "Immigration",
  "Tutors",
  "Tax Services",
  "Events",
  "Professional Services",
  "Health & Wellness",
  "Education",
  "Retail",
  "Other",
] as const;

export type BusinessCategory = (typeof BUSINESS_CATEGORIES)[number];

export type CategoryOption = {
  value: string;
  label: string;
};

export function toCategoryOptions(values: readonly string[]): CategoryOption[] {
  return values.map((value) => ({ value, label: value }));
}

let cachedCategories: CategoryOption[] | null = null;

export async function loadBusinessCategories(
  fetcher: (path: string) => Promise<CategoryOption[]>
): Promise<CategoryOption[]> {
  if (cachedCategories) return cachedCategories;
  try {
    const remote = await fetcher("/listings/categories/");
    if (remote.length > 0) {
      cachedCategories = remote;
      return remote;
    }
  } catch {
    // Staging may not have the endpoint until deploy; use local canonical list.
  }
  cachedCategories = toCategoryOptions(BUSINESS_CATEGORIES);
  return cachedCategories;
}
