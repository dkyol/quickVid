"""Kling AI official API client.

Covers what carvegen needs: JWT auth (cached with refresh), text-to-video,
image-to-video (with optional `image_tail` end keyframe), robust status
polling, retries with backoff, and result download.

API contract (verified against Kling's docs + community references, 2026-07;
re-check https://app.klingai.com/.../document-api if something 4xxs):
  Auth : JWT HS256, payload {iss: access_key, exp: now+1800, nbf: now-5},
         header {alg: HS256, typ: JWT}; sent as `Authorization: Bearer <jwt>`.
  T2V  : POST /v1/videos/text2video
  I2V  : POST /v1/videos/image2video   (needs `image` and/or `image_tail`)
  Poll : GET  /v1/videos/{text2video|image2video}/{task_id}
         -> data.task_status in {submitted, processing, succeed, failed}
         -> data.task_result.videos[0].url   (URL expires quickly: download now)
"""

import base64
import logging
import mimetypes
import os
import time

import jwt
import requests

log = logging.getLogger(__name__)

_TOKEN_TTL = 1800          # Kling tokens live 30 min
_TOKEN_REFRESH_BUFFER = 300  # refresh 5 min early
_POLL_INTERVAL = 6         # seconds between status checks
_POLL_TIMEOUT = 900        # give up after 15 min per segment
_HTTP_RETRIES = 4          # transient-error retries per request
_BACKOFF_BASE = 2.0


class KlingError(RuntimeError):
    pass


