# quickreq

`quickreq` مكتبة خفيفة وبسيطة للتعامل مع HTTP requests من بايثون، لكنها تعتمد على `curl` تحت الغطاء.  
فكرتها واضحة: تعطيك واجهة نظيفة وسهلة مثل `get()` و `post()` و `Session()`، وفي نفس الوقت تستفيد من قوة `curl` في الشبكات، التحويلات، الكوكيز، ورفع الملفات.

المطور: **AHMED ALHRRANI**  
Telegram: **@maho_s9**  
GitHub: **Gisnsl**

---

## لماذا quickreq؟

أحيانًا تحتاج مكتبة:

- سريعة في الاستخدام
- خفيفة بدون تعقيد
- تدعم JSON, form data, multipart files, cookies
- فيها retry و timeout و TLS options
- وتعطيك نفس شعور `requests` لكن بأسلوب أبسط ومباشر

هنا تأتي `quickreq`.

---

## أهم الأشياء التي تعملها المكتبة

`quickreq` تقدر:

- ترسل طلبات HTTP مثل:
  - `GET`
  - `POST`
  - `PUT`
  - `DELETE`
  - `PATCH`
  - `HEAD`
  - `OPTIONS`
- ترسل `params` في الرابط
- ترسل `headers`
- ترسل `cookies`
- ترسل `data` بصيغة:
  - form-urlencoded
  - raw bytes
  - text
  - stream / file-like object
- ترسل `json`
- ترفع ملفات `files`
- تتعامل مع redirects
- تتحكم في `timeout`
- تختار `http1` أو `http2` أو `http3`
- تدعم `verify` و `tls_version` و `tls_insecure`
- تدعم `proxies`
- تدعم `auth`
- تدعم `retry`
- تعطيك كائن `Response` مرتب فيه:
  - `status_code`
  - `headers`
  - `cookies`
  - `text`
  - `content`
  - `json()`
  - `elapsed`
  - `history`
  - `ok`

---

## المتطلبات

- Python 3.8+
- وجود `curl` في النظام

> مهم: هذه المكتبة لا تعمل بدون `curl` لأنه هو المحرك الأساسي خلفها.

---

## التثبيت

إذا كانت الحزمة منشورة عندك كـ package:

