import type { BusinessFormValues } from "./types";
import CategorySelect from "./CategorySelect";
import OwnerUserSelect from "./OwnerUserSelect";

type FieldErrors = Record<string, string[]>;

function fieldError(errors: FieldErrors, key: string): string | undefined {
  return errors[key]?.[0];
}

type Props = {
  values: BusinessFormValues;
  errors: FieldErrors;
  onChange: (key: keyof BusinessFormValues, value: string | boolean) => void;
  includeOwner?: boolean;
  hideBusinessName?: boolean;
  hideOwner?: boolean;
  onGeocodeAddress?: () => void;
  geocoding?: boolean;
  geocodeError?: string;
};

export default function BusinessFormFields({
  values,
  errors,
  onChange,
  includeOwner = false,
  hideBusinessName = false,
  hideOwner = false,
  onGeocodeAddress,
  geocoding = false,
  geocodeError = "",
}: Props) {
  return (
    <div className="form-grid">
      {hideBusinessName ? null : (
        <label className="form-field">
          <span>Business name *</span>
          <input
            value={values.business_name}
            onChange={(e) => onChange("business_name", e.target.value)}
            required
          />
          {fieldError(errors, "business_name") ? (
            <small className="field-error">{fieldError(errors, "business_name")}</small>
          ) : null}
          {fieldError(errors, "title") ? (
            <small className="field-error">{fieldError(errors, "title")}</small>
          ) : null}
        </label>
      )}

      <CategorySelect
        value={values.category}
        onChange={(value) => onChange("category", value)}
        error={fieldError(errors, "category")}
      />

      <label className="form-field">
        <span>Status</span>
        <select
          value={values.status}
          onChange={(e) => onChange("status", e.target.value)}
        >
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="hidden">Hidden</option>
        </select>
      </label>

      {hideOwner ? null : includeOwner ? (
        <OwnerUserSelect
          value={values.owner_id || "unclaimed"}
          onChange={(ownerId) => onChange("owner_id", ownerId)}
          error={fieldError(errors, "owner_id")}
        />
      ) : (
        <OwnerUserSelect
          value={values.owner_id || "unclaimed"}
          onChange={(ownerId) => onChange("owner_id", ownerId)}
          error={fieldError(errors, "owner_id")}
        />
      )}

      <label className="form-field span-2">
        <span>Description</span>
        <textarea
          rows={4}
          value={values.description}
          onChange={(e) => onChange("description", e.target.value)}
        />
      </label>

      <label className="form-field span-2">
        <span>About</span>
        <textarea
          rows={3}
          value={values.about}
          onChange={(e) => onChange("about", e.target.value)}
        />
      </label>

      <label className="form-field span-2">
        <span>Street address (include ZIP) *</span>
        <input
          value={values.address}
          onChange={(e) => onChange("address", e.target.value)}
          required
        />
        {fieldError(errors, "address") ? (
          <small className="field-error">{fieldError(errors, "address")}</small>
        ) : null}
      </label>

      <label className="form-field">
        <span>City *</span>
        <input
          value={values.city}
          onChange={(e) => onChange("city", e.target.value)}
          required
        />
        {fieldError(errors, "city") ? (
          <small className="field-error">{fieldError(errors, "city")}</small>
        ) : null}
      </label>

      <label className="form-field">
        <span>State *</span>
        <input
          value={values.state}
          onChange={(e) => onChange("state", e.target.value)}
          required
        />
        {fieldError(errors, "state") ? (
          <small className="field-error">{fieldError(errors, "state")}</small>
        ) : null}
      </label>

      <div className="form-field span-2 geocode-row">
        <div className="geocode-fields">
          <label className="form-field">
            <span>Latitude</span>
            <input
              value={values.latitude}
              onChange={(e) => onChange("latitude", e.target.value)}
              placeholder="Optional — use geocode"
            />
          </label>
          <label className="form-field">
            <span>Longitude</span>
            <input
              value={values.longitude}
              onChange={(e) => onChange("longitude", e.target.value)}
              placeholder="Optional — use geocode"
            />
          </label>
        </div>
        {onGeocodeAddress ? (
          <button
            type="button"
            className="button-link secondary geocode-button"
            onClick={onGeocodeAddress}
            disabled={geocoding}
          >
            {geocoding ? "Geocoding…" : "Geocode address"}
          </button>
        ) : null}
        {geocodeError ? <small className="field-error">{geocodeError}</small> : null}
        {fieldError(errors, "latitude") ? (
          <small className="field-error">{fieldError(errors, "latitude")}</small>
        ) : null}
      </div>

      <label className="form-field">
        <span>Phone</span>
        <input
          value={values.phone}
          onChange={(e) => onChange("phone", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Contact email</span>
        <input
          value={values.contact_info}
          onChange={(e) => onChange("contact_info", e.target.value)}
          placeholder="Optional"
        />
        {fieldError(errors, "contact_info") ? (
          <small className="field-error">{fieldError(errors, "contact_info")}</small>
        ) : null}
      </label>

      <label className="form-field">
        <span>Website</span>
        <input
          value={values.website}
          onChange={(e) => onChange("website", e.target.value)}
        />
        {fieldError(errors, "website") ? (
          <small className="field-error">{fieldError(errors, "website")}</small>
        ) : null}
      </label>

      <label className="form-field">
        <span>Instagram</span>
        <input
          value={values.instagram}
          onChange={(e) => onChange("instagram", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Price</span>
        <input
          value={values.price}
          onChange={(e) => onChange("price", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Premium status</span>
        <select
          value={values.premium_status}
          onChange={(e) => onChange("premium_status", e.target.value)}
        >
          <option value="none">None</option>
          <option value="trial">Trial</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
          <option value="paused">Paused</option>
        </select>
      </label>

      <label className="form-field">
        <span>Premium start</span>
        <input
          type="datetime-local"
          value={values.premium_start_date}
          onChange={(e) => onChange("premium_start_date", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Premium end</span>
        <input
          type="datetime-local"
          value={values.premium_end_date}
          onChange={(e) => onChange("premium_end_date", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Display priority</span>
        <input
          type="number"
          min="0"
          value={values.display_priority}
          onChange={(e) => onChange("display_priority", e.target.value)}
        />
      </label>

      <label className="form-field checkbox-field">
        <input
          type="checkbox"
          checked={values.is_featured}
          onChange={(e) => onChange("is_featured", e.target.checked)}
        />
        <span>Featured</span>
      </label>

      <label className="form-field checkbox-field">
        <input
          type="checkbox"
          checked={values.is_sponsored}
          onChange={(e) => onChange("is_sponsored", e.target.checked)}
        />
        <span>Sponsored</span>
      </label>

      <label className="form-field checkbox-field">
        <input
          type="checkbox"
          checked={values.verified_badge}
          onChange={(e) => onChange("verified_badge", e.target.checked)}
        />
        <span>Verified badge</span>
      </label>

      <label className="form-field span-2">
        <span>Admin note</span>
        <textarea
          rows={3}
          value={values.admin_note}
          onChange={(e) => onChange("admin_note", e.target.value)}
        />
      </label>
    </div>
  );
}
