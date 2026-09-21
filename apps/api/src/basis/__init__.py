"""Basis API — investment management platform.

The package is organised as a modular monolith with domain-driven design:

* ``basis.kernel`` — shared kernel (money, identifiers, errors, DB, HTTP plumbing).
* ``basis.modules`` — bounded contexts (identity, clients, portfolio, market data,
  analytics), each with ``domain`` / ``application`` / ``infrastructure`` /
  ``presentation`` layers.
"""

__version__ = "0.1.0"