```bash
pip install quickreq

أو من المشروع مباشرة:

pip install .


---

استخدام سريع

GET

import quickreq

resp = quickreq.get("https://httpbin.org/get")
print(resp.status_code)
print(resp.text)

POST باستخدام JSON

import quickreq

resp = quickreq.post(
    "https://httpbin.org/post",
    json={"name": "Ahmed", "role": "developer"}
)

print(resp.status_code)
print(resp.json())

POST باستخدام form data

import quickreq

resp = quickreq.post(
    "https://httpbin.org/post",
    data={"username": "maho", "password": "1234"}
)

print(resp.status_code)
print(resp.text)

إرسال headers

import quickreq

resp = quickreq.get(
    "https://httpbin.org/headers",
    headers={
        "User-Agent": "quickreq/1.0",
        "Accept": "application/json"
    }
)

print(resp.json())

إرسال cookies

import quickreq

resp = quickreq.get(
    "https://httpbin.org/cookies",
    cookies={"session": "abc123"}
)

print(resp.text)

رفع ملف

import quickreq

resp = quickreq.post(
    "https://httpbin.org/post",
    files={
        "file": ("example.txt", b"Hello from quickreq", "text/plain")
    }
)

print(resp.status_code)
print(resp.text)


---

Client و Session

إذا كنت تريد تبني إعداداتك مرة واحدة واستخدامها في عدة requests، استخدم Client أو Session.

Client

from quickreq import Client

client = Client(
    timeout=30,
    follow_redirects=True,
    user_agent="quickreq/1.0",
    max_retries=2
)

resp = client.get("https://httpbin.org/get")
print(resp.status_code)

Session

Session موجودة كاسم بديل لـ Client.

from quickreq import Session

s = Session()
resp = s.get("https://httpbin.org/get")
print(resp.status_code)


---

إعدادات مهمة

timeout

يمكنك تمرير قيمة واحدة أو قيمتين:

quickreq.get("https://example.com", timeout=10)
quickreq.get("https://example.com", timeout=(5, 15))

timeout=10 يعني total timeout

(connect_timeout, total_timeout)



---

follow_redirects

quickreq.get("https://example.com", follow_redirects=True)

أو:

client = quickreq.Client(follow_redirects=True)


---

verify و tls_insecure

quickreq.get("https://example.com", verify=True)
quickreq.get("https://example.com", verify=False)
quickreq.get("https://example.com", tls_insecure=True)

verify=True هو الوضع الافتراضي

verify=False أو tls_insecure=True يعطّل التحقق من الشهادة



---

tls_version

quickreq.get("https://example.com", tls_version="1.2")

القيم المدعومة:

"1.0"

"1.1"

"1.2"

"1.3"



---

proxies

quickreq.get(
    "https://example.com",
    proxies={
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080"
    }
)


---

auth

quickreq.get(
    "https://example.com",
    auth=("username", "password")
)

أو:

quickreq.get(
    "https://example.com",
    auth="Bearer mytoken"
)

أو:

quickreq.get(
    "https://example.com",
    auth="token mytoken"
)


---

retry

client = quickreq.Client(
    max_retries=3,
    retry_statuses={429, 500, 502, 503, 504}
)

هذا مفيد عندما تكون الخدمة مؤقتًا مشغولة أو ترجع أخطاء قابلة لإعادة المحاولة.


---

Response

كل request يرجع لك كائن Response.

أهم الخصائص

resp.status_code
resp.url
resp.headers
resp.raw_headers
resp.cookies
resp.elapsed
resp.reason
resp.history
resp.stderr
resp.effective_url
resp.http_version
resp.redirect_count

أهم الدوال والخصائص

resp.ok
resp.text
resp.content
resp.json()
resp.iter_lines()
resp.iter_content(chunk_size=8192)
resp.get_header("Content-Type")
resp.raise_for_status()
resp.save("file.bin")

مثال

resp = quickreq.get("https://httpbin.org/json")

if resp.ok:
    data = resp.json()
    print(data)
else:
    print("Request failed:", resp.status_code)


---

التعامل مع JSON

resp = quickreq.get("https://httpbin.org/json")

print(resp.is_json)
print(resp.json())

ولو رجع الرد ليس JSON، فالمكتبة سترفع خطأ مناسب.
ويمكنك تمرير قيمة افتراضية:

value = resp.json(default={})


---

حفظ المحتوى في ملف

resp = quickreq.get("https://example.com/file.zip")
resp.save("file.zip")

أو يمكنك حفظ أي رد إلى ملف:

with open("out.txt", "w", encoding="utf-8") as f:
    f.write(resp.text)


---

رفع الملفات والـ multipart

quickreq تدعم رفع الملفات بطريقة عملية جدًا.

ملف من bytes

quickreq.post(
    "https://httpbin.org/post",
    files={
        "upload": ("hello.txt", b"hello world", "text/plain")
    }
)

ملف من path

quickreq.post(
    "https://httpbin.org/post",
    files={
        "upload": "myfile.txt"
    }
)

بيانات + ملفات معًا

quickreq.post(
    "https://httpbin.org/post",
    data={"title": "test"},
    files={"upload": ("a.txt", b"content")}
)


---

الأخطاء

المكتبة تستخدم أخطاء واضحة بدل الرسائل الغامضة.

الأنواع الأساسية

RequestError

CurlError

NetworkError

DNSResolutionError

DNSDropError

RequestTimeoutError

TLSError

HTTPStatusError

JSONDecodeError


مثال

import quickreq

try:
    resp = quickreq.get("https://invalid.domain.example")
    resp.raise_for_status()
except quickreq.RequestError as e:
    print("Request error:", e)


---

الاختصارات الجاهزة

المكتبة توفر دوال جاهزة مباشرة:

quickreq.get(...)
quickreq.post(...)
quickreq.put(...)
quickreq.delete(...)
quickreq.patch(...)
quickreq.head(...)
quickreq.options(...)
quickreq.request(...)


---

build_client

إذا كنت تريد إنشاء Client بطريقة واضحة:

client = quickreq.build_client(
    timeout=20,
    follow_redirects=True,
    headers={"X-App": "quickreq"}
)


---

helper functions

المكتبة فيها بعض الدوال الصغيرة المفيدة:

quickreq.is_json_response(resp)
quickreq.text(resp)
quickreq.json(resp)
quickreq.cookies(resp)
quickreq.status(resp)
quickreq.headers(resp)
quickreq.content(resp)
quickreq.ok(resp)


---

مثال عملي كامل

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


---

ملاحظات مهمة

هذه المكتبة تعتمد على curl، لذلك وجوده ضروري.

إذا لم يكن curl موجودًا في النظام، ستفشل الطلبات.

المكتبة تحاول أن تكون مرنة، لكنها أيضًا حذرة في التعامل مع المدخلات.

الكوكيز يتم حفظها داخل Client تلقائيًا بعد الطلبات.

stream=True يخزن الرد على ملف مؤقت بدل تحميله كاملًا في الذاكرة.



---

هيكل المكتبة

عادة تكون بالشكل التالي:

quickreq/
└── __init__.py
README.md
pyproject.toml


---

الترخيص

يُضاف هنا الترخيص الذي تريده للمشروع، مثل:

MIT

Apache-2.0

BSD-3-Clause



---

للمساهمة

إذا كنت تريد تطوير quickreq:

1. افتح issue


2. اقترح تحسين


3. أرسل pull request




---

كلمة أخيرة

quickreq مكتبة كتبت لتكون مباشرة، مفهومة، وسهلة الاستخدام.
ما فيها تعقيد زائد، وما تحاول تتفلسف على المستخدم.
فكرتها أنها تعطيك أدوات HTTP جاهزة بشكل نظيف، وتخليك تشتغل بسرعة.


---

روابط المطور

Telegram: T.me/maho_s9

GitHub: Gisnsl
