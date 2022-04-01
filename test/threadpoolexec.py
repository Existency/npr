from concurrent.futures import ThreadPoolExecutor
import time


def task_1():
    _t = 0
    while _t < 1000:
        _t += 1
        time.sleep(0.03)


def task_2():
    _t = 0
    while _t < 1000:
        _t += 1
        time.sleep(0.03)


def task_3():
    _t = 0
    while _t < 1000:
        _t += 1
        time.sleep(0.03)


def task_4():
    _t = 0
    while _t < 1000:
        _t += 1
        time.sleep(0.03)


def run():

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(task_1)
        executor.submit(task_2)
        executor.submit(task_3)
        executor.submit(task_4)
        executor.shutdown(wait=True)

    print("yey")


if __name__ == "__main__":
    run()
    print("done")
