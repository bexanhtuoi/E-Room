---
name: Quy chuẩn lập trình Python
description: Quy ước viết mã Python cho các dịch vụ backend.
tags:
  - python
  - backend
  - api
paths:
  - "**/*.py"
---

# Quy chuẩn lập trình Python

## Mục tiêu

Viết mã Python rõ ràng, dễ đọc, dễ bảo trì, dễ mở rộng và sẵn sàng cho môi trường production.

---

## Nguyên tắc chung

- Ưu tiên tính dễ đọc hơn các kỹ thuật quá phức tạp.
- Tuân thủ PEP 8, trừ khi dự án có quy ước riêng.
- Viết mã đơn giản, dễ hiểu.
- Không tối ưu hóa quá sớm.
- Tránh tạo tầng trừu tượng không cần thiết.
- Luôn luôn dùng uv để quản lí thư viện và thực thi code

---

## Quy tắc đặt tên

- Biến: `snake_case`
- Hàm: `snake_case`
- Lớp: `PascalCase`

Tên phải rõ nghĩa, tránh viết tắt nếu không phổ biến.

---

## Hàm

- Khi đặt tên hàm không được _ trước hoặc sau tên hàm.
- Mỗi hàm chỉ nên thực hiện một nhiệm vụ.
- Ưu tiên `early return` để giảm lồng điều kiện.
- Khuyến nghị không quá 50 dòng.
- Sử dụng type hint đầy đủ, ưu tiên Optional[str] hay List[str] thay vì str | None hay list[str].
- BẮT BUỘC dãn cách: dòng trống sau MỖI câu lệnh/khối logic (kể cả 2 phép gán liên tiếp cũng cách nhau), trước/sau mỗi khối if/for/while/try, giữa các bước xử lý.
- Dict/list nhiều key thì mỗi key 1 dòng.
- KHÔNG viết comment trang trí/docstring dư thừa — chỉ giữ comment theo bước (đánh số) hoặc ghi chú ràng buộc quan trọng, luôn tiếng Việt có dấu.
- Nếu bên trong hàm có thể phân nhỏ ra thành các hàm con để tái sử dụng cho lần sau thì hãy phân nhỏ ra và gọi các hàm con đó thay vì ném hết vào 1 hàm duy nhất.

### Nên

```python
def square(number: float) -> float:
    return number * number


def sum_of_squares(a: float, b: float) -> float:
    return square(a) + square(b)


def calculate_distance(x: float, y: float) -> float:
    total = sum_of_squares(x, y)

    distance = total ** 0.5

    return distance
```

### Không nên

```python
def calculate_hypotenuse(a, b):
    a_square = a * a
    b_square = b * b
    total = a_square + b_square

    print(a_square)
    print(b_square)

    save_log(total)
    update_statistics(total)

    return total ** 0.5
```

---

## Lớp

- Ưu tiên **Composition** hơn **Inheritance** nếu chỉ cần tái sử dụng chức năng.
- Chỉ sử dụng **Inheritance** khi tồn tại quan hệ "is-a" rõ ràng và lớp con thực sự mở rộng hành vi của lớp cha.
- Constructor (`__init__`) chỉ nên khởi tạo dữ liệu, không chứa logic nghiệp vụ hoặc xử lý phức tạp.
- Không sử dụng mutable class variable (`list`, `dict`, `set`,...) để tránh các instance dùng chung dữ liệu.
- Dùng TypedDict hoặc Pydantic nếu dữ liệu có cấu trúc.
- Tận dụng các magic methods (`__init__`, `__call__`, `__str__`, `__repr__`,...) và decorator (`@property`, `@staticmethod`, `@classmethod`) khi phù hợp để code rõ ràng và Pythonic.

### Nên

```python
class Calculator:
    def square(self, number: float) -> float:
        return number * number


class ScientificCalculator(Calculator):
    def __init__(self) -> None:
        self.history: list[str] = []

    @property
    def total_calculations(self) -> int:
        return len(self.history)

    def calculate_distance(self, x: float, y: float) -> float:
        # Tính tổng bình phương
        total = self.square(x) + self.square(y)

        # Lưu lịch sử tính toán
        self.history.append(f"{x}² + {y}² = {total}")

        # Trả về khoảng cách
        return total ** 0.5


calculator = ScientificCalculator()

print(calculator.calculate_distance(3, 4))
print(calculator.total_calculations)
```

### Không nên

