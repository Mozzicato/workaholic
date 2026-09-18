"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

/**
 * Reads questions aloud with the browser's own speech synthesis.
 *
 * Nothing leaves the device: the voice is the operating system's, so there is no provider, no
 * cost and no audio anywhere but the speaker. Browsers only allow speech after the person has
 * interacted with the page, which is why the assistant starts from a button.
 */

const PREFERENCE_KEY = "workaholic.read-aloud";
const listeners = new Set<() => void>();
// Storage can be unavailable (private windows, blocked site data); the choice still holds for
// this visit.
let remembered: boolean | null = null;

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function readPreference(): boolean {
  if (remembered !== null) return remembered;
  try {
    return window.localStorage.getItem(PREFERENCE_KEY) !== "off";
  } catch {
    return true;
  }
}

function writePreference(on: boolean): void {
  remembered = on;
  try {
    window.localStorage.setItem(PREFERENCE_KEY, on ? "on" : "off");
  } catch {
    // Kept in memory above.
  }
  listeners.forEach((listener) => listener());
}

const noSubscription = () => () => {};

export function useSpeaker() {
  const supported = useSyncExternalStore(
    noSubscription,
    () => "speechSynthesis" in window,
    () => false,
  );
  const enabled = useSyncExternalStore(subscribe, readPreference, () => false);
  const [speaking, setSpeaking] = useState(false);

  const stop = useCallback(() => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const speak = useCallback(
    (text: string) => {
      if (!supported || !text.trim()) return;
      const synth = window.speechSynthesis;
      synth.cancel(); // never talk over itself
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en";
      utterance.rate = 1;
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      synth.speak(utterance);
    },
    [supported],
  );

  const setEnabled = useCallback(
    (on: boolean) => {
      writePreference(on);
      if (!on) stop();
    },
    [stop],
  );

  // Leaving the page must not leave a question being read out to an empty room.
  useEffect(() => {
    return () => {
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, []);

  return { supported, enabled: supported && enabled, speaking, speak, stop, setEnabled };
}

export type Speaker = ReturnType<typeof useSpeaker>;
