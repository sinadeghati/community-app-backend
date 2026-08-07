import { useMemo, useState } from "react";
import { ApiError, apiFetch, apiUpload, apiUploadPatch } from "../../api";
import { formatFileSize, validateImageFile, type EventGalleryImage } from "./types";

type Props = {
  eventId: number;
  coverImageUrl: string | null;
  gallery: EventGalleryImage[];
  onChange: () => Promise<void>;
  onToast: (message: string, isError?: boolean) => void;
};

type PreviewState = {
  title: string;
  imageUrl: string;
  filename?: string;
  uploadedAt?: string;
};

export default function EventMediaSection({
  eventId,
  coverImageUrl,
  gallery,
  onChange,
  onToast,
}: Props) {
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; label: string } | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [galleryOrder, setGalleryOrder] = useState<string[]>([]);

  const orderedGallery = useMemo(() => {
    if (galleryOrder.length === 0) return gallery;
    const orderMap = new Map(galleryOrder.map((id, index) => [id, index]));
    return [...gallery].sort(
      (a, b) => (orderMap.get(a.id) ?? 999) - (orderMap.get(b.id) ?? 999)
    );
  }, [gallery, galleryOrder]);

  const uploadImage = async (file: File, role: "cover" | "gallery") => {
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
      await apiUpload(`/admin/events/${eventId}/media/`, formData, setUploadProgress);
      onToast(role === "cover" ? "Cover uploaded." : "Gallery image uploaded.");
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Upload failed.", true);
    } finally {
      setUploadProgress(null);
    }
  };

  const replaceCover = async (file: File) => {
    const validationError = validateImageFile(file);
    if (validationError) {
      onToast(validationError, true);
      return;
    }
    const formData = new FormData();
    formData.append("image", file);
    setBusyId("cover");
    setUploadProgress(0);
    try {
      await apiUploadPatch(`/admin/events/${eventId}/media/cover/`, formData, setUploadProgress);
      onToast("Cover replaced.");
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Replace failed.", true);
    } finally {
      setBusyId(null);
      setUploadProgress(null);
    }
  };

  const replaceGallery = async (image: EventGalleryImage, file: File) => {
    const validationError = validateImageFile(file);
    if (validationError) {
      onToast(validationError, true);
      return;
    }
    const formData = new FormData();
    formData.append("image", file);
    setBusyId(image.id);
    setUploadProgress(0);
    try {
      await apiUploadPatch(`/admin/events/${eventId}/media/${image.id}/`, formData, setUploadProgress);
      onToast("Image replaced.");
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Replace failed.", true);
    } finally {
      setBusyId(null);
      setUploadProgress(null);
    }
  };

  const deleteImage = async () => {
    if (!deleteTarget) return;
    setBusyId(deleteTarget.id);
    try {
      await apiFetch(`/admin/events/${eventId}/media/${deleteTarget.id}/`, { method: "DELETE" });
      onToast("Image deleted.");
      setDeleteTarget(null);
      await onChange();
    } catch (error) {
      onToast(error instanceof ApiError ? error.message : "Delete failed.", true);
    } finally {
      setBusyId(null);
    }
  };

  const persistGalleryOrder = async (order: string[]) => {
    setGalleryOrder(order);
    try {
      await apiFetch(`/admin/events/${eventId}/media/reorder/`, {
        method: "POST",
        body: JSON.stringify({ order }),
      });
      onToast("Gallery order saved.");
      await onChange();
    } catch {
      onToast("Could not save gallery order.", true);
      await onChange();
    }
  };

  const onGalleryDrop = async (targetId: string) => {
    if (!draggingId || draggingId === targetId) return;
    const ids = orderedGallery.map((item) => item.id);
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
        <p className="muted">Manage cover image and gallery photos for this event.</p>
      </div>

      {uploadProgress !== null ? (
        <div className="upload-progress">
          <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }} />
          <span>{uploadProgress}%</span>
        </div>
      ) : null}

      <div className="media-role-grid">
        <article className="media-role-card">
          <h3>Cover image</h3>
          <p className="muted">Primary image shown in listings and previews.</p>
          <div className="media-role-preview">
            {coverImageUrl ? (
              <img src={coverImageUrl} alt="Event cover" className="media-preview-image" loading="lazy" />
            ) : (
              <label className="media-dropzone">
                <span>Upload cover image</span>
                <small className="muted">PNG, JPEG, or WEBP</small>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                  hidden
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) uploadImage(file, "cover");
                    e.currentTarget.value = "";
                  }}
                />
              </label>
            )}
          </div>
          {coverImageUrl ? (
            <div className="inline-actions">
              <button type="button" onClick={() => setPreview({ title: "Cover image", imageUrl: coverImageUrl })}>View</button>
              <label className="replace-link">
                Replace
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                  hidden
                  disabled={busyId === "cover"}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) replaceCover(file);
                    e.currentTarget.value = "";
                  }}
                />
              </label>
              <button type="button" onClick={() => setDeleteTarget({ id: "cover", label: "cover image" })}>Delete</button>
              <button type="button" onClick={() => window.open(coverImageUrl, "_blank")}>Download</button>
            </div>
          ) : null}
        </article>
      </div>

      <div className="gallery-section">
        <div className="gallery-header">
          <div>
            <h3>Gallery</h3>
            <p className="muted">Drag images to reorder. Thumbnails lazy-load until preview.</p>
          </div>
          <label className="button-link secondary upload-button">
            Upload gallery image
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) uploadImage(file, "gallery");
                e.currentTarget.value = "";
              }}
            />
          </label>
        </div>

        {orderedGallery.length === 0 ? (
          <div className="media-empty">No gallery images yet.</div>
        ) : (
          <div className="gallery-grid">
            {orderedGallery.map((image) => (
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
                    <img src={image.image_url} alt={image.filename || image.id} loading="lazy" className="gallery-thumb" />
                  ) : (
                    <div className="image-placeholder">No preview</div>
                  )}
                  <div className="gallery-hover-actions">
                    <button
                      type="button"
                      onClick={() =>
                        setPreview({
                          title: image.filename || "Gallery image",
                          imageUrl: image.image_url || "",
                          filename: image.filename,
                          uploadedAt: image.uploaded_at,
                        })
                      }
                    >
                      View
                    </button>
                    <button type="button" onClick={() => setDeleteTarget({ id: image.id, label: image.filename || "image" })}>
                      Delete
                    </button>
                  </div>
                </div>
                <div className="gallery-meta">
                  <strong>{image.filename || image.id}</strong>
                  <span>{image.uploaded_at ? new Date(image.uploaded_at).toLocaleString() : "—"}</span>
                </div>
                <label className="replace-link">
                  Replace
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                    hidden
                    disabled={busyId === image.id}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) replaceGallery(image, file);
                      e.currentTarget.value = "";
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
          <div className="modal-card media-preview-modal" onClick={(e) => e.stopPropagation()}>
            <h3>{preview.title}</h3>
            <img src={preview.imageUrl} alt={preview.title} className="media-preview-image" />
            <div className="compact-meta">
              {preview.filename ? <p><strong>Filename:</strong> {preview.filename}</p> : null}
              {preview.uploadedAt ? <p><strong>Uploaded:</strong> {new Date(preview.uploadedAt).toLocaleString()}</p> : null}
            </div>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setPreview(null)}>Close</button>
            </div>
          </div>
        </div>
      ) : null}

      {deleteTarget ? (
        <div className="modal-backdrop">
          <div className="modal-card">
            <h3>Delete image?</h3>
            <p>This will permanently remove the {deleteTarget.label}.</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setDeleteTarget(null)}>Cancel</button>
              <button type="button" className="danger" onClick={deleteImage}>Delete</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
