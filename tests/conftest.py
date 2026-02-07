import pytest

from .mocks import FakeModbusClient

@pytest.fixture
def fake_client():
    # Example initial state: power off; mode auto; some temps.
    regs = {
        100: 0,  # 40101 status (ha_address 100)
        101: 0,  # 40102 mode (ha_address 101)
        140: 25*10, # 40141 outdoor 25.0C (0.1C units)
    }
    return FakeModbusClient(regs)
