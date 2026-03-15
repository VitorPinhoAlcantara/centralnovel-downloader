#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from centralnovel.menus import menu_principal


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\nInterrompido")
    except Exception as exc:
        print(f"\n[ERRO] {exc}")

