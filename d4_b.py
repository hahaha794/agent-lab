import random
import time
from typing import Callable, TypeVar
import requests

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    attempts: int = 3,
    base_delay: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (),
) -> T:
    if attempts < 1:
        raise ValueError("attempts 至少为 1")

    for attempt in range(1, attempts + 1):
        try:
            return fn()                       # ① 成功立刻返回（别忘 return）
        except retry_on as e:                 # ② 关键：except 后面可以放"元组"
            if attempt == attempts:           # ③ 最后一次：原样抛出
                raise
            delay = base_delay * 2 ** (attempt - 1) + random.uniform(0, 1)                # ④ 指数退避 + 抖动
            print(f"第 {attempt} 次失败（{type(e).__name__}），{delay:.1f} 秒后重试")               # ⑤ 日志
            time.sleep(delay)

    raise RuntimeError("不可达：循环内一定会 return 或 raise")

if __name__ == "__main__":
    # 用例 1：第一次就成功 → 不重试、不打印
    print(with_retry(lambda: "直接成功", attempts=3, retry_on=(requests.Timeout,)))

    # 用例 2：前 2 次失败、第 3 次成功 → 打印 2 次重试
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] <= 2:
            raise requests.Timeout("模拟超时")
        return "第 3 次成功"

    # 注意：这里 base_delay 用 0.1，不然真的要等 3 秒
    print(with_retry(flaky, attempts=3, base_delay=0.1, retry_on=(requests.Timeout,)))

    # 用例 3：一直失败 → 3 次后抛 Timeout
    def always_fail():
        raise requests.Timeout("永远超时")
    try:
        with_retry(always_fail, attempts=3, base_delay=0.1, retry_on=(requests.Timeout,))
    except requests.Timeout:
        print("用尽重试后抛出原异常 ✅")

    # 用例 4：不归它管的异常 → 立刻抛，不重试
    def bad():
        raise ValueError("这不是网络问题")
    try:
        with_retry(bad, attempts=3, retry_on=(requests.Timeout,))
    except ValueError:
        print("ValueError 立刻抛出，没有重试 ✅")