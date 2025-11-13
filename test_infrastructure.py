"""Test script to verify connection to TG Infrastructure Stack.

Tests Redis, Loki, and Pushgateway connectivity.
"""

import os
import sys
from datetime import datetime


def test_redis() -> bool:
    """Test Redis connection."""
    print("=" * 60)
    print("Testing Redis connection...")
    print("=" * 60)

    try:
        import redis

        redis_host = os.getenv("REDIS_HOST", "tg-redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", "")

        print(f"Connecting to Redis: {redis_host}:{redis_port}")

        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password if redis_password else None,
            decode_responses=True,
        )

        # Test PING
        result = r.ping()
        print(f"✅ Redis PING: {result}")

        # Test SET/GET
        test_key = "test_connection"
        test_value = f"Connected at {datetime.now().isoformat()}"
        r.set(test_key, test_value)
        retrieved = r.get(test_key)
        print(f"✅ Redis SET/GET: {retrieved}")

        # Test PUBLISH
        channel = "tg_events"
        message = (
            '{"event": "test.connection", "service": "telegram-fetcher", "timestamp": "'
            + datetime.now().isoformat()
            + '"}'
        )
        r.publish(channel, message)
        print(f"✅ Redis PUBLISH to channel '{channel}': OK")

        print("✅ Redis: ALL TESTS PASSED")
        return True

    except ImportError:
        print("❌ Redis library not installed: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def test_loki() -> bool:
    """Test Loki connection."""
    print("\n" + "=" * 60)
    print("Testing Loki connection...")
    print("=" * 60)

    try:
        import requests

        loki_url = os.getenv("LOKI_URL", "http://tg-loki:3100")

        print(f"Connecting to Loki: {loki_url}")

        # Test ready endpoint
        response = requests.get(f"{loki_url}/ready", timeout=5)
        print(f"✅ Loki /ready: {response.status_code} - {response.text.strip()}")

        # Test metrics endpoint
        response = requests.get(f"{loki_url}/metrics", timeout=5)
        print(f"✅ Loki /metrics: {response.status_code} - metrics available")

        # Test push logs
        log_entry = {
            "streams": [
                {
                    "stream": {
                        "job": "telegram-fetcher",
                        "level": "INFO",
                        "service": "telegram-fetcher",
                    },
                    "values": [
                        [
                            # nanosecond timestamp
                            str(int(datetime.now().timestamp() * 1e9)),
                            (
                                '{"message": "Test log", "timestamp": "'
                                + datetime.now().isoformat()
                                + '"}'
                            ),
                        ]
                    ],
                }
            ]
        }

        response = requests.post(
            f"{loki_url}/loki/api/v1/push",
            json=log_entry,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        print(f"✅ Loki push log: {response.status_code}")

        print("✅ Loki: ALL TESTS PASSED")
        return True

    except ImportError:
        print("❌ Requests library not installed: pip install requests")
        return False
    except Exception as e:
        print(f"❌ Loki connection failed: {e}")
        return False


def test_pushgateway() -> bool:
    """Test Pushgateway connection."""
    print("\n" + "=" * 60)
    print("Testing Pushgateway connection...")
    print("=" * 60)

    try:
        from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

        pushgateway_url = os.getenv("PUSHGATEWAY_URL", "http://tg-pushgateway:9091")

        # Remove http:// prefix for prometheus_client
        gateway = pushgateway_url.replace("http://", "").replace("https://", "")

        print(f"Connecting to Pushgateway: {pushgateway_url}")

        # Create test metric
        registry = CollectorRegistry()
        test_metric = Gauge(
            "infrastructure_test_timestamp",
            "Test metric from infrastructure test",
            registry=registry,
        )
        test_metric.set(datetime.now().timestamp())

        # Push to gateway
        push_to_gateway(gateway, job="telegram-fetcher-test", registry=registry)

        print("✅ Pushgateway push metric: OK")
        print("✅ Pushgateway: ALL TESTS PASSED")
        return True

    except ImportError:
        print("❌ Prometheus client not installed: pip install prometheus-client")
        return False
    except Exception as e:
        print(f"❌ Pushgateway connection failed: {e}")
        return False


def main() -> int:
    """Run all infrastructure tests."""
    print("\n" + "=" * 60)
    print("TG Infrastructure Stack - Connection Test")
    print("=" * 60)
    print(f"Date: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {
        "redis": test_redis(),
        "loki": test_loki(),
        "pushgateway": test_pushgateway(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for service, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{service.upper():20s} {status}")

    all_passed = all(results.values())

    print("=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Infrastructure is ready!")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED - Check logs above")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
