# quickreq

`quickreq` هي مكتبة HTTP خفيفة ومباشرة للبايثون، مبنية فوق `curl`.

فكرتها بسيطة: تعطيك واجهة مرتبة وسهلة مثل `get()` و`post()` و`Session()`، وفي نفس الوقت تستفيد من قوة `curl` في التحويلات، الشهادات، البروكسي، رفع الملفات، والكوكيز.

المطور: **AHMED ALHRRANI**  
Telegram: **@maho_s9**  
GitHub: **Gisnsl**

---

## ماذا تفعل المكتبة؟

`quickreq` تساعدك في إرسال الطلبات التالية:

- `GET`
- `POST`
- `PUT`
- `DELETE`
- `PATCH`
- `HEAD`
- `OPTIONS`

وتعطيك أشياء مهمة مثل:

- `params` داخل الرابط
- `headers`
- `cookies`
- `json`
- `data`
- `files`
- `auth`
- `proxies`
- `retry`
- `timeout`
- `follow_redirects`
- `TLS` و`SSL`

---

## لماذا قد تستخدمها؟

أنت قد تحتاج `quickreq` إذا كنت تريد:

- مكتبة خفيفة
- واجهة سهلة تشبه requests
- دعم ممتاز لرفع الملفات
- دعم JSON وform data
- تحكم جيد في redirects وtimeouts
- الاعتماد على `curl` بدل بناء محرك شبكة كامل من الصفر

---

## المتطلبات

- Python 3.8+
- وجود `curl` في النظام

> إذا لم يكن `curl` موجودًا، فلن تعمل المكتبة.

---

## التثبيت

من المشروع مباشرة:

```bash
pip install .
```

أو لو نشرت الحزمة على PyPI:

```bash
pip install quickreq
```

---

## الاستخدام السريع

### طلب GET

```python
import quickreq

resp = quickreq.get("https://httpbin.org/get")
print(resp.status_code)
print(resp.text)
```

### طلب POST مع JSON

```python
import quickreq

resp = quickreq.post(
    "https://httpbin.org/post",
    json={"name": "Ahmed", "role": "developer"}
)

print(resp.status_code)
print(resp.json())
```

### طلب POST مع form data

```python
import quickreq

resp = quickreq.post(
    "https://httpbin.org/post",
    data={"username": "maho", "password": "1234"}
)

print(resp.status_code)
print(resp.text)
```

### إرسال headers

```python
import quickreq

resp = quickreq.get(
    "https://httpbin.org/headers",
    headers={
        "User-Agent": "quickreq/1.0",
        "Accept": "application/json"
    }
)

print(resp.json())
```

### إرسال cookies

```python
import quickreq

resp = quickreq.get(
    "https://httpbin.org/cookies",
    cookies={"session": "abc123"}
)

print(resp.text)
```

### رفع ملف

```python
import quickreq

resp = quickreq.post(
    "https://httpbin.org/post",
    files={
        "file": ("example.txt", b"Hello from quickreq", "text/plain")
    }
)

print(resp.status_code)
print(resp.text)
```

---

## Client و Session

إذا أردت الاحتفاظ بإعدادات ثابتة واستخدامها أكثر من مرة، فاستعمل `Client`.

```python
from quickreq import Client

client = Client(
    timeout=30,
    follow_redirects=True,
    user_agent="quickreq/1.0",
    max_retries=2
)

resp = client.get("https://httpbin.org/get")
print(resp.status_code)
```

`Session` موجودة أيضًا كاسم بديل لـ `Client`.

```python
from quickreq import Session

s = Session()
resp = s.get("https://httpbin.org/get")
print(resp.status_code)
```

---

## الإعدادات المهمة

### timeout

يمكنك تمرير قيمة واحدة:

```python
quickreq.get("https://example.com", timeout=10)
```

أو تمرير قيمتين:

```python
quickreq.get("https://example.com", timeout=(5, 15))
```

- القيمة الأولى: `connect timeout`
- القيمة الثانية: `total timeout`

---

### follow_redirects

```python
quickreq.get("https://example.com", follow_redirects=True)
```

---

### verify و tls_insecure

```python
quickreq.get("https://example.com", verify=True)
quickreq.get("https://example.com", verify=False)
quickreq.get("https://example.com", tls_insecure=True)
```

- `verify=True` هو الوضع الافتراضي
- `verify=False` أو `tls_insecure=True` يعطل التحقق من الشهادة

---

### tls_version

```python
quickreq.get("https://example.com", tls_version="1.2")
```

القيم المدعومة:

- `1.0`
- `1.1`
- `1.2`
- `1.3`

---

### proxies

```python
quickreq.get(
    "https://example.com",
    proxies={
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080"
    }
)
```

---

### auth

```python
quickreq.get(
    "https://example.com",
    auth=("username", "password")
)
```

أو:

```python
quickreq.get(
    "https://example.com",
    auth="Bearer mytoken"
)
```

