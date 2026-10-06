CREATE TABLE IF NOT EXISTS users (
    user_id         BIGSERIAL PRIMARY KEY,
    city_id         INT NOT NULL,
    district_id     INT NOT NULL,
    age_group       SMALLINT NOT NULL,
    gender          CHAR(1),
    created_at      TIMESTAMP NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    status          SMALLINT NOT NULL,
    created_at      TIMESTAMP NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    payment_method  SMALLINT,
    updated_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_activities (
    activity_id     BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    event_type      SMALLINT NOT NULL,
    event_time      TIMESTAMP NOT NULL,
    session_id      UUID,
    device_type     SMALLINT
);
