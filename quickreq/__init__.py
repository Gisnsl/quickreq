
from __future__ import annotations

import base64
import json as _json
import mimetypes
import os
import random
import shutil
import subprocess
import tempfile
import time
from http.cookies import SimpleCookie
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

__all__ = [
    "Client",
    "Session",
    "Response",
    "CookieJar",
    "RequestError",
    "CurlError",
    "NetworkError",
    "DNSResolutionError",
    "DNSDropError",
    "RequestTimeoutError",
    "TLSError",
    "HTTPStatusError",
    "JSONDecodeError",
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
    "request",
    "build_client",
    "is_json_response",
    "text",
    "json",
    "cookies",
    "status",
    "headers",
    "content",
    "ok",
]

JSONDecodeError = _json.JSONDecodeError
_MISSING = object()


class RequestError(Exception):
    """Base error for quickreq."""


class CurlError(RequestError):
    """Curl returned a non-zero exit status or an unknown failure."""


class NetworkError(CurlError):
    """Generic connection or transport failure."""


class DNSResolutionError(NetworkError):
    """DNS resolution failed."""


class DNSDropError(DNSResolutionError):
    """Alias for DNS resolution failures."""


class RequestTimeoutError(NetworkError):
    """Request timed out."""


class TLSError(NetworkError):
    """TLS / certificate / handshake failure."""


class HTTPStatusError(RequestError):
    """Raised by Response.raise_for_status()."""

    def __init__(self, response: "Response", message: Optional[str] = None) -> None:
        self.response = response
        super().__init__(message or f"HTTP {response.status_code} {response.reason}".strip())


def _now() -> float:
    return time.perf_counter()


def _sanitize_text(value: Any, what: str) -> str:
    s = str(value)
    if "\x00" in s or "\r" in s or "\n" in s:
        raise ValueError(f"{what} contains control characters")
    return s


