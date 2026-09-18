"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

/** Formats browsers actually produce, in the order we prefer them. */
const PREFERRED_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

export type RecorderState = "unsupported" | "idle" | "recording" | "stopping";

export type Recorder = {
  state: RecorderState;
  seconds: number;
  start: () => Promise<void>;
  stop: () => Promise<Blob | null>;
  cancel: () => void;
};

function supportedType(): string | null {
  if (typeof MediaRecorder === "undefined") return null;
  return PREFERRED_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) ?? null;
}

/** Whether this browser can record at all — read without a hydration mismatch. */
function useRecordingSupported(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => supportedType() !== null,
    () => false, // the server cannot know, and renders as though it cannot record
  );
}

/**
 * Records one answer from the microphone.
 *
 * The recording lives in memory and is handed to the caller as a blob; nothing is written to
 * disk here, and the microphone is released the moment recording stops — a page that keeps a
 * live microphone open is a page nobody should trust.
 */
export function useRecorder(maxSeconds = 180): Recorder {
  const supported = useRecordingSupported();
  const [state, setState] = useState<Exclude<RecorderState, "unsupported">>("idle");
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const release = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    recorder.current?.stream.getTracks().forEach((track) => track.stop());
    recorder.current = null;
    setSeconds(0);
  }, []);

  useEffect(() => release, [release]);

  const start = useCallback(async () => {
    const mimeType = supportedType();
    if (mimeType === null) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const instance = new MediaRecorder(stream, { mimeType });
    chunks.current = [];
    instance.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.current.push(event.data);
    };
    instance.start();
    recorder.current = instance;
    setSeconds(0);
    setState("recording");
    timer.current = setInterval(() => {
      setSeconds((current) => {
        const next = current + 1;
        // Stop at the limit rather than let the upload be rejected afterwards.
        if (next >= maxSeconds && recorder.current?.state === "recording") {
          recorder.current.stop();
        }
        return next;
      });
    }, 1000);
  }, [maxSeconds]);

  const stop = useCallback(async () => {
    const instance = recorder.current;
    if (!instance || instance.state === "inactive") {
      release();
      setState("idle");
      return null;
    }
    setState("stopping");
    const recorded = await new Promise<Blob>((resolve) => {
      instance.onstop = () => resolve(new Blob(chunks.current, { type: instance.mimeType }));
      instance.stop();
    });
    release();
    setState("idle");
    return recorded.size > 0 ? recorded : null;
  }, [release]);

  const cancel = useCallback(() => {
    const instance = recorder.current;
    if (instance && instance.state !== "inactive") {
      instance.onstop = null;
      instance.stop();
    }
    chunks.current = [];
    release();
    setState("idle");
  }, [release]);

  return { state: supported ? state : "unsupported", seconds, start, stop, cancel };
}
