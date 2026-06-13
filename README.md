# quickreq

`quickreq` مكتبة بسيطة جدًا لطلبات HTTP، لكنها لا تحاول أن تكون “ذكية أكثر من اللازم”.
فكرتها واضحة: أنت تكتب طلبك من Python، والمكتبة تتولى تشغيل `curl` في الخلفية، ثم تعيد لك الاستجابة بشكل مرتب وسهل الاستخدام.

**المطور:** AHMED ALHRRANI  
**T.me:** maho_s9  
**GitHub:** Gisnsl

## لماذا هذه المكتبة موجودة؟

أحيانًا لا تريد إطارًا ضخمًا ولا طبقات كثيرة فوق بعض. تريد شيئًا مباشرًا:

- ترسل `GET` أو `POST`
- تضيف headers
- تحفظ cookies
- ترسل JSON
- ترفع ملفات
- تتحكم في البروكسي و TLS
- وتتعامل مع النتيجة بدون تعقيد

هذا بالضبط ما تحاول `quickreq` أن تقدمه.

## الفكرة ببساطة

المكتبة لا تعيد اختراع HTTP من الصفر. هي تبني أمر `curl` مناسبًا ثم تشغله، وبعدها تقرأ:

- status code
- headers
- body
- cookies
- معلومات التحويلات redirect
- وأي خطأ حصل أثناء الاتصال

يعني أنت تتعامل مع واجهة Python نظيفة، بينما القوة الفعلية تأتي من `curl` نفسه.

## المتطلبات

- Python 3.8 أو أحدث
- وجود `curl` مثبتًا على النظام

إذا لم يكن `curl` موجودًا، فلن تعمل الطلبات.

## التثبيت

إذا كانت الحزمة داخل مجلد `quickreq/`:

```bash
pip install .
```

أو لو تريدها بوضع التطوير:

```bash
pip install -e .
```

## شكل الحزمة

```text
quickreq/
└── __init__.py
README.md
pyproject.toml
```

## ما الذي توفره `quickreq`؟

### 1) `Client`
هذا هو قلب المكتبة.

من خلاله تستطيع ضبط أغلب الأشياء المهمة قبل إرسال أي طلب:

- `http1` / `http2` / `http3`
- `timeout`
- `connect_timeout`
- `follow_redirects`
- `verify`
- `tls_version`
- `tls_insecure`
- `cookies`
- `headers`
- `user_agent`
- `proxies`
- `max_retries`
- `retry_statuses`
- `retry_backoff_factor`
- `retry_max_delay`
- `debug`

فكرة `Client` أنه يحفظ لك الإعدادات التي تريد استخدامها مرارًا، بدل أن تكتبها كل مرة من جديد.

### 2) `Session`
هي ليست كائنًا مختلفًا فعليًا، بل اسم مألوف لمن يفضل أسلوبًا قريبًا من مكتبات HTTP المعروفة.

### 3) `Response`
هذا هو كائن النتيجة الذي تستلمه بعد الطلب.

يحمل معه أشياء مفيدة مثل:

- `status_code`: كود الرد مثل 200 أو 404
- `url`: الرابط النهائي الذي انتهى إليه الطلب
- `headers`: الهيدرز بشكل منظم
- `raw_headers`: الهيدرز كما وردت تقريبًا
- `content`: المحتوى الخام بالبايت
- `text`: المحتوى كنص
- `cookies`: الكوكيز المستلمة
- `elapsed`: الزمن الذي استغرقه الطلب
- `reason`: السبب النصي للحالة إن وجد
- `history`: سجل التحويلات عند وجود Redirects
- `stderr`: رسالة `curl` في حال ظهرت
- `effective_url`: الرابط النهائي الفعلي
- `http_version`: إصدار HTTP المستخدم
- `redirect_count`: عدد التحويلات
- `request_cmd`: أمر `curl` الذي تم تنفيذه

### 4) الاستثناءات
المكتبة لا ترجع لك الفشل على شكل رسالة عامة فقط، بل تحاول تصنيفه:

- `RequestError`
- `CurlError`
- `NetworkError`
- `DNSResolutionError`
- `DNSDropError`
- `RequestTimeoutError`
- `TLSError`
- `HTTPStatusError`
- `JSONDecodeError`

