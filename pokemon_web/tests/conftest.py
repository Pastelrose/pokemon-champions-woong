# -*- coding: utf-8 -*-
"""tests 폴더에서 pokemon_web 모듈(queries, db)을 import할 수 있게 경로 추가."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
