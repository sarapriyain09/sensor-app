CREATE TABLE IF NOT EXISTS telemetry_events (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  factory_id TEXT NOT NULL,
  machine_id TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  temperature_c DOUBLE PRECISION NOT NULL,
  vibration_mm_s DOUBLE PRECISION NOT NULL,
  rpm INTEGER NOT NULL,
  pressure_bar DOUBLE PRECISION NOT NULL,
  state TEXT NOT NULL,
  raw JSONB
);

CREATE INDEX IF NOT EXISTS idx_telemetry_machine_ts ON telemetry_events(machine_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_state_ts ON telemetry_events(state, ts DESC);
