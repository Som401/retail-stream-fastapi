CREATE TABLE IF NOT EXISTS order_lines (
    id            SERIAL PRIMARY KEY,
    invoice       VARCHAR(20) NOT NULL,
    stock_code    VARCHAR(32) NOT NULL,
    description   TEXT,
    quantity      INTEGER NOT NULL,
    invoice_date  TIMESTAMP NOT NULL,
    price         NUMERIC(12, 2) NOT NULL,
    customer_id   INTEGER,
    country       VARCHAR(64),
    year          VARCHAR(16)
);

CREATE INDEX IF NOT EXISTS idx_order_lines_stock_code ON order_lines (stock_code);
CREATE INDEX IF NOT EXISTS idx_order_lines_invoice ON order_lines (invoice);
CREATE INDEX IF NOT EXISTS idx_order_lines_customer ON order_lines (customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_country ON order_lines (country);
CREATE INDEX IF NOT EXISTS idx_order_lines_invoice_date ON order_lines (invoice_date);

CREATE TABLE IF NOT EXISTS products (
    stock_code  VARCHAR(32) PRIMARY KEY,
    description TEXT NOT NULL,
    price       NUMERIC(12, 2) NOT NULL
);
