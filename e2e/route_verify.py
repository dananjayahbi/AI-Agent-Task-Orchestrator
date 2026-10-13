#!/usr/bin/env python3
"""Blocked-vs-allowed route verification — MT-5.2-04 (WP-5.2).

Executes the checklist in ``infra/cloudflare/route-verification-checklist.md``
against whatever vantage points are available, and records a JSON results
document (Section 20.4 item 1 evidence):

* ``--ingress``     — structural proof: ``cloudflared tunnel ingress validate``
  plus one ``tunnel ingress rule`` probe per allowlist sample, asserting the
  first-match rule equals ``route-allowlist.md``'s ``ingress`` field
  (deny-403 / backend). Needs Docker + the pinned cloudflared image; no
  network.
* ``--lan-url``     — LAN vantage: every checklist sample is requested
  directly at the Compose backend. Section 19's "succeed on LAN" half —
  any application answer passes, only a connection failure fails.
* ``--public-url``  — public vantage through the Cloudflare edge: with no
  credentials (Access-gate hooks V1/V2) and, when
  ``CF_ACCESS_CLIENT_ID``/``CF_ACCESS_CLIENT_SECRET`` are exported, again
  with the service token (hooks V3/V4 — the sharp allow-vs-deny
  discriminator). Expectations come from the checklist's machine block.
* ``--rate-probe``  — API rate-limit hook R-API on the LAN vantage: log in
  with ``ROUTE_VERIFY_USERNAME``/``ROUTE_VERIFY_PASSWORD`` (env only, never
  committed) and POST the device budget + 1 times; the final answer must be
  the canonical ``RATE_LIMITED`` envelope. The edge-threshold hook R-EDGE is
  deliberately manual (see the checklist §4) — this script never bursts the
  public hostname.

Stdlib only (Python 3.10+), like ``e2e/sse_tunnel_stability.py``. Exit code
0 = every executed check matched its expectation (at least one check
executed; skips are recorded, never counted as passes); 1 = at least one
mismatch or nothing executed. A public run before the operator applies
``access-policy.md`` §4 is *expected* to fail — that failure is the drift
detector doing its job; the results document is what gets appended to the
checklist §5.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_MD = REPO_ROOT / "infra" / "cloudflare" / "route-verification-checklist.md"
ALLOWLIST_MD = REPO_ROOT / "infra" / "cloudflare" / "route-allowlist.md"
RATE_LIMITS_MD = REPO_ROOT / "infra" / "cloudflare" / "rate-limits.md"
COMPOSE_YAML = REPO_ROOT / "infra" / "compose" / "compose.yaml"

CHECKLIST_HEADING = "## 6. Machine-readable checklist"
ALLOWLIST_HEADING = "## 7. Machine-readable rule table"
RATE_LIMITS_HEADING = "## 6. Machine-readable coverage block"

USER_AGENT = "route-verify/1.0 (WP-5.2 checklist)"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds", sep="T").replace("+00:00", "Z")


def json_block_after(path: Path, heading: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if heading not in text:
        raise SystemExit(f"{path.name}: missing heading {heading!r}")
    tail = text.split(heading, 1)[1]
    match = re.search(r"```json\n(.*?)\n```", tail, flags=re.DOTALL)
    if not match:
        raise SystemExit(f"{path.name}: no JSON block after {heading!r}")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path.name}: JSON block is not an object")
    return payload


# --- HTTP probing -----------------------------------------------------------


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: a 3xx from the edge IS a result."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _has_django_envelope(body: bytes) -> tuple[bool, str]:
    """The Section 9.2 error envelope identifies an *application* answer."""
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeDecodeError):
        return False, ""
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        code = payload["error"].get("code")
        return True, str(code) if code else "envelope"
    return False, ""


def classify(status: int, headers: Any, body: bytes, *, vantage: str) -> str:
    """Map one HTTP answer onto the checklist's expectation vocabulary."""
    envelope, code = _has_django_envelope(body)
    if status == 429:
        if envelope and code == "RATE_LIMITED":
            return "app-response:RATE_LIMITED"
        return "app-response" if envelope else "edge-rate-limit"
    if 300 <= status < 400:
        location = str(headers.get("Location", ""))
        if "cdn-cgi" in location and "access" in location:
            return "edge-gate"
        return "redirect-other"
    if status == 403 and not envelope:
        return "edge-block"
    if vantage == "lan":
        # No Cloudflare exists on this path by construction (checklist §0):
        # any answer at all is the application answering.
        return "app-response"
    # Origin-looking answers (envelope, 2xx, 400/401/404/405/5xx without an
    # edge marker) mean the request REACHED the backend.
    return "app-response"


