import { useState } from "react";
import { ApiError, apiFetch, apiUpload, apiUploadPatch } from "../../api";
import { HERO_ASPECT_NOTE, validateImageFile, type PromotionDetail } from "./types";

type Props = {
  promotionId: number;
  promotion: PromotionDetail;
  onChange: () => Promise<void>;
  onToast: (message: string, isError?: boolean) => void;
};

export default function PromotionHeroSection({ promotionId, promotion, onChange, onToast }: Props) {
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  const upload = async (file: File, replace = false) => {
    const validationError = validateImageFile(file);
    if (validationError) {
      onToast(validationError, true);
      return;
    }
    const formData = new FormData();
    formData.append("image", file);
    setUploadProgress(0);
    setBusy(true);
    try {
      if (replace) {
        await apiUploadPatch(`/admin/promotions/${promotionId}/hero-image/`, formData, setUploadProgress);
        onToast("Hero image replaced.");
      } else {
        await apiUpload(`/admin/promotions/${promotionId}/hero-image/`, formData, setUploadProgress);
        onToast("Hero image uploaded.");
      }
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Upload failed.", true);
    } finally {
      setBusy(false);
      setUploadProgress(null);
    }
  };

  const deleteImage = async () => {
    setBusy(true);
    try {
      await apiFetch(`/admin/promotions/${promotionId}/hero-image/`, { method: "DELETE" });
      onToast("Hero image deleted.");
      setDeleteOpen(false);
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Delete failed.", true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel media-panel" id="hero-media">
      <div className="section-heading">
        <h2>Hero image / media</h2>
        <p className="muted">{HERO_ASPECT_NOTE}</p>
      </div>

      {uploadProgress !== null ? (
        <div className="upload-progress">
          <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }} />
          <span>{uploadProgress}%</span>
        </div>
      ) : null}

      <div className="media-role-preview">
        {promotion.image_url ? (
          <img src={promotion.image_url} alt={promotion.title} className="media-preview-image hero-preview-wide" loading="lazy" />
        ) : (
          <label className="media-dropzone">
            <span>Upload hero image</span>
            <small className="muted">PNG, JPEG, or WEBP</small>
            <input type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" hidden onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload(file);
              e.currentTarget.value = "";
            }} />
          </label>
        )}
      </div>

      <div className="compact-meta">
        <p><strong>Filename:</strong> {promotion.image_filename || "—"}</p>
        <p><strong>Status:</strong> {promotion.status} {promotion.hero_approved ? "· Approved" : "· Not approved"}</p>
      </div>

      {promotion.image_url ? (
        <div className="inline-actions">
          <button type="button" onClick={() => setPreviewOpen(true)}>Preview</button>
          <label className="replace-link">
            Replace
            <input type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" hidden disabled={busy} onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload(file, true);
              e.currentTarget.value = "";
            }} />
          </label>
          <button type="button" onClick={() => window.open(promotion.image_url || "", "_blank")}>Download</button>
          <button type="button" className="danger" onClick={() => setDeleteOpen(true)}>Delete</button>
        </div>
      ) : null}

      {previewOpen && promotion.image_url ? (
        <div className="modal-backdrop" onClick={() => setPreviewOpen(false)}>
          <div className="modal-card media-preview-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Hero preview</h3>
            <img src={promotion.image_url} alt={promotion.title} className="media-preview-image" />
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setPreviewOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      ) : null}

      {deleteOpen ? (
        <div className="modal-backdrop">
          <div className="modal-card">
            <h3>Delete hero image?</h3>
            <p>This will remove the hero image from this promotion.</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setDeleteOpen(false)}>Cancel</button>
              <button type="button" className="danger" disabled={busy} onClick={deleteImage}>Delete image</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
