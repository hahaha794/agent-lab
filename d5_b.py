#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

def level1()->None:
    level2()

def level2()->None:
    level3()

def level3()->None:
    _ = int("abc")

def main()->None:
    level1()

if __name__ == '__main__':
    main()