أو:

```python
quickreq.get(
    "https://example.com",
    auth="token mytoken"
)
```

---

## Response

كل طلب يرجع كائن `Response`.

### الخصائص المهمة

- `status_code`
- `url`
- `headers`
- `raw_headers`
- `cookies`
- `elapsed`
- `reason`
- `history`
- `stderr`
- `effective_url`
- `http_version`
- `redirect_count`

### الدوال والخصائص المفيدة

- `ok`
- `text`
- `content`
- `json()`
- `iter_lines()`
- `iter_content()`
- `get_header()`
- `raise_for_status()`
- `save()`

### مثال

```python
resp = quickreq.get("https://httpbin.org/json")

if resp.ok:
    print(resp.json())
else:
    print(resp.status_code)
```

---

## التعامل مع JSON

```python
resp = quickreq.get("https://httpbin.org/json")
print(resp.is_json)
print(resp.json())
```

ولو كان الرد ليس JSON، يمكنك تمرير قيمة افتراضية:

```python
value = resp.json(default={})
```

---

## حفظ الرد في ملف

```python
resp = quickreq.get("https://example.com/file.zip")
resp.save("file.zip")
```

---

## التعامل مع الملفات والـ multipart

`quickreq` تدعم إرسال الملفات بشكل مريح.

### ملف من bytes

```python
quickreq.post(
    "https://httpbin.org/post",
    files={
        "upload": ("hello.txt", b"hello world", "text/plain")
    }
)
```

### ملف من path

```python
quickreq.post(
    "https://httpbin.org/post",
    files={
        "upload": "myfile.txt"
    }
)
```

### data + files معًا

```python
quickreq.post(
    "https://httpbin.org/post",
    data={"title": "test"},
    files={"upload": ("a.txt", b"content")}
)
```

---

## الأخطاء

المكتبة تستخدم أخطاء واضحة تساعدك تعرف سبب المشكلة بسرعة:

- `RequestError`
- `CurlError`
- `NetworkError`
- `DNSResolutionError`
- `DNSDropError`
- `RequestTimeoutError`
- `TLSError`
- `HTTPStatusError`
- `JSONDecodeError`

### مثال

```python
import quickreq

try:
    resp = quickreq.get("https://invalid.domain.example")
    resp.raise_for_status()
except quickreq.RequestError as e:
    print("Request error:", e)
```

---

## الدوال الجاهزة

بدل ما تنشئ `Client` في كل مرة، يمكنك استخدام الدوال الجاهزة مباشرة:

```python
quickreq.get(...)
quickreq.post(...)
quickreq.put(...)
quickreq.delete(...)
quickreq.patch(...)
quickreq.head(...)
quickreq.options(...)
quickreq.request(...)
```

---

## build_client

```python
client = quickreq.build_client(
    timeout=20,
    follow_redirects=True,
    headers={"X-App": "quickreq"}
)
```

---

## helper functions

المكتبة توفر أيضًا دوال صغيرة مفيدة:

```python
quickreq.is_json_response(resp)
quickreq.text(resp)
quickreq.json(resp)
quickreq.cookies(resp)
quickreq.status(resp)
quickreq.headers(resp)
quickreq.content(resp)
quickreq.ok(resp)
```

---

## مثال عملي كامل

```python
import quickreq

client = quickreq.Client(
    follow_redirects=True,
    timeout=15,
    user_agent="quickreq/1.0",
    max_retries=2
)

resp = client.post(
    "https://httpbin.org/post",
    json={
        "name": "Ahmed",
        "project": "quickreq"
    },
    headers={
        "Accept": "application/json"
    }
)

print("Status:", resp.status_code)
print("URL:", resp.url)
print("JSON:", resp.json())
```

---

## ملاحظات مهمة

- المكتبة تعتمد على `curl`.
- الكوكيز داخل `Client` يتم الاحتفاظ بها تلقائيًا بعد الطلبات.
- `stream=True` يجعل الرد يُحفظ في ملف مؤقت بدل تحميله كاملًا في الذاكرة.
- المكتبة تحاول أن تكون مرنة، لكن ما زالت تحافظ على التحقق من القيم لتجنب الأخطاء الواضحة.

---

## هيكل المشروع

```bash
quickreq/
└── __init__.py
README.md
pyproject.toml
```

---

## الترخيص

- MIT
- Apache-2.0
- BSD-3-Clause

---

## المساهمة

إذا أردت تطوير المشروع أكثر:

1. افتح issue
2. اشرح الفكرة بوضوح
3. أرسل pull request

---

## كلمة أخيرة

`quickreq` مكتبة مباشرة، خفيفة، ومناسبة لمن يريد Requests-style API لكن مع الاعتماد على `curl` كخلفية تنفيذ.

### روابط المطور

- Telegram: `T.me/maho_s9`
- GitHub: `Gisnsl`