class KlingClient:
    """Kling client with two auth modes:

      - api_key (preferred): the single key from https://kling.ai/dev, sent
        verbatim as a Bearer token. Supports the newest models.
      - access_key + secret_key (legacy): signed into a short-lived JWT.

    Pass whichever you have; api_key wins if both are given.
    """

    def __init__(self, *, api_key=None, access_key=None, secret_key=None,
                 api_base="https://api-singapore.klingai.com"):
        if not api_key and not (access_key and secret_key):
            raise KlingError("Kling api_key (or access_key+secret_key) required.")
        self._api_key = api_key
        self._ak = access_key
        self._sk = secret_key
        self.api_base = api_base.rstrip("/")
        self._token = None
        self._token_exp = 0

    @classmethod
    def from_settings(cls, settings):
        return cls(api_key=settings.api_key, access_key=settings.access_key,
                   secret_key=settings.secret_key, api_base=settings.api_base)

    # ----------------------------- auth ----------------------------------- #
    def _bearer(self):
        """The token for the Authorization header: the raw API key if we have
        one, else a freshly-minted (cached) JWT from the legacy ak/sk pair."""
        if self._api_key:
            return self._api_key
        now = int(time.time())
        if self._token and now < self._token_exp - _TOKEN_REFRESH_BUFFER:
            return self._token
        payload = {"iss": self._ak, "exp": now + _TOKEN_TTL, "nbf": now - 5}
        token = jwt.encode(payload, self._sk, algorithm="HS256",
                            headers={"alg": "HS256", "typ": "JWT"})
        self._token = token.decode() if isinstance(token, bytes) else token
        self._token_exp = now + _TOKEN_TTL
        return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self._bearer()}",
                "Content-Type": "application/json"}

    # --------------------------- http core -------------------------------- #
    def _request(self, method, path, **kw):
        """One HTTP call with retry/backoff on TRANSIENT failures only (5xx,
        genuine rate limits, network errors). Kling business errors — which it
        confusingly returns under HTTP 429 too (e.g. code 1102 'Account balance
        not enough') — fail fast, since retrying them just burns time."""
        url = f"{self.api_base}{path}"
        last = None
        for attempt in range(1, _HTTP_RETRIES + 1):
            try:
                r = requests.request(method, url, headers=self._headers(),
                                     timeout=60, **kw)
            except requests.RequestException as e:
                last = e
                wait = _BACKOFF_BASE ** attempt
                log.warning("network error (%s), retry %d/%d in %.0fs",
                            e, attempt, _HTTP_RETRIES, wait)
                time.sleep(wait)
                continue

            # Try to read Kling's {code, message, data} envelope.
            try:
                body = r.json()
            except ValueError:
                body = None
            biz_code = body.get("code") if isinstance(body, dict) else None
            biz_msg = body.get("message") if isinstance(body, dict) else r.text[:300]

            # A concrete business code (non-zero) never fixes itself on retry.
            if biz_code not in (0, None):
                raise KlingError(f"{path} -> code {biz_code}: {biz_msg}")

            # Otherwise retry only genuine transient HTTP statuses.
            if r.status_code == 429 or r.status_code >= 500:
                last = KlingError(f"{r.status_code}: {biz_msg}")
                wait = _BACKOFF_BASE ** attempt
                log.warning("transient %s, retry %d/%d in %.0fs",
                            r.status_code, attempt, _HTTP_RETRIES, wait)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise KlingError(f"{method} {path} -> {r.status_code}: {biz_msg}")
            return body
        raise KlingError(f"{method} {path} failed after {_HTTP_RETRIES} retries: {last}")

    # --------------------------- helpers ---------------------------------- #
    @staticmethod
    def _as_image_field(image):
        """Kling `image`/`image_tail` accept a public URL or base64 (no data:
        prefix). Local paths are read and base64-encoded; URLs pass through."""
        if not image:
            return None
        if image.startswith("http://") or image.startswith("https://"):
            return image
        if not os.path.isfile(image):
            raise KlingError(f"seed image not found: {image}")
        with open(image, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")

    # --------------------------- generation ------------------------------- #
    def submit_text2video(self, prompt, *, model, mode, aspect_ratio, duration,
                          cfg_scale, negative_prompt=None):
        payload = {
            "model_name": model, "prompt": prompt, "mode": mode,
            "aspect_ratio": aspect_ratio, "duration": str(duration),
            "cfg_scale": cfg_scale,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        data = self._request("POST", "/v1/videos/text2video", json=payload)["data"]
        return data["task_id"]

    def submit_image2video(self, prompt, *, model, mode, duration, cfg_scale,
                           start_image=None, end_image=None, negative_prompt=None,
                           aspect_ratio=None):
        img = self._as_image_field(start_image)
        tail = self._as_image_field(end_image)
        if not img and not tail:
            raise KlingError("image2video needs start_image and/or end_image.")
        payload = {
            "model_name": model, "prompt": prompt, "mode": mode,
            "duration": str(duration), "cfg_scale": cfg_scale,
        }
        if img:
            payload["image"] = img
        if tail:
            # NOTE: image_tail (end keyframe) is MODEL-SPECIFIC. kling-v1-6
            # supports it; kling-v2-master returns
            # "Image tail is not supported by the current model". Use a v1.x
            # model when a segment sets end_image, or drop end_image for v2.
            payload["image_tail"] = tail
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        # aspect_ratio is honored for i2v when no image pins it; harmless to send.
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        data = self._request("POST", "/v1/videos/image2video", json=payload)["data"]
        return data["task_id"]

    # ----------------------------- polling -------------------------------- #
    def wait(self, task_id, kind, *, poll=_POLL_INTERVAL, timeout=_POLL_TIMEOUT):
        """Block until the task succeeds; return the video URL. `kind` is
        'text2video' or 'image2video'."""
        path = f"/v1/videos/{kind}/{task_id}"
        waited = 0
        while waited <= timeout:
            data = self._request("GET", path)["data"]
            status = data.get("task_status")
            if status == "succeed":
                vids = data.get("task_result", {}).get("videos", [])
                if not vids:
                    raise KlingError(f"{task_id} succeeded but returned no video")
                url = vids[0]["url"]
                log.info("task %s succeeded", task_id)
                return url
            if status == "failed":
                msg = data.get("task_status_msg", "no message")
                raise KlingError(f"task {task_id} failed: {msg}")
            log.info("task %s: %s (%ds)", task_id, status, waited)
            time.sleep(poll)
            waited += poll
        raise KlingError(f"task {task_id} timed out after {timeout}s")

    def generate(self, *, prompt, model, mode, aspect_ratio, duration, cfg_scale,
                 start_image=None, end_image=None, negative_prompt=None):
        """High-level: pick t2v vs i2v, submit, wait, return video URL.
        Uses image2video whenever a start or end frame is given (preferred for
        carving — it keeps the subject anchored to a known frame)."""
        if start_image or end_image:
            tid = self.submit_image2video(
                prompt, model=model, mode=mode, duration=duration,
                cfg_scale=cfg_scale, start_image=start_image, end_image=end_image,
                negative_prompt=negative_prompt, aspect_ratio=aspect_ratio)
            return self.wait(tid, "image2video")
        tid = self.submit_text2video(
            prompt, model=model, mode=mode, aspect_ratio=aspect_ratio,
            duration=duration, cfg_scale=cfg_scale, negative_prompt=negative_prompt)
        return self.wait(tid, "text2video")

    @staticmethod
    def download(url, dst):
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(r.content)
        return dst

    def auth_check(self):
        """Cheap-ish sanity check: mint a token and hit a lightweight endpoint.
        We reuse text2video task query with a bogus id — a 200/40x with a Kling
        code proves auth works; a 401 proves it doesn't."""
        try:
            self._request("GET", "/v1/videos/text2video/auth-probe-0000")
        except KlingError as e:
            msg = str(e)
            if "401" in msg or "Unauthorized" in msg:
                raise
            # Any structured Kling error (e.g. task not found) means auth passed.
            return True
        return True
