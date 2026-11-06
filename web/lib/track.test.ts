import assert from "node:assert/strict";
import { test } from "node:test";
import { attributionFrom, fileType, referrerHost } from "./track.ts";

test("reads UTM tags from the landing URL", () => {
  assert.deepEqual(
    attributionFrom("https://shoebox.app/?utm_source=linkedin&utm_medium=social&utm_campaign=launch_post", ""),
    { utm_source: "linkedin", utm_medium: "social", utm_campaign: "launch_post" },
  );
});

test("keeps only the referrer's hostname", () => {
  assert.deepEqual(attributionFrom("https://shoebox.app/", "https://www.google.com/search?q=receipts"), {
    referrer_host: "www.google.com",
  });
});

test("referrerHost drops path and query", () => {
  assert.equal(referrerHost("https://www.Google.com/search?q=private+stuff"), "www.google.com");
  assert.equal(referrerHost(""), "");
  assert.equal(referrerHost("garbage"), "");
});

test("ignores links from Shoebox itself", () => {
  assert.deepEqual(attributionFrom("https://shoebox.app/", "https://shoebox.app/privacy"), {});
});

test("ignores blank tags and bad input", () => {
  assert.deepEqual(attributionFrom("https://shoebox.app/?utm_source=%20", "not a url"), {});
  assert.deepEqual(attributionFrom("::", "https://x.com/"), {});
});

test("caps tag length", () => {
  const long = "a".repeat(500);
  assert.equal(attributionFrom(`https://shoebox.app/?utm_campaign=${long}`, "").utm_campaign?.length, 200);
});

test("detects PDFs by type or extension", () => {
  assert.equal(fileType(new File([""], "r.pdf")), "pdf");
  assert.equal(fileType(new File([""], "r", { type: "application/pdf" })), "pdf");
  assert.equal(fileType(new File([""], "r.jpg", { type: "image/jpeg" })), "image");
});
