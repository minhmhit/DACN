-- Seed smoke-test (khớp MAX_USER_ID=20000 mặc định trong script benchmark)
-- Chỉ chạy 1 lần khi volume trống. Muốn seed lại: docker compose down -v

INSERT INTO users (user_id, city_id, district_id, age_group, gender, created_at, is_active)
SELECT
    g,
    1 + (g % 63),
    (1 + (g % 63)) * 100 + 1 + (g % 20),
    1 + (g % 4),
    CASE WHEN g % 2 = 0 THEN 'M' ELSE 'F' END,
    TIMESTAMP '2020-01-01' + ((g % 1800) || ' days')::interval,
    (g % 12) <> 0
FROM generate_series(1, 20000) AS g;

INSERT INTO orders (order_id, user_id, status, created_at, amount, payment_method, updated_at)
SELECT
    g,
    1 + (g % 20000),
    1 + (g % 5),
    NOW() - ((g % 400) || ' days')::interval - ((g % 86400) || ' seconds')::interval,
    (50000 + (g % 5000000))::numeric,
    1 + (g % 4),
    NOW() - ((g % 200) || ' days')::interval
FROM generate_series(1, 80000) AS g;

INSERT INTO user_activities (activity_id, user_id, event_type, event_time, session_id, device_type)
SELECT
    g,
    1 + (g % 20000),
    1 + (g % 6),
    NOW() - ((g % 120) || ' days')::interval - ((g % 86400) || ' seconds')::interval,
    gen_random_uuid(),
    1 + (g % 3)
FROM generate_series(1, 120000) AS g;

ANALYZE users;
ANALYZE orders;
ANALYZE user_activities;
