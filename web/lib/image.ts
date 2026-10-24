const MAX_SIDE = 1600;
const MAX_PDF_BYTES = 4 * 1024 * 1024;
const RAW_OK = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);

export interface Prepared {
  blob: Blob;
  name: string;
}

/**
 * Downscale photos to ≤1600px JPEG before upload: phone photos drop from ~4 MB to
 * ~300 KB, uploads get faster, model cost drops, and anything the browser can
 * decode (including HEIC on Safari) becomes a format the API accepts.
 */
export async function prepareFile(file: File): Promise<Prepared> {
  if (file.type === "application/pdf") {
    if (file.size > MAX_PDF_BYTES) throw new Error("PDF is over 4 MB. Try a single-page export.");
    return { blob: file, name: file.name };
  }
  const looksLikeImage = file.type.startsWith("image/") || /\.(heic|heif)$/i.test(file.name);
  if (!looksLikeImage) throw new Error("Not an image or PDF.");

  let bitmap: ImageBitmap | null = null;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    bitmap = null;
  }
  if (!bitmap) {
    if (RAW_OK.has(file.type) && file.size < 5 * 1024 * 1024) return { blob: file, name: file.name };
    throw new Error("This browser can't open that image. Save it as JPG or PNG and try again.");
  }

  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Couldn't process that image.");
  ctx.fillStyle = "#fff"; // transparent PNGs → white, not black
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/jpeg", 0.85));
  if (!blob) throw new Error("Couldn't process that image.");
  return { blob, name: file.name.replace(/\.[^.]+$/, "") + ".jpg" };
}
