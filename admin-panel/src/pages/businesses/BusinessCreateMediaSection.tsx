import { useEffect, useMemo, useState } from "react";
import { validateImageFile } from "./types";

export type PendingBusinessMedia = {
  logo: File | null;
  cover: File | null;
  gallery: File[];
};

export function emptyPendingBusinessMedia(): PendingBusinessMedia {
  return { logo: null, cover: null, gallery: [] };
}

type PreviewEntry = {
  key: string;
  url: string;
  file: File;
  role: "logo" | "cover" | "gallery";
  galleryIndex?: number;
};

type Props = {
  media: PendingBusinessMedia;
  onChange: (media: PendingBusinessMedia) => void;
  error?: string;
};

export default function BusinessCreateMediaSection({ media, onChange, error }: Props) {
  const [previewUrls, setPreviewUrls] = useState<PreviewEntry[]>([]);

  const entries = useMemo(() => {
    const next: PreviewEntry[] = [];
    if (media.logo) {
      next.push({ key: "logo", url: "", file: media.logo, role: "logo" });
    }
    if (media.cover) {
      next.push({ key: "cover", url: "", file: media.cover, role: "cover" });
    }
    media.gallery.forEach((file, index) => {
      next.push({
        key: `gallery-${index}-${file.name}`,
        url: "",
        file,
        role: "gallery",
        galleryIndex: index,
      });
    });
    return next;
  }, [media]);

  useEffect(() => {
    const created = entries.map((entry) => ({
      ...entry,
      url: URL.createObjectURL(entry.file),
    }));
    setPreviewUrls(created);
    return () => {
      created.forEach((entry) => URL.revokeObjectURL(entry.url));
    };
  }, [entries]);

  const setFile = (role: "logo" | "cover", file: File | null) => {
    onChange({ ...media, [role]: file });
  };

  const addGalleryFile = (file: File) => {
    onChange({ ...media, gallery: [...media.gallery, file] });
  };

  const removeGalleryFile = (index: number) => {
    onChange({
      ...media,
      gallery: media.gallery.filter((_, currentIndex) => currentIndex !== index),
    });
  };

  const handlePick = (
    role: "logo" | "cover" | "gallery",
    fileList: FileList | null,
    onInvalid: (message: string) => void
  ) => {
    const file = fileList?.[0];
    if (!file) return;
    const validationError = validateImageFile(file);
    if (validationError) {
      onInvalid(validationError);
      return;
    }
    if (role === "gallery") {
      addGalleryFile(file);
      return;
    }
    setFile(role, file);
  };

  const logoPreview = previewUrls.find((entry) => entry.role === "logo");
  const coverPreview = previewUrls.find((entry) => entry.role === "cover");

  return (
    <section className="panel media-panel" id="create-media">
      <div className="section-heading">
        <h2>Media</h2>
        <p className="muted">
          Add logo, cover, and gallery images. They upload after the business is created.
        </p>
      </div>

      {error ? <p className="field-error">{error}</p> : null}

      <div className="media-role-grid">
        <PendingRoleCard
          title="Logo"
          description="Circular brand mark shown on business detail."
          previewUrl={logoPreview?.url}
          fileName={media.logo?.name}
          onPick={(files, onInvalid) => handlePick("logo", files, onInvalid)}
          onRemove={() => setFile("logo", null)}
        />
        <PendingRoleCard
          title="Cover image"
          description="Hero image at the top of business detail."
          previewUrl={coverPreview?.url}
          fileName={media.cover?.name}
          onPick={(files, onInvalid) => handlePick("cover", files, onInvalid)}
          onRemove={() => setFile("cover", null)}
        />
      </div>

      <div className="gallery-section">
        <div className="gallery-header">
          <div>
            <h3>Gallery</h3>
            <p className="muted">Upload multiple photos for the business gallery.</p>
          </div>
          <label className="button-link secondary upload-button">
            Add gallery photo
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  const validationError = validateImageFile(file);
                  if (validationError) {
                    event.currentTarget.setCustomValidity(validationError);
                    event.currentTarget.reportValidity();
                  } else {
                    addGalleryFile(file);
                  }
                }
                event.currentTarget.value = "";
              }}
            />
          </label>
        </div>

        {media.gallery.length === 0 ? (
          <div className="media-empty">No gallery photos selected yet.</div>
        ) : (
          <div className="gallery-grid">
            {media.gallery.map((file, index) => {
              const preview = previewUrls.find(
                (entry) => entry.role === "gallery" && entry.galleryIndex === index
              );
              return (
                <article key={`${file.name}-${index}`} className="gallery-card">
                  <div className="gallery-thumb-wrap">
                    {preview?.url ? (
                      <img
                        src={preview.url}
                        alt={file.name}
                        loading="lazy"
                        className="gallery-thumb"
                      />
                    ) : (
                      <div className="image-placeholder">No preview</div>
                    )}
                  </div>
                  <div className="gallery-meta">
                    <strong>{file.name}</strong>
                    <span>{Math.round(file.size / 1024)} KB</span>
                  </div>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => removeGalleryFile(index)}
                  >
                    Remove
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function PendingRoleCard({
  title,
  description,
  previewUrl,
  fileName,
  onPick,
  onRemove,
}: {
  title: string;
  description: string;
  previewUrl?: string;
  fileName?: string;
  onPick: (files: FileList | null, onInvalid: (message: string) => void) => void;
  onRemove: () => void;
}) {
  const [localError, setLocalError] = useState("");

  return (
    <div className="media-role-card">
      <div className="media-role-copy">
        <h3>{title}</h3>
        <p className="muted">{description}</p>
      </div>
      {previewUrl ? (
        <div className="media-role-preview">
          <img src={previewUrl} alt={title} loading="lazy" />
          <div className="gallery-meta">
            <strong>{fileName}</strong>
          </div>
          <div className="row">
            <label className="button-link secondary">
              Replace
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                hidden
                onChange={(event) => {
                  setLocalError("");
                  onPick(event.target.files, setLocalError);
                  event.currentTarget.value = "";
                }}
              />
            </label>
            <button type="button" className="danger" onClick={onRemove}>
              Remove
            </button>
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
              setLocalError("");
              onPick(event.target.files, setLocalError);
              event.currentTarget.value = "";
            }}
          />
        </label>
      )}
      {localError ? <small className="field-error">{localError}</small> : null}
    </div>
  );
}
