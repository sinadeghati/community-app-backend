import type { BusinessFormValues } from "./types";

type FieldErrors = Record<string, string[]>;

function fieldError(errors: FieldErrors, key: string): string | undefined {
  return errors[key]?.[0];
}

type Props = {
  values: BusinessFormValues;
  errors: FieldErrors;
  onChange: (key: keyof BusinessFormValues, value: string | boolean) => void;
  includeOwner?: boolean;
};

export default function BusinessFormFields({
  values,
  errors,
  onChange,
  includeOwner = false,
}: Props) {
  return (
    <div className="form-grid">
      <label className="form-field">
        <span>Title *</span>
        <input
          value={values.title}
          onChange={(e) => onChange("title", e.target.value)}
          required
        />
        {fieldError(errors, "title") ? (
          <small className="field-error">{fieldError(errors, "title")}</small>
        ) : null}
      </label>

      <label className="form-field">
        <span>Business name</span>
        <input
          value={values.business_name}
          onChange={(e) => onChange("business_name", e.target.value)}
        />
        {fieldError(errors, "business_name") ? (
          <small className="field-error">{fieldError(errors, "business_name")}</small>
        ) : null}
      </label>

      <label className="form-field">
        <span>Category</span>
        <input
          value={values.category}
          onChange={(e) => onChange("category", e.target.value)}
        />
      </label>

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

      {includeOwner ? (
        <label className="form-field">
          <span>Owner user ID *</span>
          <input
            value={values.owner_id}
            onChange={(e) => onChange("owner_id", e.target.value)}
            required
          />
          {fieldError(errors, "owner_id") ? (
            <small className="field-error">{fieldError(errors, "owner_id")}</small>
          ) : null}
        </label>
      ) : (
        <label className="form-field">
          <span>Owner user ID</span>
          <input
            value={values.owner_id}
            onChange={(e) => onChange("owner_id", e.target.value)}
            placeholder="Leave blank to keep current owner"
          />
        </label>
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
        <span>Address</span>
        <input
          value={values.address}
          onChange={(e) => onChange("address", e.target.value)}
        />
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

      <label className="form-field">
        <span>Latitude</span>
        <input
          value={values.latitude}
          onChange={(e) => onChange("latitude", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Longitude</span>
        <input
          value={values.longitude}
          onChange={(e) => onChange("longitude", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Phone</span>
        <input
          value={values.phone}
          onChange={(e) => onChange("phone", e.target.value)}
        />
      </label>

      <label className="form-field">
        <span>Contact email / info *</span>
        <input
          value={values.contact_info}
          onChange={(e) => onChange("contact_info", e.target.value)}
          required
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
