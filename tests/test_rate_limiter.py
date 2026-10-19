import asyncio
import time
import unittest

from src.rate_limiter import RateLimiterManager, TokenBucketRateLimiter


class TestRateLimiter(unittest.IsolatedAsyncioTestCase):
    async def test_try_acquire_success(self):
        # 10 tokens per sec, capacity 5
        limiter = TokenBucketRateLimiter(rate=10.0, capacity=5)
        
        # Initial capacity is full
        self.assertTrue(await limiter.try_acquire(3))
        self.assertTrue(await limiter.try_acquire(2))
        # Now empty
        self.assertFalse(await limiter.try_acquire(1))

    async def test_refill(self):
        limiter = TokenBucketRateLimiter(rate=100.0, capacity=10)
        # Empty it
        await limiter.try_acquire(10)
        self.assertFalse(await limiter.try_acquire(1))
        
        # Wait for refill (0.02s should give 2 tokens)
        await asyncio.sleep(0.02)
        self.assertTrue(await limiter.try_acquire(1))

    async def test_acquire_wait(self):
        limiter = TokenBucketRateLimiter(rate=100.0, capacity=1)
        await limiter.try_acquire(1) # Empty it
        
        start = time.monotonic()
        await limiter.acquire(1) # Should wait ~0.01s
        elapsed = time.monotonic() - start
        
        self.assertGreaterEqual(elapsed, 0.005)

    async def test_acquire_exceeds_capacity_raises_value_error(self):
        limiter = TokenBucketRateLimiter(rate=10.0, capacity=5)
        with self.assertRaises(ValueError):
            await limiter.acquire(6)

    async def test_acquire_zero_or_negative_raises_value_error(self):
        limiter = TokenBucketRateLimiter(rate=10.0, capacity=5)
        with self.assertRaises(ValueError):
            await limiter.acquire(0)
        with self.assertRaises(ValueError):
            await limiter.acquire(-1)

    async def test_acquire_does_not_hold_lock_while_sleeping(self):
        # 1 token/sec, capacity 1. Empty the bucket first.
        limiter = TokenBucketRateLimiter(rate=1.0, capacity=1)
        self.assertTrue(await limiter.try_acquire(1))

        # Start an acquire task that must wait ~1s
        task = asyncio.create_task(limiter.acquire(1))

        # Yield to let acquire() enter its loop and begin sleeping
        await asyncio.sleep(0.01)

        # Another task should immediately be able to call try_acquire()
        # without being blocked for 1s by the waiting acquire task
        lock_acquired_immediately = False
        try:
            await asyncio.wait_for(limiter.try_acquire(1), timeout=0.1)
            lock_acquired_immediately = True
        except asyncio.TimeoutError:
            lock_acquired_immediately = False

        self.assertTrue(lock_acquired_immediately)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

class TestRateLimiterManager(unittest.IsolatedAsyncioTestCase):
    async def test_manager_limiters(self):
        manager = RateLimiterManager(rate=10.0, capacity=5)
        l1 = await manager.get_limiter("user1")
        l2 = await manager.get_limiter("user2")
        
        self.assertNotEqual(l1, l2)
        self.assertEqual(l1.rate, 10.0)

    async def test_manager_try_acquire(self):
        manager = RateLimiterManager(rate=1.0, capacity=1)
        self.assertTrue(await manager.try_acquire("user1"))
        self.assertFalse(await manager.try_acquire("user1"))
        self.assertTrue(await manager.try_acquire("user2"))

if __name__ == "__main__":
    unittest.main()
