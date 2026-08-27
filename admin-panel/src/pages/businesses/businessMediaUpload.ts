import { apiUpload } from "../../api";
import type { PendingBusinessMedia } from "./BusinessCreateMediaSection";

export async function uploadPendingBusinessMedia(
  businessId: number,
  media: PendingBusinessMedia,
  onProgress?: (percent: number) => void
): Promise<void> {
  const uploads: Array<{ file: File; role: "logo" | "cover" | "gallery" }> = [];
  if (media.logo) uploads.push({ file: media.logo, role: "logo" });
  if (media.cover) uploads.push({ file: media.cover, role: "cover" });
  media.gallery.forEach((file) => uploads.push({ file, role: "gallery" }));

  for (let index = 0; index < uploads.length; index += 1) {
    const upload = uploads[index];
    const formData = new FormData();
    formData.append("image", upload.file);
    formData.append("role", upload.role);
    await apiUpload(
      `/admin/businesses/${businessId}/images/`,
      formData,
      onProgress
        ? (percent) => {
            const overall = Math.round(((index + percent / 100) / uploads.length) * 100);
            onProgress(overall);
          }
        : undefined
    );
  }
}