def matches(expected: str, observed: str) -> bool:
    if expected == "edge-gate":
        # The gate answering is what V1 proves; a non-browser challenge may
        # surface as either a redirect (3xx) or a bare 403 — both are "the
        # edge answered before origin". Deny rows expect the sharper
        # "edge-block", which only a bare 403 satisfies.
        return observed in {"edge-gate", "edge-block"}
    return expected == observed


def probe(
    base_url: str,
    sample: str,
    method: str,
    *,
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    """One request; returns observed class plus raw evidence."""
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", sample.lstrip("/"))
    verb = "GET" if method == "*" else method
    body = b"{}" if verb in {"POST", "PATCH", "PUT"} else None
    request = urllib.request.Request(url, data=body, method=verb)
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Accept", "*/*")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with _OPENER.open(request, timeout=timeout) as response:  # noqa: S310 - operator URLs
            status, hdrs, payload = response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:  # 3xx/4xx/5xx with our no-redirect handler
        status, hdrs, payload = exc.code, exc.headers, exc.read()
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"observed": "connection-error", "status": None, "envelope": "", "detail": str(exc)}
    envelope, code = _has_django_envelope(payload)
    return {
        "observed": classify(status, hdrs, payload, vantage="http"),
        "status": status,
        "envelope": code if envelope else "",
        "detail": (payload[:200].decode("utf-8", errors="replace") if payload else ""),
        "_headers": dict(hdrs),
        "_status": status,
        "_body": payload,
    }


# --- vantage runners --------------------------------------------------------


def _methods(check: dict[str, Any]) -> list[str]:
    methods = check.get("methods") or ["GET"]
    return ["GET"] if methods == ["*"] else list(methods)


def _service_token_headers() -> dict[str, str]:
    import os

    client_id = os.environ.get("CF_ACCESS_CLIENT_ID", "")
    secret = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
    if client_id and secret:
        return {"CF-Access-Client-Id": client_id, "CF-Access-Client-Secret": secret}
    return {}


def run_lan(checklist: dict[str, Any], base_url: str, timeout: float) -> list[dict[str, Any]]:
    results = []
    for row in checklist["rows"]:
        for check in row["checks"]:
            for method in _methods(check):
                answer = probe(base_url, check["sample"], method, headers={}, timeout=timeout)
                observed = answer["observed"] if answer["status"] is not None else "connection-error"
                # LAN classification: any application answer counts (§0).
                if observed != "connection-error":
                    observed = (
                        "app-response:RATE_LIMITED"
                        if answer.get("envelope") == "RATE_LIMITED"
                        else "app-response"
                    )
                expected = check["lan"]
                results.append(
                    {
                        "kind": "lan",
                        "row": row["id"],
                        "sample": check["sample"],
                        "method": method,
                        "expected": expected,
                        "observed": observed,
                        "status": "pass" if matches(expected, observed) else "fail",
                        "http_status": answer.get("status"),
                        "envelope": answer.get("envelope", ""),
                    }
                )
    return results


def run_public(
    checklist: dict[str, Any], base_url: str, timeout: float, with_token: bool
) -> list[dict[str, Any]]:
    kind = "public-service-token" if with_token else "public-no-credentials"
    headers = _service_token_headers() if with_token else {}
    results = []
    if with_token and not headers:
        return [
            {
                "kind": kind,
                "sample": None,
                "method": None,
                "expected": None,
                "observed": None,
                "status": "skip",
                "detail": "CF_ACCESS_CLIENT_ID/CF_ACCESS_CLIENT_SECRET not exported",
            }
        ]
    for row in checklist["rows"]:
        for check in row["checks"]:
            expected = (
                check["public_with_service_token"] if with_token else check["public_no_credentials"]
            )
            for method in _methods(check):
                answer = probe(base_url, check["sample"], method, headers=headers, timeout=timeout)
                observed = answer["observed"]
                results.append(
                    {
                        "kind": kind,
                        "row": row["id"],
                        "sample": check["sample"],
                        "method": method,
                        "expected": expected,
                        "observed": observed,
                        "status": "pass" if matches(expected, observed) else "fail",
                        "http_status": answer.get("status"),
                        "envelope": answer.get("envelope", ""),
                    }
                )
    return results


def run_ingress(allowlist: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    """Structural proof: cloudflared's own matcher vs the allowlist fields."""
    if shutil.which("docker") is None:
        return [
            {
                "kind": "ingress",
                "sample": None,
                "expected": None,
                "observed": None,
                "status": "skip",
                "detail": "docker not available",
            }
        ]
    compose = COMPOSE_YAML.read_text(encoding="utf-8")
    tag_match = re.search(r"ORCHESTRATOR_IMAGE_CLOUDFLARED:-([^}]+)", compose)
    image = tag_match.group(1).strip() if tag_match else "cloudflare/cloudflared:2026.10.0"
    config = str(COMPOSE_YAML.parent.parent / "cloudflare" / "ingress.yaml").replace("\\", "/")
    mount = f"{config}:/etc/cloudflared/config.yaml:ro"
    base = ["docker", "run", "--rm", "-v", mount, image, "tunnel",
            "--config", "/etc/cloudflared/config.yaml", "ingress"]

    validate = subprocess.run(  # noqa: S603 - fixed argv, local image
        [*base, "validate"], capture_output=True, text=True, timeout=timeout
    )
    results: list[dict[str, Any]] = [
        {
            "kind": "ingress",
            "sample": "validate",
            "expected": "exit 0",
            "observed": f"exit {validate.returncode}",
            "status": "pass" if validate.returncode == 0 else "fail",
            "detail": (validate.stdout + validate.stderr).strip()[:300],
        }
    ]
    hostname = "orchestrator.<owner-domain>"
    expected_service = {"deny-403": "http_status:403", "backend": "http://backend:8000"}
    for row in allowlist["rows"]:
        for entry in row["paths"]:
            probe_run = subprocess.run(  # noqa: S603 - fixed argv
                [*base, "rule", f"https://{hostname}{entry['sample']}"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = probe_run.stdout + probe_run.stderr
            service_match = re.search(r"service:\s*(\S+)", output)
            observed = service_match.group(1) if service_match else f"exit {probe_run.returncode}"
            want = expected_service[entry["ingress"]]
            results.append(
                {
                    "kind": "ingress",
                    "row": row["id"],
                    "sample": entry["sample"],
                    "expected": want,
                    "observed": observed,
                    "status": "pass" if observed == want and probe_run.returncode == 0 else "fail",
                    "detail": output.strip().splitlines()[-1][:200] if output.strip() else "",
                }
            )
    return results


def run_rate_probe(lan_url: str, rate_limits: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    """R-API: budget + 1 device posts must end in the canonical envelope."""
    import os

    username = os.environ.get("ROUTE_VERIFY_USERNAME", "")
    password = os.environ.get("ROUTE_VERIFY_PASSWORD", "")
    if not username or not password or not lan_url:
        return [
            {
                "kind": "rate-probe",
                "sample": "/api/v1/devices",
                "expected": "app-response:RATE_LIMITED",
                "observed": None,
                "status": "skip",
                "detail": "needs --lan-url and ROUTE_VERIFY_USERNAME/ROUTE_VERIFY_PASSWORD",
            }
        ]
    budget = int(rate_limits["meta"]["api_settings"]["ORCHESTRATOR_RATE_LIMIT_DEVICE_PER_MINUTE"])

    login_url = urllib.parse.urljoin(lan_url.rstrip("/") + "/", "api/v1/auth/login")
    jar = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(jar, _NoRedirect)
    login_request = urllib.request.Request(
        login_url,
        data=json.dumps({"username": username, "password": password}).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        opener.open(login_request, timeout=timeout).read()
    except urllib.error.HTTPError as exc:
        return [
            {
                "kind": "rate-probe",
                "sample": "/api/v1/auth/login",
                "expected": "200 session",
                "observed": f"HTTP {exc.code}",
                "status": "fail",
                "detail": "login failed — check ROUTE_VERIFY_USERNAME/PASSWORD",
            }
        ]

    # Session-authenticated POSTs carry Django's CSRF header (DRF
    # SessionAuthentication enforces it); anonymous probes above do not.
    csrf = next((c.value for c in jar.cookiejar if c.name == "csrftoken"), None)

    register_url = urllib.parse.urljoin(lan_url.rstrip("/") + "/", "api/v1/devices")
    last_status, last_body = None, b""
    for index in range(budget + 1):
        request = urllib.request.Request(
            register_url,
            data=json.dumps(
                {"platform": "ios", "push_token": f"route-verify-{index}-{utc_now()}"}
            ).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        if csrf:
            request.add_header("X-CSRFToken", csrf)
        try:
            with opener.open(request, timeout=timeout) as response:
                last_status, last_body = response.status, response.read()
        except urllib.error.HTTPError as exc:
            last_status, last_body = exc.code, exc.read()
        except (urllib.error.URLError, OSError) as exc:
            return [
                {
                    "kind": "rate-probe",
                    "sample": "/api/v1/devices",
                    "expected": "app-response:RATE_LIMITED",
                    "observed": "connection-error",
                    "status": "fail",
                    "detail": str(exc),
                }
            ]
    envelope, code = _has_django_envelope(last_body)
    observed = (
        "app-response:RATE_LIMITED"
        if last_status == 429 and envelope and code == "RATE_LIMITED"
        else f"app-response(status={last_status},code={code})" if envelope else f"http-{last_status}"
    )
    return [
        {
            "kind": "rate-probe",
            "sample": "/api/v1/devices",
            "expected": "app-response:RATE_LIMITED",
            "observed": observed,
            "status": "pass" if observed == "app-response:RATE_LIMITED" else "fail",
            "detail": f"{budget + 1} posts against device budget {budget}",
        }
    ]


# --- main -------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="WP-5.2 route verification checklist runner")
    parser.add_argument("--lan-url", help="LAN vantage base URL, e.g. http://127.0.0.1:8020")
    parser.add_argument("--public-url", help="public tunnel base URL, https://<hostname>")
    parser.add_argument("--ingress", action="store_true", help="run the ingress structural proof")
    parser.add_argument("--rate-probe", action="store_true", help="run the R-API LAN rate probe")
    parser.add_argument("--output", help="results JSON path (default: e2e/route_verification_results.json)")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    checklist = json_block_after(CHECKLIST_MD, CHECKLIST_HEADING)
    allowlist = json_block_after(ALLOWLIST_MD, ALLOWLIST_HEADING)
    rate_limits = json_block_after(RATE_LIMITS_MD, RATE_LIMITS_HEADING)

    checks: list[dict[str, Any]] = []
    if args.ingress:
        checks.extend(run_ingress(allowlist, args.timeout))
    if args.lan_url:
        checks.extend(run_lan(checklist, args.lan_url, args.timeout))
        if args.rate_probe:
            checks.extend(run_rate_probe(args.lan_url, rate_limits, args.timeout))
    elif args.rate_probe:
        checks.extend(run_rate_probe("", rate_limits, args.timeout))
    if args.public_url:
        checks.extend(run_public(checklist, args.public_url, args.timeout, with_token=False))
        checks.extend(run_public(checklist, args.public_url, args.timeout, with_token=True))

    executed = [c for c in checks if c["status"] != "skip"]
    failures = [c for c in checks if c["status"] == "fail"]
    summary = {
        "pass": sum(1 for c in checks if c["status"] == "pass"),
        "fail": len(failures),
        "skip": sum(1 for c in checks if c["status"] == "skip"),
        "executed": len(executed),
    }
    overall = summary["fail"] == 0 and summary["executed"] > 0

    results = {
        "recorded_at": utc_now(),
        "checklist": str(CHECKLIST_MD.relative_to(REPO_ROOT)),
        "vantages": {
            "lan": args.lan_url,
            "public": args.public_url,
            "ingress": args.ingress,
            "rate_probe": args.rate_probe,
            "service_token_headers": bool(_service_token_headers()),
        },
        "summary": summary,
        "pass": overall,
        "checks": checks,
    }
    output = Path(args.output) if args.output else REPO_ROOT / "e2e" / "route_verification_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    print(f"executed={summary['executed']} pass={summary['pass']} "
          f"fail={summary['fail']} skip={summary['skip']} -> {'PASS' if overall else 'FAIL'}")
    for failure in failures:
        print(f"  FAIL {failure['kind']} {failure.get('sample')} [{failure.get('method')}] "
              f"expected={failure['expected']} observed={failure['observed']}")
    print(f"results: {output}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
