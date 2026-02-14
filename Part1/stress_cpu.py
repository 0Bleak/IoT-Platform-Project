import time
import argparse

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=int, default=130)
    args = p.parse_args()

    end = time.time() + args.seconds
    while time.time() < end:
        x = 0
        for _ in range(200_000):
            x += 1
        if x < 0:
            print(x)

if __name__ == "__main__":
    main()
