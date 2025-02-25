import sys
from .wrapper import py_add


def main():
    if len(sys.argv) != 3:
        print("Usage: python -m bluemap <arg1> <arg2>")
        sys.exit(1)

    arg1 = int(sys.argv[1])
    arg2 = int(sys.argv[2])
    result = py_add(arg1, arg2)
    print(f"The result of adding {arg1} and {arg2} is {result}")


if __name__ == "__main__":
    main()
