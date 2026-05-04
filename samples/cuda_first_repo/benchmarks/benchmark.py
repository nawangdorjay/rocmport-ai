import subprocess
import time


def main():
    subprocess.run(["nvidia-smi"], check=False)
    start = time.perf_counter()
    time.sleep(0.1)
    print({"latency_ms": (time.perf_counter() - start) * 1000})


if __name__ == "__main__":
    main()
