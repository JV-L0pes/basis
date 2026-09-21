-- Basis — local database bootstrap
-- Runs once on first container start (docker-entrypoint-initdb.d).
-- The main database (basis) is created by POSTGRES_DB; this adds the test database.

CREATE DATABASE basis_test OWNER basis;
