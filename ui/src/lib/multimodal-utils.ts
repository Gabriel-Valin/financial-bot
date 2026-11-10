import { ContentBlock } from "@langchain/core/messages";
import { toast } from "sonner";

export const SUPPORTED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
];

// Formats accepted by OpenAI transcription (the backend transcribes audio).
export const SUPPORTED_AUDIO_TYPES = [
  "audio/webm",
  "audio/ogg",
  "audio/mpeg",
  "audio/mp3",
  "audio/mp4",
  "audio/m4a",
  "audio/x-m4a",
  "audio/wav",
  "audio/x-wav",
];

export const SUPPORTED_FILE_TYPES = [
  ...SUPPORTED_IMAGE_TYPES,
  ...SUPPORTED_AUDIO_TYPES,
  "application/pdf",
];

// "audio/webm;codecs=opus" -> "audio/webm"
export function baseMimeType(mimeType: string): string {
  return mimeType.split(";")[0].trim().toLowerCase();
}

export function isSupportedFile(file: File): boolean {
  return SUPPORTED_FILE_TYPES.includes(baseMimeType(file.type));
}

// Returns a Promise of a typed multimodal block for images, audio or PDFs
export async function fileToContentBlock(
  file: File,
): Promise<ContentBlock.Multimodal.Data> {
  const mimeType = baseMimeType(file.type);
  if (!SUPPORTED_FILE_TYPES.includes(mimeType)) {
    toast.error(`Tipo de arquivo não suportado: ${file.type || file.name}`);
    return Promise.reject(new Error(`Unsupported file type: ${file.type}`));
  }

  const data = await fileToBase64(file);

  if (SUPPORTED_IMAGE_TYPES.includes(mimeType)) {
    return { type: "image", mimeType, data, metadata: { name: file.name } };
  }

  if (SUPPORTED_AUDIO_TYPES.includes(mimeType)) {
    return { type: "audio", mimeType, data, metadata: { name: file.name } };
  }

  // PDF
  return {
    type: "file",
    mimeType: "application/pdf",
    data,
    metadata: { filename: file.name },
  };
}

// Helper to convert File to base64 string
export async function fileToBase64(file: File): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      // Remove the data:...;base64, prefix
      resolve(result.split(",")[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Returns the block in the UI shape ({ mimeType, data }), or null if it is not
 * a base64 image/audio/PDF block. Accepts the shape this UI sends and the
 * Python LangChain shape ({ mime_type, base64 }) the backend stores.
 */
export function toBase64ContentBlock(
  block: unknown,
): ContentBlock.Multimodal.Data | null {
  if (typeof block !== "object" || block === null) return null;
  const b = block as Record<string, unknown>;
  const mime = b.mimeType ?? b.mime_type;
  const data = b.data ?? b.base64;
  if (typeof mime !== "string" || typeof data !== "string") return null;

  const mimeType = baseMimeType(mime);
  const metadata = (b.metadata as Record<string, unknown> | undefined) ?? {};
  const isImage = mimeType.startsWith("image/");
  const isAudio = mimeType.startsWith("audio/");
  const isPdf = mimeType === "application/pdf";

  if (b.type === "image" && isImage) {
    return { type: "image", mimeType, data, metadata };
  }
  if (b.type === "audio" && isAudio) {
    return { type: "audio", mimeType, data, metadata };
  }
  // "file" is the legacy type for images and PDFs
  if (b.type === "file" && (isImage || isPdf)) {
    return isImage
      ? { type: "image", mimeType, data, metadata }
      : { type: "file", mimeType, data, metadata };
  }
  return null;
}

// Type guard for Base64ContentBlock
export function isBase64ContentBlock(
  block: unknown,
): block is ContentBlock.Multimodal.Data {
  return toBase64ContentBlock(block) !== null;
}
