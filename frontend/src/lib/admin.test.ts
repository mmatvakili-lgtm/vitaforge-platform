import assert from "node:assert/strict";
import { test } from "node:test";
import { parseYouTubeId, resolveMedia } from "./admin.ts";

const base = { hasPhoto: true, video: { id: "aaaaaaaaaaa", title: "V" } };
test("no override → photo, video, 3d in that order", () => {
  const r = resolveMedia(base, undefined);
  assert.deepEqual(r.views, ["photo", "video", "3d"]); assert.equal(r.initial, "photo");
});
test("disabled kinds disappear and the default moves on", () => {
  const r = resolveMedia(base, { photo: false, anim3d: false });
  assert.deepEqual(r.views, ["video"]); assert.equal(r.initial, "video");
});
test("explicit default wins only when that view is available", () => {
  assert.equal(resolveMedia(base, { default: "3d" }).initial, "3d");
  assert.equal(resolveMedia(base, { default: "3d", anim3d: false }).initial, "photo");
});
test("replacement video and uploaded photo apply even without bundled media", () => {
  const r = resolveMedia({ hasPhoto: false, video: null }, { photo_file: "mf-00000001", video_id: "bbbbbbbbbbb" });
  assert.deepEqual(r.views, ["photo", "video", "3d"]); assert.equal(r.video?.id, "bbbbbbbbbbb"); assert.equal(r.photoFile, "mf-00000001");
});
test("everything switched off → nothing to show", () => {
  const r = resolveMedia(base, { photo: false, video: false, anim3d: false });
  assert.deepEqual(r.views, []); assert.equal(r.initial, null); assert.equal(r.video, null);
});
test("youtube id parsing", () => {
  assert.equal(parseYouTubeId("dQw4w9WgXcQ"), "dQw4w9WgXcQ");
  assert.equal(parseYouTubeId("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3"), "dQw4w9WgXcQ");
  assert.equal(parseYouTubeId("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ");
  assert.equal(parseYouTubeId("https://youtube.com/shorts/dQw4w9WgXcQ"), "dQw4w9WgXcQ");
  assert.equal(parseYouTubeId("https://evil.com/watch?v=dQw4w9WgXcQ"), null);
  assert.equal(parseYouTubeId("nope"), null);
});
