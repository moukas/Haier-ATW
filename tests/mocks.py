from __future__ import annotations

class FakeModbusClient:
    def __init__(self, registers: dict[int,int] | None = None):
        self.registers = registers or {}
        self.fail_reads = False
        self.fail_writes = False

    async def read_holding(self, address: int, count: int = 1):
        if self.fail_reads:
            raise TimeoutError("Simulated timeout")
        return [int(self.registers.get(address+i, 0)) for i in range(count)]

    async def write_register(self, address: int, value: int):
        if self.fail_writes:
            raise TimeoutError("Simulated timeout")
        self.registers[int(address)] = int(value)