```python
class Calculator:
    history = []

    def __init__(self):
        print("Initializing...")

        self.history.append("Created")

        total = 0
        for i in range(1_000_000):
            total += i

        print(total)

    def calculate_distance(self, x, y):
        x_square = x * x
        y_square = y * y
        total = x_square + y_square

        self.history.append(total)

        print(total)

        save_log(total)
        update_statistics(total)
        send_notification(total)

        return total ** 0.5
```
---

## Import

Thứ tự import:

1. Thư viện chuẩn (Standard Library).
2. Thư viện bên thứ ba (Third-party).
3. Module nội bộ của dự án (Local).

- Mỗi nhóm cách nhau một dòng.
- Sắp xếp import theo thứ tự alphabet trong từng nhóm.
- Không sử dụng `from ... import *`.
- Chỉ import những gì thực sự cần sử dụng.

### Nên

```python
import os
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter

from app.schemas.user import UserResponse
from app.services.user_service import UserService
from app.utils.file import read_json
```

### Không nên

```python
from app.services.user_service import UserService
import pandas as pd
from fastapi import APIRouter
from app.utils.file import *
import os
import numpy as np
from pathlib import Path
from app.schemas.user import UserResponse
```

---

## Xử lý ngoại lệ

- Không sử dụng `except:` hoặc `except Exception:` nếu không có mục đích rõ ràng.
- Luôn bắt đúng loại Exception có thể xảy ra.
- Thông báo lỗi phải rõ ràng, dễ hiểu và có ngữ cảnh.
- Khi ném lại ngoại lệ, giữ nguyên traceback bằng `raise` hoặc sử dụng `raise ... from ...`.

### Nên

```python
def divide(a: float, b: float) -> float:
    try:
        return a / b
    except ZeroDivisionError:
        raise ValueError("Không thể chia cho 0")
```

### Không nên

```python
def divide(a, b):
    try:
        return a / b
    except:
        print("Có lỗi xảy ra")
```
---

## Logging

- Sử dụng `logging` thay cho `print()`.
- Không ghi log thông tin nhạy cảm như mật khẩu, token, API key hoặc thông tin cá nhân.
- Log cần đầy đủ ngữ cảnh như tên chức năng, mã định danh, trạng thái và nguyên nhân lỗi.
- Sử dụng placeholder (`%s`) hoặc structured logging thay vì nối chuỗi hoặc f-string.
- Chọn đúng mức log (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) theo mức độ của sự kiện.

### Nên

```python
from app.log import get_logger

log = get_logger("order", log_file="log/app.log")


def process_order(order_id: int, customer_id: int) -> None:
    # Bắt đầu xử lý đơn hàng
    logger.info(
        "Processing order | order_id=%s customer_id=%s",
        order_id,
        customer_id,
    )

    try:
        # Xử lý nghiệp vụ
        ...

        # Xử lý thành công
        logger.info(
            "Order processed successfully | order_id=%s",
            order_id,
        )

    except ValueError as error:
        # Ghi nhận lỗi nghiệp vụ
        logger.error(
            "Failed to process order | order_id=%s reason=%s",
            order_id,
            error,
        )
        raise
```

### Không nên

```python
def process_order(order_id, customer_id):
    print("Start")

    try:
        ...

        print(f"Order {order_id} completed")

    except Exception as error:
        print(error)
```

---

## Kiểm thử

- Viết Unit Test cho chức năng mới.
- Bao phủ các trường hợp biên (edge cases).
- Test phải ổn định, độc lập và có thể chạy lặp lại.

### Nên

```python
def square(number: int) -> int:
    return number * number


def test_square():
    assert square(3) == 9
    assert square(0) == 0
    assert square(-2) == 4
```

### Không nên

```python
import random


def square(number):
    return number * number


def test_square():
    value = random.randint(1, 100)
    assert square(value) == value * value
```

---

## Không được phép

- Sử dụng biến toàn cục có thể thay đổi.
- Hard-code các giá trị không có ý nghĩa (magic numbers).
- Lồng điều kiện quá 3 cấp.
- Để lại mã đã comment.
- Giữ mã không còn sử dụng.

### Nên

```python
MAX_RETRY = 3


def can_retry(retry_count: int) -> bool:
    return retry_count < MAX_RETRY
```

### Không nên

```python
retry = 0


def process():
    global retry

    if retry < 3:
        if check():
            if verify():
                if execute():
                    print("Success")

    # old_process()

    retry += 1
```