هذا يساعدك على معرفة أين المشكلة بالضبط: DNS، شبكة، TLS، timeout، أو كود HTTP نفسه.

## الاستخدام السريع

```python
from quickreq import get

resp = get('https://example.com')
print(resp.status_code)
print(resp.text)
```

## إرسال طلب GET

```python
from quickreq import get

resp = get('https://httpbin.org/get')
print(resp.status_code)
print(resp.headers)
```

## إرسال طلب POST مع JSON

هذه من أكثر الحالات استخدامًا.

```python
from quickreq import post

resp = post(
    'https://httpbin.org/post',
    json={'name': 'Ahmed', 'tool': 'quickreq'}
)

print(resp.status_code)
print(resp.json())
```

عند استخدام `json=...` تقوم المكتبة تلقائيًا بتهيئة المحتوى كـ JSON وتضيف `Content-Type: application/json; charset=utf-8`.

## إرسال form data

```python
from quickreq import post

resp = post(
    'https://httpbin.org/post',
    data={'a': 1, 'b': 'hello'}
)

print(resp.text)
```

هنا يتم تحويل البيانات إلى `application/x-www-form-urlencoded`.

## رفع ملفات

المكتبة تدعم رفع الملفات عبر `multipart/form-data`.

```python
from quickreq import post

resp = post(
    'https://httpbin.org/post',
    files={
        'file': ('sample.txt', b'hello world', 'text/plain')
    }
)

print(resp.status_code)
```

يمكنك أيضًا تمرير ملف من المسار مباشرة، أو تمرير محتوى خام، والمكتبة ستتعامل معه.

## استخدام الكوكيز

`quickreq` تحفظ الكوكيز وتدمجها مع الطلبات التالية داخل نفس `Client`.

```python
from quickreq import Client

client = Client(cookies={'session': '12345'})
resp = client.get('https://example.com')

print(resp.cookies.get_dict())
```

هذا مفيد جدًا لو كنت تتعامل مع جلسة تسجيل دخول أو API يعتمد على cookies.

## التعامل مع الاستجابة

### `resp.text`
يعطيك الجسم كنص بعد محاولة استخدام الترميز المناسب.

### `resp.content`
يعطيك الجسم الخام بالبايت.

### `resp.json()`
يفك JSON إذا كان نوع المحتوى مناسبًا.

### `resp.lines`
يرجع النص مقسومًا إلى أسطر.

### `resp.iter_content(chunk_size=8192)`
مفيد عندما تريد قراءة المحتوى على دفعات بدل تحميله دفعة واحدة.

### `resp.iter_lines()`
يمر على الأسطر واحدًا واحدًا.

### `resp.save(path)`
يحفظ الرد في ملف.

### `resp.raise_for_status()`
يرفع `HTTPStatusError` إذا كانت الحالة ليست ضمن نطاق النجاح.

## خصائص مفيدة داخل `Response`

### `resp.ok`
ترجع `True` إذا كانت الحالة بين 200 و 399.

### `resp.is_json`
تتحقق من أن المحتوى JSON فعليًا عبر `Content-Type`.

### `resp.encoding`
تحاول قراءة `charset` من الهيدر، وإن لم تجده فتعتمد `utf-8`.

### `resp.content_type`
تعطيك قيمة `Content-Type` كما وصلت.

## إعداد عميل مخصص

```python
from quickreq import Client

client = Client(
    timeout=20,
    follow_redirects=True,
    user_agent='quickreq/1.0',
    headers={'Accept': 'application/json'},
)

resp = client.get('https://httpbin.org/json')
print(resp.json())
```

هذا الأسلوب جيد عندما تريد نفس السلوك في أكثر من طلب.

## البروتوكولات HTTP

يمكنك اختيار بروتوكول واحد فقط:

- `http1=True`
- `http2=True`
- `http3=True`

مثال:

```python
client = Client(http2=True)
```

إذا لم تحدد شيئًا، فالمكتبة تستخدم HTTP/1.1 بشكل افتراضي.

## الوقت والمهلات

يمكنك ضبط:

