"use client";

import { useEffect, useRef } from "react";
import { trackVisit } from "@/lib/track";

/** Sends one visit event per page load, from whichever page the visitor lands on. */
export default function TrackVisit() {
  const sent = useRef(false);
  useEffect(() => {
    // React's development double-invoke would otherwise send two visits.
    if (sent.current) return;
    sent.current = true;
    trackVisit();
  }, []);
  return null;
}
