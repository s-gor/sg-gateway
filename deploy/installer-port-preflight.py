#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import os
import socket
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PortSpec:
    label: str
    protocol: str
    port: int
    scope: str = "public"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for name in (
        "panel", "xray", "awg", "mieru", "xhttp_reality", "xhttp_tls",
        "hysteria2", "anytls", "tuic", "hostd", "backend",
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=int, required=True)
    return parser.parse_args()


def port_specs(args: argparse.Namespace) -> list[PortSpec]:
    return [
        PortSpec("Nginx HTTP / ACME", "tcp", 80),
        PortSpec("Панель SG-Gateway", "tcp", args.panel),
        PortSpec("VLESS Reality TCP", "tcp", args.xray),
        PortSpec("Mieru", "tcp", args.mieru),
        PortSpec("VLESS XHTTP Reality", "tcp", args.xhttp_reality),
        PortSpec("VLESS XHTTP TLS", "tcp", args.xhttp_tls),
        PortSpec("AnyTLS", "tcp", args.anytls),
        PortSpec("SG-HostD", "tcp", args.hostd, "loopback"),
        PortSpec("Backend панели", "tcp", args.backend, "loopback"),
        PortSpec("AmneziaWG", "udp", args.awg),
        PortSpec("Hysteria2", "udp", args.hysteria2),
        PortSpec("TUIC v5", "udp", args.tuic),
    ]


def duplicate_errors(items: list[PortSpec]) -> list[str]:
    grouped: dict[tuple[str, int], list[str]] = {}
    errors: list[str] = []
    for item in items:
        if not 1 <= item.port <= 65535:
            errors.append(f"{item.label}: недопустимый порт {item.port}")
            continue
        grouped.setdefault((item.protocol, item.port), []).append(item.label)
    for (protocol, port), labels in grouped.items():
        if len(labels) > 1:
            errors.append(
                f"{port}/{protocol.upper()} одновременно назначен: " + ", ".join(labels)
            )
    return errors


def bind_check(item: PortSpec, family: socket.AddressFamily) -> tuple[bool, str]:
    sock_type = socket.SOCK_STREAM if item.protocol == "tcp" else socket.SOCK_DGRAM
    if family == socket.AF_INET:
        host = "127.0.0.1" if item.scope == "loopback" else "0.0.0.0"
        address = (host, item.port)
    else:
        host = "::1" if item.scope == "loopback" else "::"
        address = (host, item.port, 0, 0)
    sock = socket.socket(family, sock_type)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        if family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.bind(address)
        if sock_type == socket.SOCK_STREAM:
            sock.listen(1)
        return True, ""
    except OSError as exc:
        if family == socket.AF_INET6 and exc.errno in {
            errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL,
        }:
            return True, "IPv6 недоступен"
        return False, os.strerror(exc.errno) if exc.errno else str(exc)
    finally:
        sock.close()


def socket_inodes(protocol: str, port: int) -> set[str]:
    names = (
        ("/proc/net/tcp", "/proc/net/tcp6")
        if protocol == "tcp"
        else ("/proc/net/udp", "/proc/net/udp6")
    )
    wanted = f"{port:04X}"
    result: set[str] = set()
    for name in names:
        try:
            lines = Path(name).read_text(encoding="ascii", errors="ignore").splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 10:
                continue
            if fields[1].rpartition(":")[2].upper() != wanted:
                continue
            if protocol == "tcp" and fields[3] != "0A":
                continue
            result.add(fields[9])
    return result


def owners(protocol: str, port: int) -> list[str]:
    inodes = socket_inodes(protocol, port)
    if not inodes:
        return []
    found: list[str] = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            fds = list((proc / "fd").iterdir())
        except OSError:
            continue
        matched = False
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                matched = True
                break
        if not matched:
            continue
        try:
            command = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            ).strip()
        except OSError:
            command = ""
        try:
            name = (proc / "comm").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            name = "unknown"
        found.append(f"PID {proc.name}; процесс={name}; команда={command or name}")
    return sorted(set(found))


def main() -> int:
    items = port_specs(arguments())
    errors = duplicate_errors(items)
    if errors:
        print("[SG-Gateway] [PORT ERROR] Конфликт портов в параметрах установки:")
        for error in errors:
            print("  - " + error)
        return 1

    print("[SG-Gateway] Проверка обязательных портов до изменения сервера:")
    conflicts: list[tuple[PortSpec, list[str]]] = []
    for item in items:
        failures: list[str] = []
        for family, label in ((socket.AF_INET, "IPv4"), (socket.AF_INET6, "IPv6")):
            ok, note = bind_check(item, family)
            if not ok:
                failures.append(f"{label}: {note}")
        if failures:
            conflicts.append((item, failures))
            print(f"  [ЗАНЯТ] {item.port}/{item.protocol.upper():3} — {item.label}")
        else:
            print(f"  [OK]    {item.port}/{item.protocol.upper():3} — {item.label}")

    if not conflicts:
        print("[SG-Gateway] [OK] Все обязательные TCP/UDP-порты свободны.")
        return 0

    print("\n[SG-Gateway] [PORT ERROR] Установка остановлена до backup и копирования файлов.")
    for item, failures in conflicts:
        print(f"\n{item.label}: {item.port}/{item.protocol.upper()}")
        for failure in failures:
            print("  " + failure)
        details = owners(item.protocol, item.port)
        for detail in details or ["Процесс не определён через /proc; проверьте ss -lntup."]:
            print("  " + detail)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