- `timeout` كقيمة واحدة
- أو `timeout=(connect_timeout, total_timeout)`
- أو `connect_timeout` بشكل مستقل

مثال:

```python
client = Client(timeout=(5, 20))
```

المعنى هنا:
- 5 ثوانٍ للاتصال
- 20 ثانية كحد إجمالي

## إعادة المحاولة Retry

المكتبة لا تستسلم مباشرة لبعض الحالات المؤقتة.

عادةً تعيد المحاولة في حالات مثل:

- `429`
- `500`
- `502`
- `503`
- `504`

مثال:

```python
client = Client(max_retries=3, retry_backoff_factor=0.5)
resp = client.get('https://example.com')
```

كما أنها تتعامل مع `Retry-After` إذا كان موجودًا في الرد.

## TLS والبروكسي

### TLS
يمكنك اختيار نسخة TLS أو تخفيف التحقق عند الحاجة:

```python
client = Client(tls_version='1.2')
```

أو:

```python
client = Client(verify=False)
```

أو:

```python
client = Client(tls_insecure=True)
```

### Proxy
يدعم:

- `http`
- `https`
- `all`
- `proxy`

مثال:

```python
client = Client(proxies={'https': 'http://127.0.0.1:8080'})
```

## التوثيق Authentication

المكتبة تتعامل مع `auth` بعدة صيغ:

- `(username, password)` → Basic Auth
- `'Bearer ...'` → يبقى كما هو
- `'Token ...'` → يتحول إلى Bearer
- أي string عادي → Bearer token

مثال:

```python
from quickreq import get

resp = get('https://api.example.com', auth=('user', 'pass'))
```

## الهيدرز Headers

يمكنك تمرير الهيدرز التي تريدها، والمكتبة تدمجها مع الهيدرز الافتراضية.

هي أيضًا تمنع القيم التي تحتوي على:

- ` `
- ``
- `
`

وهذا مهم لأن وجود هذه الأحرف داخل headers قد يسبب مشاكل أو سلوكًا غير آمن.

## البث Streaming

إذا استخدمت:

```python
resp = client.get(url, stream=True)
```

فسيتم الاحتفاظ بالجسم في ملف مؤقت بدل نسخه كاملًا إلى الذاكرة فورًا.

هذا مفيد عندما يكون الرد كبيرًا أو عندما تريد قراءته تدريجيًا.

## الدوال الجاهزة على مستوى المكتبة

بدل أن تنشئ `Client` في كل مرة، تستطيع استعمال الدوال المختصرة:

- `request(method, url, ...)`
- `get(url, ...)`
- `post(url, ...)`
- `put(url, ...)`
- `delete(url, ...)`
- `patch(url, ...)`
- `head(url, ...)`
- `options(url, ...)`

وتوجد أيضًا دوال مساعدة لقراءة أجزاء من `Response`:

- `is_json_response(resp)`
- `text(resp)`
- `json(resp, default=...)`
- `cookies(resp)`
- `status(resp)`
- `headers(resp)`
- `content(resp)`
- `ok(resp)`

## مثال على التعامل مع الأخطاء

```python
from quickreq import get, RequestError, HTTPStatusError

try:
    resp = get('https://example.com', raise_for_status=True)
except HTTPStatusError as e:
    print('HTTP status:', e.response.status_code)
except RequestError as e:
    print('Request failed:', e)
```

## ملاحظات صريحة ومهمة

- `quickreq` تعتمد على `curl` فعلًا، لذلك جودة التجربة مرتبطة ببيئة النظام.
- دعم `http3` يعتمد على نسخة `curl` الموجودة عندك.
- عند استخدام `stream=True` من الأفضل إنهاء التعامل مع الرد بشكل صحيح أو استدعاء `close()` إذا احتجت.
- `Client` يحتفظ بالكوكيز ويحدّثها تلقائيًا بعد الطلبات.

## خلاصة سريعة

`quickreq` مناسبة لك إذا كنت تريد مكتبة:

- خفيفة
- واضحة
- فيها دعم JSON و form و files
- تتعامل مع cookies و headers و redirects
- وتستفيد من قوة `curl` بدون أن تكتب أوامره يدويًا كل مرة
