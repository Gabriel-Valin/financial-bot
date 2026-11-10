"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const MAX_SECONDS = 120;

// First format the browser can record wins (Chrome/Firefox: webm, Safari: mp4).
const CANDIDATE_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

const EXTENSIONS: Record<string, string> = {
  "audio/webm": "webm",
  "audio/mp4": "mp4",
  "audio/ogg": "ogg",
};

function pickMimeType(): string | undefined {
  return CANDIDATE_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface RecordButtonProps {
  onRecorded: (file: File) => void | Promise<void>;
  disabled?: boolean;
}

export function RecordButton({ onRecorded, disabled }: RecordButtonProps) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  };

  // Release the microphone if the component unmounts mid-recording.
  useEffect(
    () => () => {
      stopTimer();
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        recorder.stop();
        recorder.stream.getTracks().forEach((t) => t.stop());
      }
    },
    [],
  );

  const stop = () => {
    stopTimer();
    recorderRef.current?.stop();
  };

  const start = async () => {
    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices) {
      toast.error("Seu navegador não suporta gravação de áudio.");
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      toast.error(
        "Não foi possível acessar o microfone. Verifique a permissão.",
      );
      return;
    }

    const recorder = new MediaRecorder(stream, { mimeType: pickMimeType() });
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      recorderRef.current = null;
      setRecording(false);
      setSeconds(0);
      if (chunks.length === 0) return;

      const mimeType = recorder.mimeType.split(";")[0] || "audio/webm";
      const stamp = new Date().toTimeString().slice(0, 8).replaceAll(":", "");
      const file = new File(
        chunks,
        `gravacao-${stamp}.${EXTENSIONS[mimeType] ?? "webm"}`,
        { type: mimeType },
      );
      void onRecorded(file);
    };

    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
    setSeconds(0);
    const startedAt = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSeconds(elapsed);
      if (elapsed >= MAX_SECONDS) stop();
    }, 250);
  };

  return (
    <button
      type="button"
      onClick={recording ? stop : start}
      disabled={disabled && !recording}
      aria-pressed={recording}
      className={cn(
        "flex cursor-pointer items-center gap-2 text-sm text-gray-600 disabled:cursor-not-allowed disabled:opacity-50",
        recording && "text-red-600",
      )}
    >
      {recording ? (
        <>
          <Square className="size-4 animate-pulse fill-current" />
          <span className="tabular-nums">Parar {formatTime(seconds)}</span>
        </>
      ) : (
        <>
          <Mic className="size-5" />
          <span>Gravar áudio</span>
        </>
      )}
    </button>
  );
}
