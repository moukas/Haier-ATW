DOMAIN = "haier_atw_ew11"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TRANSPORT = "transport"
CONF_TIMEOUT = "timeout"
CONF_THROTTLE_MS = "throttle_ms"
CONF_RETRIES = "retries"

DEFAULT_PORT = 8899
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_TIMEOUT = 3.0
DEFAULT_THROTTLE_MS = 60
DEFAULT_RETRIES = 2

TRANSPORT_MODBUS_TCP = "modbus_tcp"
TRANSPORT_RTU_OVER_TCP = "rtu_over_tcp"
TRANSPORT_LEGACY_EW11_RTU_OVER_TCP = "ew11_rtu_over_tcp"
DEFAULT_RTU_OVER_TCP_PORT = 8899
TRANSPORTS = [TRANSPORT_MODBUS_TCP, TRANSPORT_RTU_OVER_TCP]

REGISTER_BASE = 40001

# Special points with write behavior / UI types
SPECIAL = {
  "power": {"register": 40001, "verify_register": 40101},
  "mode": {"register": 40002, "verify_register": 40102},
  "zone1_sp": {"register": 40003, "verify_register": 40103, "step": 0.5, "min": 0, "max": 80, "scale_write": 2.0, "scale_read": 0.5},
  "zone2_sp": {"register": 40004, "verify_register": 40104, "step": 0.5, "min": 0, "max": 80, "scale_write": 2.0, "scale_read": 0.5},
  "dhw_sp": {"register": 40005, "verify_register": 40105, "step": 0.5, "min": 0, "max": 80, "scale_write": 2.0, "scale_read": 0.5},
  "pool_sp": {"register": 40006, "verify_register": 40106, "step": 0.5, "min": 0, "max": 80, "scale_write": 2.0, "scale_read": 0.5},
  "steril_sp": {"register": 40007, "verify_register": 40107, "step": 1.0, "min": 0, "max": 80, "scale_write": 1.0, "scale_read": 1.0},
  "eco": {"register": 40008, "verify_register": 40110},
  "fast_dhw": {"register": 40009, "verify_register": 40111},
}

MODE_OPTIONS = {
  0: "Auto",
  1: "Cool",
  2: "Heat",
  3: "DHW",
  4: "Pool",
  5: "Heat+Pool",
  6: "Auto+DHW",
  7: "Cool+DHW",
  8: "Heat+DHW",
}
