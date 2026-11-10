import { useState, useRef, useEffect, useCallback, ChangeEvent } from "react";
import { toast } from "sonner";
import { ContentBlock } from "@langchain/core/messages";
import {
  baseMimeType,
  fileToContentBlock,
  isSupportedFile,
} from "@/lib/multimodal-utils";

interface UseFileUploadOptions {
  initialBlocks?: ContentBlock.Multimodal.Data[];
}

function blockName(block: ContentBlock.Multimodal.Data): unknown {
  return block.metadata?.name ?? block.metadata?.filename;
}

function isDuplicate(file: File, blocks: ContentBlock.Multimodal.Data[]) {
  const mimeType = baseMimeType(file.type);
  return blocks.some(
    (b) => b.mimeType === mimeType && blockName(b) === file.name,
  );
}

export function useFileUpload({
  initialBlocks = [],
}: UseFileUploadOptions = {}) {
  const [contentBlocks, setContentBlocks] =
    useState<ContentBlock.Multimodal.Data[]>(initialBlocks);
  // Latest blocks for duplicate checks inside the stable addFiles callback.
  const blocksRef = useRef(contentBlocks);
  useEffect(() => {
    blocksRef.current = contentBlocks;
  }, [contentBlocks]);
  const dropRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const dragCounter = useRef(0);

  /** Validates files and adds them as content blocks (upload, drop, paste, mic). */
  const addFiles = useCallback(async (files: File[]) => {
    const invalidFiles = files.filter((file) => !isSupportedFile(file));
    const validFiles = files.filter(isSupportedFile);
    const duplicateFiles = validFiles.filter((file) =>
      isDuplicate(file, blocksRef.current),
    );
    const uniqueFiles = validFiles.filter(
      (file) => !isDuplicate(file, blocksRef.current),
    );

    if (invalidFiles.length > 0) {
      toast.error(
        "Tipo de arquivo inválido. Envie uma imagem (JPEG, PNG, GIF, WEBP), um áudio (webm, ogg, mp3, m4a, wav) ou um PDF.",
      );
    }
    if (duplicateFiles.length > 0) {
      toast.error(
        `Arquivo(s) repetido(s): ${duplicateFiles.map((f) => f.name).join(", ")}. Cada arquivo só pode ser enviado uma vez por mensagem.`,
      );
    }
    if (uniqueFiles.length === 0) return;

    const newBlocks = await Promise.all(uniqueFiles.map(fileToContentBlock));
    setContentBlocks((prev) => [...prev, ...newBlocks]);
  }, []);

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    await addFiles(Array.from(files));
    e.target.value = "";
  };

  // Drag and drop handlers
  useEffect(() => {
    if (!dropRef.current) return;

    // Global drag events with counter for robust dragOver state
    const handleWindowDragEnter = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        dragCounter.current += 1;
        setDragOver(true);
      }
    };
    const handleWindowDragLeave = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        dragCounter.current -= 1;
        if (dragCounter.current <= 0) {
          setDragOver(false);
          dragCounter.current = 0;
        }
      }
    };
    const handleWindowDrop = async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setDragOver(false);

      if (!e.dataTransfer) return;
      await addFiles(Array.from(e.dataTransfer.files));
    };
    const handleWindowDragEnd = () => {
      dragCounter.current = 0;
      setDragOver(false);
    };
    window.addEventListener("dragenter", handleWindowDragEnter);
    window.addEventListener("dragleave", handleWindowDragLeave);
    window.addEventListener("drop", handleWindowDrop);
    window.addEventListener("dragend", handleWindowDragEnd);

    // Prevent default browser behavior for dragover globally
    const handleWindowDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("dragover", handleWindowDragOver);

    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(true);
    };
    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(true);
    };
    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);
    };
    const element = dropRef.current;
    element.addEventListener("dragover", handleDragOver);
    element.addEventListener("dragenter", handleDragEnter);
    element.addEventListener("dragleave", handleDragLeave);

    return () => {
      element.removeEventListener("dragover", handleDragOver);
      element.removeEventListener("dragenter", handleDragEnter);
      element.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("dragenter", handleWindowDragEnter);
      window.removeEventListener("dragleave", handleWindowDragLeave);
      window.removeEventListener("drop", handleWindowDrop);
      window.removeEventListener("dragend", handleWindowDragEnd);
      window.removeEventListener("dragover", handleWindowDragOver);
      dragCounter.current = 0;
    };
  }, [addFiles]);

  const removeBlock = (idx: number) => {
    setContentBlocks((prev) => prev.filter((_, i) => i !== idx));
  };

  const resetBlocks = () => setContentBlocks([]);

  /**
   * Handle paste event for files (images, audio, PDFs)
   * Can be used as onPaste={handlePaste} on a textarea or input
   */
  const handlePaste = async (
    e: React.ClipboardEvent<HTMLTextAreaElement | HTMLInputElement>,
  ) => {
    const items = e.clipboardData.items;
    if (!items) return;
    const files: File[] = [];
    for (let i = 0; i < items.length; i += 1) {
      const item = items[i];
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length === 0) return;
    e.preventDefault();
    await addFiles(files);
  };

  return {
    contentBlocks,
    setContentBlocks,
    addFiles,
    handleFileUpload,
    dropRef,
    removeBlock,
    resetBlocks,
    dragOver,
    handlePaste,
  };
}
