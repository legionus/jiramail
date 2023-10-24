#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import base64
import binascii
import hashlib
import hmac
import os
import random
import time

from typing import Callable, Tuple, Any

import jiramail

logger = jiramail.logger

def cram_md5(user: str, password: str, interact: Callable[[Any, str], str], data: Any) -> Tuple[bool, str]:
    pid = os.getpid()
    now = time.time_ns()
    rnd = random.randrange(2**32 - 1)
    shared = f"<{pid}.{now}.{rnd}@jiramail>"

    line = interact(data, base64.b64encode(shared.encode()).decode())

    try:
        buf = base64.standard_b64decode(line).decode()
    except binascii.Error:
        return (False, "couldn't decode your credentials")

    fields = buf.split(" ")

    if len(fields) != 2:
        return (False, "wrong number of fields in the token")

    hexdigest = hmac.new(password.encode(),
                         shared.encode(),
                         hashlib.md5).hexdigest()

    if hmac.compare_digest(user, fields[0]) and hmac.compare_digest(hexdigest, fields[1]):
        return (True, "authentication successful")

    return (False, "authenticate failure")
