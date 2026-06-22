#!/usr/bin/env python3
"""Stage 3: load parsed rows into PostGIS."""
from mariupol_seizures.db import load

if __name__ == "__main__":
    load.run()
