import colorama

colorama.just_fix_windows_console()

RESET = colorama.Style.RESET_ALL


def print_assert(msg: str, passed: bool) -> None:
    prefix = f"Check: {msg} " if msg else "Check: "
    word = "SUCCESS" if passed else "FAILURE"
    color = colorama.Fore.GREEN if passed else colorama.Fore.RED
    print(f"{prefix}[{color}{word}{RESET}]")


def print_test_summary(test_name: str, passed: int, failed: int) -> None:
    total = passed + failed
    color = colorama.Fore.GREEN if failed == 0 else colorama.Fore.RED
    print(
        f"{colorama.Fore.BLUE}Test '{test_name}' finished:{RESET} ",
        end="",
    )
    if failed == 0:
        print(f"{color}all passed{RESET} - {color}{passed}{RESET}/{total}")
    else:
        print(f"{color}{failed} failed{RESET} - {color}{passed}{RESET}/{total}")


def print_test_start(test_name: str) -> None:
    print(f"{colorama.Fore.BLUE}Starting test '{test_name}'...{RESET}")