def _normalize_headers(headers: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not headers:
        return out
    for k, v in headers.items():
        if v is None:
            continue
        out[_sanitize_text(k, "header name")] = _sanitize_text(v, "header value")
    return out


def _header_exists(headers: Mapping[str, str], name: str) -> bool:
    target = name.lower()
    return any(k.lower() == target for k in headers.keys())


def _set_header(headers: Dict[str, str], name: str, value: Any) -> None:
    target = name.lower()
    for key in list(headers.keys()):
        if key.lower() == target:
            del headers[key]
    headers[_sanitize_text(name, "header name")] = _sanitize_text(value, "header value")


def _merge_url_params(url: str, params: Optional[Mapping[str, Any]]) -> str:
    if not params:
        return url
    parts = urlsplit(url)
    existing = parse_qsl(parts.query, keep_blank_values=True)
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                existing.append((_sanitize_text(key, "query param name"), str(item)))
        else:
            existing.append((_sanitize_text(key, "query param name"), str(value)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(existing, doseq=True), parts.fragment))


def _build_cookie_header(cookies: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not cookies:
        return None
    parts: List[str] = []
    for k, v in cookies.items():
        if v is None:
            continue
        parts.append(f"{_sanitize_text(k, 'cookie name')}={_sanitize_text(v, 'cookie value')}")
    return "; ".join(parts) if parts else None


def _guess_mime(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def _is_path_like(value: Any) -> bool:
    return isinstance(value, (str, os.PathLike))


def _make_temp_file(data: bytes) -> str:
    fd, path = tempfile.mkstemp(prefix="quickreq-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path
    except Exception:
        try:
            os.unlink(path)
        except Exception:
            pass
        raise


def _cleanup_paths(paths: Sequence[str]) -> None:
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.unlink(p)
        except Exception:
            pass


def _find_curl_binary() -> str:
    return shutil.which("curl") or "curl"


def _normalize_tls_version(tls_version: Optional[str]) -> Optional[str]:
    if tls_version is None:
        return None
    tv = str(tls_version).strip()
    if tv in {"1.0", "1.1", "1.2", "1.3"}:
        return tv
    raise ValueError("tls_version must be one of: '1.0', '1.1', '1.2', '1.3' or None")


def _curl_tls_args(tls_version: Optional[str]) -> List[str]:
    tv = _normalize_tls_version(tls_version)
    if tv is None:
        return []
    return {
        "1.0": ["--tlsv1.0"],
        "1.1": ["--tlsv1.1"],
        "1.2": ["--tlsv1.2"],
        "1.3": ["--tlsv1.3"],
    }[tv]


def _resolve_protocol(
    http1: Optional[bool],
    http2: Optional[bool],
    http3: Optional[bool],
    *,
    default_http1: bool = True,
) -> Tuple[bool, bool, bool]:
    selected = [name for name, value in (("http1", http1), ("http2", http2), ("http3", http3)) if value is True]
    if len(selected) > 1:
        raise ValueError("Choose only one of http1=True, http2=True, http3=True")
    if selected:
        return selected[0] == "http1", selected[0] == "http2", selected[0] == "http3"
    return bool(default_http1), False, False


def _normalize_timeout(timeout: Any) -> Tuple[Optional[float], Optional[float]]:
    if timeout is None:
        return None, None
    if isinstance(timeout, (tuple, list)):
        if len(timeout) != 2:
            raise ValueError("timeout tuple/list must be (connect_timeout, total_timeout)")
        return (
            None if timeout[0] is None else float(timeout[0]),
            None if timeout[1] is None else float(timeout[1]),
        )
    return None, float(timeout)


def _pick_proxy(proxies: Mapping[str, str]) -> Optional[str]:
    for key in ("https", "http", "all", "proxy"):
        value = proxies.get(key)
        if value:
            return _sanitize_text(value, "proxy url")
    return None


def _encode_form_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _build_form_part(field: str, value: Any) -> Tuple[str, List[str]]:
    field = _sanitize_text(field, "form field")
    temp_paths: List[str] = []

    if isinstance(value, (tuple, list)):
        if len(value) not in {2, 3}:
            raise ValueError("files tuple must be (filename, content) or (filename, content, mime)")
        filename = _sanitize_text(value[0], "filename")
        content = value[1]
        mime = _sanitize_text(value[2], "mime type") if len(value) == 3 else _guess_mime(filename)

        if isinstance(content, (bytes, bytearray, memoryview)):
            path = _make_temp_file(bytes(content))
            temp_paths.append(path)
            return f"{field}=@{path};filename={filename};type={mime}", temp_paths
        if _is_path_like(content):
            return f"{field}=@{os.fspath(content)};filename={filename};type={mime}", temp_paths

        path = _make_temp_file(_encode_form_value(content).encode("utf-8"))
        temp_paths.append(path)
        return f"{field}=@{path};filename={filename};type={mime}", temp_paths

    if isinstance(value, (bytes, bytearray, memoryview)):
        path = _make_temp_file(bytes(value))
        temp_paths.append(path)
        return f"{field}=@{path}", temp_paths
    if _is_path_like(value):
        return f"{field}=@{os.fspath(value)}", temp_paths
    return f"{field}={_encode_form_value(value)}", temp_paths


def _build_multipart_args(data: Any = None, files: Optional[Mapping[str, Any]] = None) -> Tuple[List[str], List[str]]:
    args: List[str] = []
    temp_paths: List[str] = []

    if data is not None:
        if isinstance(data, Mapping):
            iterable = data.items()
        elif isinstance(data, (list, tuple)) and all(isinstance(x, tuple) and len(x) == 2 for x in data):
            iterable = data
        else:
            raise ValueError("When sending multipart data, 'data' must be a mapping or sequence of pairs.")
        for key, value in iterable:
            part, paths = _build_form_part(key, value)
            args.extend(["-F", part])
            temp_paths.extend(paths)

    if files:
        for field, filevalue in files.items():
            part, paths = _build_form_part(field, filevalue)
            args.extend(["-F", part])
            temp_paths.extend(paths)

    return args, temp_paths



def _iter_body_chunks(source: Any, chunk_size: int = 65536) -> Iterator[bytes]:
    if source is None:
        return
    if isinstance(source, memoryview):
        yield source.tobytes()
        return
    if isinstance(source, bytes):
        yield source
        return
    if isinstance(source, bytearray):
        yield bytes(source)
        return
    if isinstance(source, str):
        yield source.encode("utf-8")
        return
    if _is_path_like(source) and os.path.exists(os.fspath(source)):
        with open(os.fspath(source), "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        return
    read = getattr(source, "read", None)
    if callable(read):
        while True:
            chunk = read(chunk_size)
            if not chunk:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            elif isinstance(chunk, memoryview):
                chunk = chunk.tobytes()
            elif isinstance(chunk, bytearray):
                chunk = bytes(chunk)
            elif not isinstance(chunk, bytes):
                chunk = str(chunk).encode("utf-8")
            yield chunk
        return
    if hasattr(source, "__iter__"):
        for chunk in source:
            if chunk is None:
                continue
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            elif isinstance(chunk, memoryview):
                chunk = chunk.tobytes()
            elif isinstance(chunk, bytearray):
                chunk = bytes(chunk)
            elif not isinstance(chunk, bytes):
                chunk = str(chunk).encode("utf-8")
            yield chunk
        return
    yield str(source).encode("utf-8")


def _write_body_to_temp_file(source: Any) -> str:
    fd, path = tempfile.mkstemp(prefix="quickreq-body-")
    try:
        with os.fdopen(fd, "wb") as f:
            for chunk in _iter_body_chunks(source):
                f.write(chunk)
        return path
    except Exception:
        try:
            os.unlink(path)
        except Exception:
            pass
        raise

def _encode_body(
    data: Any = None,
    json_data: Any = None,
    files: Optional[Mapping[str, Any]] = None,
) -> Tuple[Optional[Union[bytes, str]], List[str], List[str]]:
    extra_args: List[str] = []
    temp_paths: List[str] = []

    if json_data is not None:
        if files:
            raise ValueError("json and files cannot be used together")
        if data is not None:
            raise ValueError("json and data cannot be used together")
        body = _json.dumps(json_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        extra_args += ["-H", "Content-Type: application/json; charset=utf-8"]
        return body, extra_args, temp_paths

    if files:
        fargs, ftemps = _build_multipart_args(data=data, files=files)
        extra_args.extend(fargs)
        temp_paths.extend(ftemps)
        return None, extra_args, temp_paths

    if data is None:
        return None, extra_args, temp_paths

    if isinstance(data, Mapping):
        body = urlencode([(k, v) for k, v in data.items()], doseq=True).encode("utf-8")
        extra_args += ["-H", "Content-Type: application/x-www-form-urlencoded"]
        return body, extra_args, temp_paths

    if isinstance(data, (list, tuple)) and all(isinstance(x, tuple) and len(x) == 2 for x in data):
        body = urlencode(data, doseq=True).encode("utf-8")
        extra_args += ["-H", "Content-Type: application/x-www-form-urlencoded"]
        return body, extra_args, temp_paths

    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data), extra_args, temp_paths

    if isinstance(data, str):
        return data.encode("utf-8"), extra_args, temp_paths

    if _is_path_like(data) and os.path.exists(os.fspath(data)):
        temp_path = _write_body_to_temp_file(data)
        temp_paths.append(temp_path)
        return temp_path, extra_args, temp_paths

    if hasattr(data, "read") or (hasattr(data, "__iter__") and not isinstance(data, (dict, list, tuple, set))):
        temp_path = _write_body_to_temp_file(data)
        temp_paths.append(temp_path)
        return temp_path, extra_args, temp_paths

    return str(data).encode("utf-8"), extra_args, temp_paths
def _parse_header_blocks(header_blob: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, str], List[Tuple[str, str]], int, str]:
    text = header_blob.decode("iso-8859-1", errors="replace")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = [c for c in normalized.split("\n\n") if c.strip()]

    blocks: List[Dict[str, Any]] = []
    for chunk in chunks:
        lines = [ln for ln in chunk.split("\n") if ln.strip()]
        if not lines:
            continue
        start_index = next((i for i, ln in enumerate(lines) if ln.startswith("HTTP/")), None)
        if start_index is None:
            continue

        status_line = lines[start_index]
        pieces = status_line.split(" ", 2)
        try:
            status_code = int(pieces[1]) if len(pieces) > 1 else 0
        except ValueError:
            status_code = 0
        reason = pieces[2] if len(pieces) > 2 else ""

        raw_headers: List[Tuple[str, str]] = []
        for line in lines[start_index + 1 :]:
            if ":" in line:
                k, v = line.split(":", 1)
                raw_headers.append((k.strip(), v.strip()))

        headers: Dict[str, str] = {}
        for k, v in raw_headers:
            headers[k.lower()] = v

        blocks.append({"status_code": status_code, "reason": reason, "headers": headers, "raw_headers": raw_headers})

    if not blocks:
        return [], {}, [], 0, ""

    final = blocks[-1]
    return blocks, final["headers"], final["raw_headers"], final["status_code"], final["reason"]


def _parse_set_cookies(raw_headers: Sequence[Tuple[str, str]], jar: Optional["CookieJar"] = None) -> "CookieJar":
    jar = jar or CookieJar()
    for k, v in raw_headers:
        if k.lower() != "set-cookie":
            continue
        c = SimpleCookie()
        try:
            c.load(v)
            for name, morsel in c.items():
                jar[name] = morsel.value
        except Exception:
            first = v.split(";", 1)[0]
            if "=" in first:
                name, value = first.split("=", 1)
                jar[name.strip()] = value.strip()
    return jar


def _verify_args(verify: Union[bool, str, None], tls_insecure: bool) -> List[str]:
    if tls_insecure or verify is False:
        return ["-k"]
    if isinstance(verify, str) and verify:
        return ["--cacert", _sanitize_text(verify, "CA bundle path")]
    return []


def _build_auth_header(auth: Any) -> Optional[str]:
    if auth is None:
        return None

    if isinstance(auth, (tuple, list)):
        if len(auth) != 2:
            raise ValueError("auth tuple/list must be (username, password)")
        user = _sanitize_text(auth[0], "auth username")
        password = _sanitize_text(auth[1], "auth password")
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    if isinstance(auth, str):
        s = auth.strip()
        if not s:
            return None
        low = s.lower()
        if low.startswith("basic ") or low.startswith("bearer "):
            return s
        if low.startswith("token "):
            return "Bearer " + s[6:].strip()
        return "Bearer " + s

    return str(auth)


def _classify_curl_error(stderr: str, returncode: int) -> RequestError:
    low = (stderr or "").lower()

    if "could not resolve host" in low or "failed to resolve" in low or "name or service not known" in low:
        return DNSDropError(stderr or "DNS resolution failed")
    if "couldn't connect to server" in low or "failed to connect" in low or "connection refused" in low:
        return NetworkError(stderr or "Network connection failed")
    if "empty reply from server" in low or "connection reset by peer" in low or "connection aborted" in low:
        return NetworkError(stderr or "Connection closed unexpectedly")
    if "timed out" in low or "operation timed out" in low or "timeout was reached" in low:
        return RequestTimeoutError(stderr or "Request timed out")
    if "ssl certificate problem" in low or "certificate" in low or "tls" in low or "handshake" in low:
        return TLSError(stderr or "TLS failure")

    code_map = {
        3: RequestError("URL rejected: No host part in the URL"),
        5: NetworkError("Could not resolve proxy"),
        6: DNSDropError("Could not resolve host"),
        7: NetworkError("Failed to connect to host"),
        22: CurlError(stderr or "HTTP response error"),
        28: RequestTimeoutError("Operation timed out"),
        35: TLSError("SSL connect error"),
        51: TLSError("Peer's SSL certificate or SSH remote key was not OK"),
        56: NetworkError("Failure in receiving network data"),
        60: TLSError("SSL certificate problem"),
        77: TLSError("Problem with the SSL CA cert"),
        90: TLSError("SSL server certificate validation error"),
    }
    err = code_map.get(returncode)
    if err is not None:
        return err

    if returncode != 0:
        return CurlError(stderr or f"curl failed with code {returncode}")

    return CurlError(stderr or "curl request failed")


def _retry_after_seconds(headers: Mapping[str, str]) -> float:
    value = headers.get("retry-after")
    if not value:
        return 0.0
    value = value.strip()
    try:
        return max(0.0, float(int(value)))
    except Exception:
        return 0.0


def _is_retryable_error(err: RequestError) -> bool:
    return isinstance(err, (NetworkError, RequestTimeoutError, CurlError)) and not isinstance(err, (DNSResolutionError, TLSError))


class CookieJar:
    def __init__(self, cookies: Optional[Mapping[str, Any]] = None) -> None:
        self._cookies: Dict[str, str] = {}
        if cookies:
            self.update(cookies)

    def get_dict(self) -> Dict[str, str]:
        return dict(self._cookies)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._cookies.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._cookies[_sanitize_text(key, "cookie name")] = _sanitize_text(value, "cookie value")

    def update(self, other: Mapping[str, Any]) -> None:
        for k, v in other.items():
            if v is None:
                continue
            self._cookies[_sanitize_text(k, "cookie name")] = _sanitize_text(v, "cookie value")

    def clear(self) -> None:
        self._cookies.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._cookies

    def __getitem__(self, key: str) -> str:
        return self._cookies[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __iter__(self) -> Iterator[str]:
        return iter(self._cookies)

    def items(self):
        return self._cookies.items()

    def keys(self):
        return self._cookies.keys()

    def values(self):
        return self._cookies.values()

    def __len__(self) -> int:
        return len(self._cookies)

    def __repr__(self) -> str:
        return f"CookieJar({self._cookies!r})"


class Response:
    def __init__(
        self,
        status_code: int,
        url: str,
        headers: Dict[str, str],
        raw_headers: List[Tuple[str, str]],
        content: Optional[bytes],
        cookies: CookieJar,
        elapsed: float,
        reason: str = "",
        history: Optional[List["Response"]] = None,
        stderr: str = "",
        effective_url: str = "",
        http_version: str = "",
        redirect_count: int = 0,
        request_cmd: Optional[List[str]] = None,
        body_path: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.headers = headers
        self.raw_headers = raw_headers
        self.cookies = cookies
        self.elapsed = elapsed
        self.reason = reason
        self.history = history or []
        self.stderr = stderr
        self.effective_url = effective_url
        self.http_version = http_version
        self.redirect_count = redirect_count
        self.request_cmd = request_cmd
        self._content = content
        self._body_path = body_path

    def close(self) -> None:
        if self._body_path and os.path.exists(self._body_path):
            try:
                os.unlink(self._body_path)
            except Exception:
                pass
        self._body_path = None

    def __del__(self) -> None:
        self.close()

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "")

    @property
    def is_json(self) -> bool:
        ctype = self.content_type.lower()
        return "application/json" in ctype or ctype.endswith("+json") or "+json;" in ctype

    @property
    def encoding(self) -> str:
        ctype = self.content_type
        if "charset=" in ctype:
            enc = ctype.split("charset=", 1)[1].split(";")[0].strip().strip('"').strip("'")
            if enc:
                return enc
        return "utf-8"

    @property
    def content(self) -> bytes:
        if self._content is None:
            if self._body_path and os.path.exists(self._body_path):
                with open(self._body_path, "rb") as f:
                    self._content = f.read()
            else:
                self._content = b""
        return self._content

    @property
    def text(self) -> str:
        try:
            return self.content.decode(self.encoding, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")

    @property
    def lines(self) -> List[str]:
        return self.text.splitlines()

    def json(self, default: Any = _MISSING) -> Any:
        if not self.is_json:
            if default is not _MISSING:
                return default
            raise RequestError(f"Response is not JSON (content-type: {self.content_type or 'unknown'})")
        try:
            return _json.loads(self.text)
        except _json.JSONDecodeError as e:
            if default is not _MISSING:
                return default
            raise RequestError(f"Invalid JSON response: {e}") from e

    def iter_lines(self) -> Iterator[str]:
        yield from self.lines

    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if self._body_path and os.path.exists(self._body_path):
            with open(self._body_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            return
        data = self.content
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        target = name.lower()
        for k, v in self.headers.items():
            if k.lower() == target:
                return v
        return default

    def raise_for_status(self) -> None:
        if not self.ok:
            raise HTTPStatusError(self)

    def save(self, path: str) -> str:
        if self._body_path and os.path.exists(self._body_path):
            with open(self._body_path, "rb") as src, open(path, "wb") as dst:
                while True:
                    chunk = src.read(8192)
                    if not chunk:
                        break
                    dst.write(chunk)
        else:
            with open(path, "wb") as f:
                f.write(self.content)
        return path

    def __repr__(self) -> str:
        return f"<Response [{self.status_code}]>"


class Client:
    def __init__(
        self,
        http1: Optional[bool] = None,
        http2: Optional[bool] = None,
        http3: Optional[bool] = None,
        timeout: Optional[Union[float, Tuple[Optional[float], Optional[float]]]] = 30,
        connect_timeout: Optional[float] = None,
        follow_redirects: bool = False,
        verify: Union[bool, str] = True,
        tls_version: Optional[str] = None,
        tls_insecure: bool = False,
        cookies: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        user_agent: Optional[str] = None,
        proxies: Optional[Mapping[str, str]] = None,
        max_retries: int = 0,
        retry_statuses: Optional[Sequence[int]] = None,
        retry_backoff_factor: float = 0.5,
        retry_max_delay: float = 10.0,
        debug: bool = False,
        curl_path: Optional[str] = None,
    ) -> None:
        self.http1, self.http2, self.http3 = _resolve_protocol(http1, http2, http3, default_http1=True)
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.follow_redirects = follow_redirects
        self.verify = verify
        self.tls_version = _normalize_tls_version(tls_version)
        self.tls_insecure = tls_insecure
        self.cookies = CookieJar(cookies)
        self.headers = _normalize_headers(headers)
        self.user_agent = user_agent
        self.proxies = dict(proxies or {})
        self.max_retries = max(0, int(max_retries))
        self.retry_statuses = set(retry_statuses or {429, 500, 502, 503, 504})
        self.retry_backoff_factor = float(retry_backoff_factor)
        self.retry_max_delay = float(retry_max_delay)
        self.debug = debug
        self.curl_path = curl_path or _find_curl_binary()

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        return self._request(method, url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self._request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self._request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self._request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self._request("PATCH", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> Response:
        return self._request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs: Any) -> Response:
        return self._request("OPTIONS", url, **kwargs)

    def _sleep_backoff(self, attempt: int, retry_after: float = 0.0) -> None:
        base = self.retry_backoff_factor * (2 ** attempt)
        delay = max(retry_after, min(self.retry_max_delay, base))
        if delay > 0:
            time.sleep(delay + random.uniform(0.0, min(0.25, delay * 0.1)))

    def _raise_curl_error(self, stderr_text: str, returncode: int) -> None:
        raise _classify_curl_error(stderr_text, returncode)

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Any = None,
        json: Any = None,
        files: Optional[Mapping[str, Any]] = None,
        timeout: Optional[Union[float, Tuple[Optional[float], Optional[float]]]] = None,
        connect_timeout: Optional[float] = None,
        follow_redirects: Optional[bool] = None,
        verify: Union[bool, str, None] = None,
        cookies: Optional[Mapping[str, Any]] = None,
        http1: Optional[bool] = None,
        http2: Optional[bool] = None,
        http3: Optional[bool] = None,
        tls_version: Optional[str] = None,
        tls_insecure: Optional[bool] = None,
        proxies: Optional[Mapping[str, str]] = None,
        max_retries: Optional[int] = None,
        retry_statuses: Optional[Sequence[int]] = None,
        debug: Optional[bool] = None,
        allow_redirects: Optional[bool] = None,
        raise_for_status: bool = False,
        stream: bool = False,
        auth: Any = None,
        referer: Optional[str] = None,
        accept: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_curl_args: Optional[Sequence[str]] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        compressed: bool = True,
        interface: Optional[str] = None,
        resolve: Optional[Sequence[str]] = None,
    ) -> Response:
        method = _sanitize_text(method, "HTTP method").upper()
        url = _sanitize_text(_merge_url_params(url, params), "URL")

        hdrs = dict(self.headers)
        for k, v in _normalize_headers(headers).items():
            _set_header(hdrs, k, v)

        if user_agent and not _header_exists(hdrs, "User-Agent"):
            _set_header(hdrs, "User-Agent", user_agent)
        elif self.user_agent and not _header_exists(hdrs, "User-Agent"):
            _set_header(hdrs, "User-Agent", self.user_agent)

        if accept and not _header_exists(hdrs, "Accept"):
            _set_header(hdrs, "Accept", accept)

        if referer and not _header_exists(hdrs, "Referer"):
            _set_header(hdrs, "Referer", referer)

        auth_header = _build_auth_header(auth)
        if auth_header and not _header_exists(hdrs, "Authorization"):
            _set_header(hdrs, "Authorization", auth_header)

        merged_cookies = self.cookies.get_dict()
        if cookies:
            for k, v in cookies.items():
                if v is not None:
                    merged_cookies[_sanitize_text(k, "cookie name")] = _sanitize_text(v, "cookie value")

        cookie_header = _build_cookie_header(merged_cookies)
        if cookie_header:
            _set_header(hdrs, "Cookie", cookie_header)

        req_http1, req_http2, req_http3 = _resolve_protocol(
            self.http1 if http1 is None else http1,
            self.http2 if http2 is None else http2,
            self.http3 if http3 is None else http3,
            default_http1=self.http1,
        )

        req_tls_version = _normalize_tls_version(tls_version if tls_version is not None else self.tls_version)
        req_verify = self.verify if verify is None else verify
        req_tls_insecure = self.tls_insecure if tls_insecure is None else bool(tls_insecure)

        timeout_value = self.timeout if timeout is None else timeout
        timeout_connect, timeout_total = _normalize_timeout(timeout_value)
        if connect_timeout is not None:
            timeout_connect = float(connect_timeout)

        req_follow = self.follow_redirects if follow_redirects is None else bool(follow_redirects)
        if allow_redirects is not None:
            req_follow = bool(allow_redirects)

        req_proxies: Dict[str, str] = dict(self.proxies)
        if proxies:
            req_proxies.update({str(k): str(v) for k, v in proxies.items() if v is not None})

        req_max_retries = self.max_retries if max_retries is None else max(0, int(max_retries))
        req_retry_statuses = set(self.retry_statuses if retry_statuses is None else set(retry_statuses))
        req_debug = self.debug if debug is None else bool(debug)

        attempts = req_max_retries + 1
        last_error: Optional[Exception] = None

        for attempt in range(attempts):
            temp_paths: List[str] = []
            headers_temp: Optional[str] = None
            body_temp: Optional[str] = None

            try:
                body_source, body_args, body_temp_paths = _encode_body(data=data, json_data=json, files=files)
                temp_paths.extend(body_temp_paths)

                headers_fd = tempfile.NamedTemporaryFile(delete=False)
                headers_temp = headers_fd.name
                headers_fd.close()

                body_fd = tempfile.NamedTemporaryFile(delete=False)
                body_temp = body_fd.name
                body_fd.close()

                cmd: List[str] = [
                    self.curl_path,
                    "-sS",
                    "-X",
                    method,
                    "--dump-header",
                    headers_temp,
                    "--output",
                    body_temp,
                    "--write-out",
                    "%{url_effective}\x1f%{http_code}\x1f%{num_redirects}\x1f%{http_version}",
                ]

                if req_http1:
                    cmd.append("--http1.1")
                elif req_http2:
                    cmd.append("--http2")
                elif req_http3:
                    cmd.append("--http3")

                if req_follow:
                    cmd.append("-L")

                cmd.extend(_verify_args(req_verify, req_tls_insecure))
                cmd.extend(_curl_tls_args(req_tls_version))

                if timeout_connect is not None:
                    cmd += ["--connect-timeout", str(timeout_connect)]
                if timeout_total is not None:
                    cmd += ["--max-time", str(timeout_total)]

                if compressed:
                    cmd.append("--compressed")

                proxy = _pick_proxy(req_proxies)
                if proxy:
                    cmd += ["-x", proxy]

                if interface:
                    cmd += ["--interface", _sanitize_text(interface, "network interface")]

                if cert is not None:
                    if isinstance(cert, (tuple, list)):
                        if len(cert) != 2:
                            raise ValueError("cert must be a path or (cert_path, key_path)")
                        cmd += ["--cert", _sanitize_text(cert[0], "cert path"), "--key", _sanitize_text(cert[1], "key path")]
                    else:
                        cmd += ["--cert", _sanitize_text(cert, "cert path")]

                if resolve:
                    for item in resolve:
                        cmd += ["--resolve", _sanitize_text(item, "resolve entry")]

                if req_debug:
                    cmd.append("-v")

                for k, v in hdrs.items():
                    cmd += ["-H", f"{k}: {v}"]

                cmd.extend(body_args)
                if extra_curl_args:
                    cmd.extend([_sanitize_text(x, "extra curl argument") for x in extra_curl_args])

                cmd.append(url)

                start = _now()
                stdin_body: Optional[bytes] = None
                if body_source is not None:
                    if isinstance(body_source, bytes):
                        stdin_body = body_source
                        cmd += ["--data-binary", "@-"]
                    else:
                        cmd += ["--data-binary", f"@{body_source}"]

                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE if stdin_body is not None else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout_meta, stderr_bytes = proc.communicate(stdin_body)
                elapsed = _now() - start

                stderr_text = (stderr_bytes or b"").decode("utf-8", errors="replace").strip()
                if req_debug and stderr_text:
                    print(stderr_text)

                with open(headers_temp, "rb") as f:
                    header_blob = f.read()
                blocks, final_headers, final_raw_headers, parsed_status, reason = _parse_header_blocks(header_blob)

                meta_text = (stdout_meta or b"").decode("utf-8", errors="replace").strip()
                meta_parts = meta_text.split("\x1f") if meta_text else []

                effective_url = url
                if len(meta_parts) >= 1 and meta_parts[0]:
                    effective_url = meta_parts[0]

                status_code = parsed_status
                if len(meta_parts) >= 2 and meta_parts[1]:
                    try:
                        status_code = int(meta_parts[1])
                    except ValueError:
                        pass

                redirect_count = 0
                if len(meta_parts) >= 3 and meta_parts[2]:
                    try:
                        redirect_count = int(meta_parts[2])
                    except ValueError:
                        pass

                http_version = meta_parts[3] if len(meta_parts) >= 4 else ""

                # Any non-zero curl exit code is an error, even if header/body files exist.
                if proc.returncode != 0:
                    err = _classify_curl_error(stderr_text, proc.returncode)
                    last_error = err
                    if attempt < attempts - 1 and _is_retryable_error(err):
                        self._sleep_backoff(attempt)
                        continue
                    raise err

                if status_code <= 0:
                    err = CurlError(stderr_text or "curl did not return a valid HTTP status code")
                    last_error = err
                    if attempt < attempts - 1:
                        self._sleep_backoff(attempt)
                        continue
                    raise err

                history: List[Response] = []
                all_cookies = CookieJar()

                for block in blocks[:-1]:
                    block_cookies = _parse_set_cookies(block["raw_headers"], CookieJar())
                    all_cookies.update(block_cookies.get_dict())
                    location = block["headers"].get("location", effective_url)
                    history.append(
                        Response(
                            status_code=block["status_code"],
                            url=location,
                            headers=block["headers"],
                            raw_headers=block["raw_headers"],
                            content=b"",
                            cookies=block_cookies,
                            elapsed=0.0,
                            reason=block["reason"],
                            history=[],
                            stderr=stderr_text,
                            effective_url=effective_url,
                            http_version=http_version,
                            redirect_count=redirect_count,
                            request_cmd=cmd[:],
                        )
                    )

                final_cookies = _parse_set_cookies(final_raw_headers, CookieJar())
                all_cookies.update(final_cookies.get_dict())
                if merged_cookies:
                    all_cookies.update(merged_cookies)

                content_bytes: Optional[bytes] = None
                body_path: Optional[str] = None

                if stream:
                    body_path = body_temp
                    body_temp = None
                else:
                    with open(body_temp, "rb") as f:
                        content_bytes = f.read()

                resp = Response(
                    status_code=status_code,
                    url=effective_url,
                    headers=final_headers,
                    raw_headers=final_raw_headers,
                    content=content_bytes,
                    cookies=all_cookies,
                    elapsed=elapsed,
                    reason=reason,
                    history=history,
                    stderr=stderr_text,
                    effective_url=effective_url,
                    http_version=http_version,
                    redirect_count=redirect_count,
                    request_cmd=cmd[:],
                    body_path=body_path,
                )

                self.cookies.update(resp.cookies.get_dict())

                if status_code in req_retry_statuses and attempt < attempts - 1:
                    retry_after = _retry_after_seconds(final_headers)
                    self._sleep_backoff(attempt, retry_after=retry_after)
                    last_error = RequestError(f"retryable HTTP status: {status_code}")
                    if not stream:
                        resp.close()
                    continue

                if raise_for_status and not resp.ok:
                    raise HTTPStatusError(resp)

                if not stream:
                    _cleanup_paths([body_temp])
                    resp._body_path = None

                _cleanup_paths([headers_temp])
                _cleanup_paths(temp_paths)
                return resp

            except FileNotFoundError as e:
                last_error = RequestError(f"curl binary not found: {self.curl_path}")
                if attempt < attempts - 1:
                    self._sleep_backoff(attempt)
                    continue
                raise last_error from e
            except RequestError as e:
                last_error = e
                if attempt < attempts - 1 and _is_retryable_error(e):
                    self._sleep_backoff(attempt)
                    continue
                raise
            finally:
                if headers_temp and os.path.exists(headers_temp):
                    _cleanup_paths([headers_temp])
                if not stream and body_temp and os.path.exists(body_temp):
                    _cleanup_paths([body_temp])
                _cleanup_paths(temp_paths)

        if last_error is not None:
            raise last_error
        raise RequestError("request failed")

    def close(self) -> None:
        return None

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class Session(Client):
    pass


_default_client = Client()


def request(method: str, url: str, **kwargs: Any) -> Response:
    return _default_client.request(method, url, **kwargs)


def get(url: str, **kwargs: Any) -> Response:
    return _default_client.get(url, **kwargs)


def post(url: str, **kwargs: Any) -> Response:
    return _default_client.post(url, **kwargs)


def put(url: str, **kwargs: Any) -> Response:
    return _default_client.put(url, **kwargs)


def delete(url: str, **kwargs: Any) -> Response:
    return _default_client.delete(url, **kwargs)


def patch(url: str, **kwargs: Any) -> Response:
    return _default_client.patch(url, **kwargs)


def head(url: str, **kwargs: Any) -> Response:
    return _default_client.head(url, **kwargs)


def options(url: str, **kwargs: Any) -> Response:
    return _default_client.options(url, **kwargs)


def build_client(**kwargs: Any) -> Client:
    return Client(**kwargs)


def is_json_response(resp: Response) -> bool:
    return resp.is_json


def text(resp: Response) -> str:
    return resp.text


def json(resp: Response, default: Any = _MISSING) -> Any:
    return resp.json(default=default)


def cookies(resp: Response) -> Dict[str, str]:
    return resp.cookies.get_dict()


def status(resp: Response) -> int:
    return resp.status_code


def headers(resp: Response) -> Dict[str, str]:
    return dict(resp.headers)


def content(resp: Response) -> bytes:
    return resp.content


def ok(resp: Response) -> bool:
    return resp.ok
