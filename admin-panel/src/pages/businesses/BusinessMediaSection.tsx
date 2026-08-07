import { useMemo, useState } from "react";
import { ApiError, apiFetch, apiUpload, apiUploadPatch } from "../../api";
import {
  formatFileSize,
  validateImageFile,
  type BusinessImage,
} from "./types";

type Props = {
  businessId: number;
  images: BusinessImage[];
  onChange: () => Promise<void>;
  onToast: (message: string, isError?: boolean) => void;
};

type PreviewState = {
  image: BusinessImage;
  width?: number;
  height?: number;
};

function imagesByRole(images: BusinessImage[], role: BusinessImage["role"]) {
  return images.filter((image) => image.role === role && image.media_status === "active");
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function BusinessMediaSection({
  businessId,
  images,
  onChange,
  onToast,
}: Props) {
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [busyImageId, setBusyImageId] = useState<number | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<BusinessImage | null>(null);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [galleryOrder, setGalleryOrder] = useState<number[]>([]);

  const cover = imagesByRole(images, "cover")[0] ?? null;
  const logo = imagesByRole(images, "logo")[0] ?? null;
  const gallery = useMemo(() => {
    const items = imagesByRole(images, "gallery");
    if (galleryOrder.length === 0) return items;
    const orderMap = new Map(galleryOrder.map((id, index) => [id, index]));
    return [...items].sort(
      (a, b) => (orderMap.get(a.id) ?? a.id) - (orderMap.get(b.id) ?? b.id)
    );
  }, [images, galleryOrder]);

  const uploadImage = async (file: File, role: BusinessImage["role"]) => {
    const validationError = validateImageFile(file);
    if (validationError) {
      onToast(validationError, true);
      return;
    }
    const formData = new FormData();
    formData.append("image", file);
    formData.append("role", role);
    setUploadProgress(0);
    try {
      await apiUpload(`/admin/businesses/${businessId}/images/`, formData, setUploadProgress);
      onToast(`${role === "gallery" ? "Gallery image" : role} uploaded.`);
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Upload failed.", true);
    } finally {
      setUploadProgress(null);
    }
  };

  const replaceImage = async (image: BusinessImage, file: File) => {
    const validationError = validateImageFile(file);
    if (validationError) {
      onToast(validationError, true);
      return;
    }
    const formData = new FormData();
    formData.append("image", file);
    setBusyImageId(image.id);
    setUploadProgress(0);
    try {
      await apiUploadPatch(
        `/admin/businesses/${businessId}/images/${image.id}/`,
        formData,
        setUploadProgress
      );
      onToast("Image replaced.");
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Replace failed.", true);
    } finally {
      setBusyImageId(null);
      setUploadProgress(null);
    }
  };

  const deleteImage = async () => {
    if (!deleteTarget) return;
    setBusyImageId(deleteTarget.id);
    try {
      await apiFetch(`/admin/businesses/${businessId}/images/${deleteTarget.id}/`, {
        method: "DELETE",
      });
      onToast("Image deleted.");
      setDeleteTarget(null);
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Delete failed.", true);
    } finally {
      setBusyImageId(null);
    }
  };

  const setRole = async (image: BusinessImage, action: "set-cover" | "set-logo") => {
    setBusyImageId(image.id);
    try {
      await apiFetch(`/admin/businesses/${businessId}/images/${image.id}/${action}/`, {
        method: "POST",
      });
      onToast(action === "set-cover" ? "Cover updated." : "Logo updated.");
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Update failed.", true);
    } finally {
      setBusyImageId(null);
    }
  };

  const persistGalleryOrder = async (order: number[]) => {
    setGalleryOrder(order);
    try {
      await apiFetch(`/admin/businesses/${businessId}/images/reorder/`, {
        method: "POST",
        body: JSON.stringify({ order }),
      });
      onToast("Gallery order saved.");
      await onChange();
    } catch (error) {
      onToast("Could not save gallery order.", true);
      await onChange();
    }
  };

  const onGalleryDrop = async (targetId: number) => {
    if (!draggingId || draggingId === targetId) return;
    const ids = gallery.map((item) => item.id);
    const fromIndex = ids.indexOf(draggingId);
    const toIndex = ids.indexOf(targetId);
    if (fromIndex < 0 || toIndex < 0) return;
    const next = [...ids];
    next.splice(fromIndex, 1);
    next.splice(toIndex, 0, draggingId);
    await persistGalleryOrder(next);
    setDraggingId(null);
  };

  return (
    <section className="panel media-panel" id="media">
      <div className="section-heading">
        <h2>Media</h2>
        <p className="muted">Manage cover, logo, and gallery images for this business.</p>
      </div>

      {uploadProgress !== null ? (
        <div className="upload-progress">
          <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }} />
          <span>{uploadProgress}%</span>
        </div>
      ) : null}

      <div className="media-role-grid">
        <RoleCard
          title="Cover image"
          description="Primary hero image shown on listings."
          image={cover}
          busy={busyImageId === cover?.id}
          onUpload={(file) => uploadImage(file, "cover")}
          onReplace={(file) => cover && replaceImage(cover, file)}
          onDelete={() => cover && setDeleteTarget(cover)}
          onView={() => cover && setPreview({ image: cover })}
          onDownload={() => cover?.image_url && window.open(cover.image_url, "_blank")}
        />
        <RoleCard
          title="Logo"
          description="Square brand mark or avatar."
          image={logo}
          busy={busyImageId === logo?.id}
          onUpload={(file) => uploadImage(file, "logo")}
          onReplace={(file) => logo && replaceImage(logo, file)}
          onDelete={() => logo && setDeleteTarget(logo)}
          onView={() => logo && setPreview({ image: logo })}
          onDownload={() => logo?.image_url && window.open(logo.image_url, "_blank")}
        />
      </div>

      <div className="gallery-section">
        <div className="gallery-header">
          <div>
            <h3>Gallery</h3>
            <p className="muted">Drag images to reorder. Thumbnails load first; click View for full preview.</p>
          </div>
          <label className="button-link secondary upload-button">
            Upload gallery image
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) uploadImage(file, "gallery");
                event.currentTarget.value = "";
              }}
            />
          </label>
        </div>

        {gallery.length === 0 ? (
          <div className="media-empty">No gallery images yet.</div>
        ) : (
          <div className="gallery-grid">
            {gallery.map((image) => (
              <article
                key={image.id}
                className={`gallery-card${draggingId === image.id ? " dragging" : ""}`}
                draggable
                onDragStart={() => setDraggingId(image.id)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => onGalleryDrop(image.id)}
              >
                <div className="gallery-thumb-wrap">
                  {image.image_url ? (
                    <img
                      src={image.image_url}
                      alt={image.filename || `Gallery ${image.id}`}
                      loading="lazy"
                      className="gallery-thumb"
                    />
                  ) : (
                    <div className="image-placeholder">No preview</div>
                  )}
                  <div className="gallery-hover-actions">
                    <button type="button" onClick={() => setPreview({ image })}>View</button>
                    <button type="button" onClick={() => setRole(image, "set-cover")}>Cover</button>
                    <button type="button" onClick={() => setRole(image, "set-logo")}>Logo</button>
                    <button type="button" onClick={() => setDeleteTarget(image)}>Delete</button>
                  </div>
                </div>
                <div className="gallery-meta">
                  <strong>{image.filename || `Image ${image.id}`}</strong>
                  <span>{formatFileSize(image.file_size)}</span>
                  <span>{formatDate(image.uploaded_at)}</span>
                </div>
                <label className="replace-link">
                  Replace
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                    hidden
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) replaceImage(image, file);
                      event.currentTarget.value = "";
                    }}
                  />
                </label>
              </article>
            ))}
          </div>
        )}
      </div>

      {preview ? (
        <div className="modal-backdrop" onClick={() => setPreview(null)}>
          <div className="modal-card media-preview-modal" onClick={(event) => event.stopPropagation()}>
            <h3>{preview.image.filename || `Image ${preview.image.id}`}</h3>
            {preview.image.image_url ? (
              <img
                src={preview.image.image_url}
                alt={preview.image.filename || "Preview"}
                className="media-preview-image"
                onLoad={(event) => {
                  const target = event.currentTarget;
                  setPreview((current) =>
                    current
                      ? {
                          ...current,
                          width: target.naturalWidth,
                          height: target.naturalHeight,
                        }
                      : current
                  );
                }}
              />
            ) : null}
            <dl className="meta-grid">
              <div><dt>Filename</dt><dd>{preview.image.filename || "—"}</dd></div>
              <div><dt>Resolution</dt><dd>{preview.width && preview.height ? `${preview.width} × ${preview.height}` : "—"}</dd></div>
              <div><dt>File size</dt><dd>{formatFileSize(preview.image.file_size)}</dd></div>
              <div><dt>Uploaded</dt><dd>{formatDate(preview.image.uploaded_at)}</dd></div>
            </dl>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setPreview(null)}>Close</button>
              {preview.image.image_url ? (
                <a className="button-link" href={preview.image.image_url} target="_blank" rel="noreferrer">
                  Download
                </a>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {deleteTarget ? (
        <div className="modal-backdrop">
          <div className="modal-card" role="dialog" aria-modal="true">
            <h3>Delete image?</h3>
            <p>
              This permanently removes <strong>{deleteTarget.filename || `image ${deleteTarget.id}`}</strong>.
            </p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setDeleteTarget(null)}>
                Cancel
              </button>
              <button type="button" className="danger" onClick={deleteImage}>
                Delete image
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function RoleCard({
  title,
  description,
  image,
  busy,
  onUpload,
  onReplace,
  onDelete,
  onView,
  onDownload,
}: {
  title: string;
  description: string;
  image: BusinessImage | null;
  busy?: boolean;
  onUpload: (file: File) => void;
  onReplace: (file: File) => void;
  onDelete: () => void;
  onView: () => void;
  onDownload: () => void;
}) {
  return (
    <div className="media-role-card">
      <div className="media-role-copy">
        <h3>{title}</h3>
        <p className="muted">{description}</p>
      </div>
      {image ? (
        <div className="media-role-preview">
          {image.image_url ? (
            <img src={image.image_url} alt={title} loading="lazy" />
          ) : (
            <div className="image-placeholder">No preview</div>
          )}
          <div className="gallery-meta">
            <strong>{image.filename || `Image ${image.id}`}</strong>
            <span>{formatFileSize(image.file_size)}</span>
            <span>{formatDate(image.uploaded_at)}</span>
          </div>
          <div className="row">
            <button type="button" onClick={onView} disabled={busy}>View</button>
            <button type="button" className="secondary" onClick={onDownload} disabled={busy}>Download</button>
            <label className="button-link secondary">
              Replace
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                hidden
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) onReplace(file);
                  event.currentTarget.value = "";
                }}
              />
            </label>
            <button type="button" className="danger" onClick={onDelete} disabled={busy}>Delete</button>
          </div>
        </div>
      ) : (
        <label className="media-dropzone">
          <span>Upload {title.toLowerCase()}</span>
          <small>PNG, JPEG, or WEBP</small>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onUpload(file);
              event.currentTarget.value = "";
            }}
          />
        </label>
      )}
    </div>
  );
}
