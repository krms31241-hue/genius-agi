import os
import sys
import platform
import socket
import subprocess
import json
import re
import uuid
import time
import logging
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)


class SystemResourceDetector:
    """
    Independent hardware layer for real machine resource discovery.
    Uses psutil if available, otherwise falls back to standard library and OS-specific tools.
    """

    def detect(self) -> dict:
        """
        Collects and returns real machine information.
        """
        return {
            "cpu": self._detect_cpu(),
            "memory": self._detect_memory(),
            "disk": self._detect_disk(),
            "os": self._detect_os(),
            "python": self._detect_python(),
            "gpu": self._detect_gpu(),
            "network": self._detect_network(),
            "storage": self._detect_storage()
        }

    def _detect_cpu(self) -> dict:
        cpu_info = {
            "physical_cores": 0,
            "logical_cores": 0,
            "cpu_frequency": 0.0,
            "architecture": platform.machine(),
            "processor_name": platform.processor() or "Unknown",
            "current_cpu_usage_percent": 0.0
        }

        if HAS_PSUTIL:
            try:
                cpu_info["physical_cores"] = psutil.cpu_count(logical=False) or 0
                cpu_info["logical_cores"] = psutil.cpu_count(logical=True) or 0
                freq = psutil.cpu_freq()
                if freq:
                    cpu_info["cpu_frequency"] = round(freq.current, 2)
                cpu_info["current_cpu_usage_percent"] = psutil.cpu_percent(interval=0.1)
            except Exception as e:
                logger.error(f"psutil CPU detection failed: {e}")
        else:
            cpu_info["logical_cores"] = os.cpu_count() or 0
            cpu_info["physical_cores"] = self._get_physical_cores_fallback()
            cpu_info["cpu_frequency"] = self._get_cpu_freq_fallback()
            cpu_info["current_cpu_usage_percent"] = self._get_cpu_usage_fallback()
            if not cpu_info["processor_name"] or cpu_info["processor_name"] == "Unknown":
                cpu_info["processor_name"] = self._get_processor_name_fallback()

        return cpu_info

    def _get_physical_cores_fallback(self) -> int:
        try:
            if platform.system() == "Linux":
                try:
                    out = subprocess.check_output(['lscpu'], text=True, timeout=2)
                    cores_per_socket = sockets = 1
                    for line in out.splitlines():
                        if 'Core(s) per socket:' in line:
                            cores_per_socket = int(line.split(':')[1].strip())
                        if 'Socket(s):' in line:
                            sockets = int(line.split(':')[1].strip())
                    return cores_per_socket * sockets
                except Exception:
                    with open('/proc/cpuinfo', 'r') as f:
                        content = f.read()
                    physical_ids = set(re.findall(r'physical id\s*:\s*(\d+)', content))
                    cpu_cores = re.findall(r'cpu cores\s*:\s*(\d+)', content)
                    if physical_ids and cpu_cores:
                        return len(physical_ids) * int(cpu_cores[0])
            elif platform.system() == "Darwin":
                out = subprocess.check_output(['sysctl', '-n', 'hw.physicalcpu'], text=True, timeout=2)
                return int(out.strip())
            elif platform.system() == "Windows":
                out = subprocess.check_output(['wmic', 'cpu', 'get', 'NumberOfCores'], text=True, timeout=2)
                for line in out.splitlines():
                    line = line.strip()
                    if line and line != 'NumberOfCores':
                        return int(line)
        except Exception as e:
            logger.error(f"Physical cores fallback failed: {e}")
        return 0

    def _get_cpu_freq_fallback(self) -> float:
        try:
            if platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'cpu MHz' in line:
                            return round(float(line.split(':')[1].strip()), 2)
            elif platform.system() == "Darwin":
                out = subprocess.check_output(['sysctl', '-n', 'hw.cpufrequency'], text=True, timeout=2)
                return round(int(out.strip()) / 1000000.0, 2)
            elif platform.system() == "Windows":
                out = subprocess.check_output(['wmic', 'cpu', 'get', 'MaxClockSpeed'], text=True, timeout=2)
                for line in out.splitlines():
                    line = line.strip()
                    if line and line != 'MaxClockSpeed':
                        return float(line)
        except Exception as e:
            logger.error(f"CPU freq fallback failed: {e}")
        return 0.0

    def _get_cpu_usage_fallback(self) -> float:
        try:
            if platform.system() == "Linux":
                with open('/proc/stat', 'r') as f:
                    line1 = f.readline()
                times1 = [int(x) for x in line1.split()[1:]]
                time.sleep(0.1)
                with open('/proc/stat', 'r') as f:
                    line2 = f.readline()
                times2 = [int(x) for x in line2.split()[1:]]
                
                delta = [t2 - t1 for t1, t2 in zip(times1, times2)]
                total = sum(delta)
                idle = delta[3]
                if total == 0:
                    return 0.0
                return round((1.0 - idle / total) * 100.0, 2)
        except Exception as e:
            logger.error(f"CPU usage fallback failed: {e}")
        return 0.0

    def _get_processor_name_fallback(self) -> str:
        try:
            if platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
            elif platform.system() == "Darwin":
                out = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True, timeout=2)
                return out.strip()
            elif platform.system() == "Windows":
                out = subprocess.check_output(['wmic', 'cpu', 'get', 'name'], text=True, timeout=2)
                for line in out.splitlines():
                    line = line.strip()
                    if line and line != 'Name':
                        return line
        except Exception as e:
            logger.error(f"Processor name fallback failed: {e}")
        return "Unknown"

    def _detect_memory(self) -> dict:
        mem_info = {"total": 0, "available": 0, "used": 0, "percent": 0.0}
        
        if HAS_PSUTIL:
            try:
                mem = psutil.virtual_memory()
                mem_info.update({
                    "total": mem.total,
                    "available": mem.available,
                    "used": mem.used,
                    "percent": mem.percent
                })
            except Exception as e:
                logger.error(f"psutil memory detection failed: {e}")
        else:
            try:
                if platform.system() == "Linux":
                    with open('/proc/meminfo', 'r') as f:
                        lines = f.read()
                    total = int(re.search(r'MemTotal:\s+(\d+)', lines).group(1)) * 1024
                    available = int(re.search(r'MemAvailable:\s+(\d+)', lines).group(1)) * 1024
                    used = total - available
                    mem_info.update({
                        "total": total,
                        "available": available,
                        "used": used,
                        "percent": round((used / total) * 100, 2) if total > 0 else 0.0
                    })
                elif platform.system() == "Darwin":
                    out = subprocess.check_output(['sysctl', '-n', 'hw.memsize'], text=True, timeout=2)
                    total = int(out.strip())
                    # Fallback for available on macOS without psutil is complex, approximating
                    vm_stat = subprocess.check_output(['vm_stat'], text=True, timeout=2)
                    pages_free = int(re.search(r'Pages free:\s+(\d+)', vm_stat).group(1))
                    pages_inactive = int(re.search(r'Pages inactive:\s+(\d+)', vm_stat).group(1))
                    page_size = 4096 # Default, could be parsed but 4096 is standard for modern Macs
                    available = (pages_free + pages_inactive) * page_size
                    used = total - available
                    mem_info.update({
                        "total": total,
                        "available": max(0, available),
                        "used": max(0, used),
                        "percent": round((used / total) * 100, 2) if total > 0 else 0.0
                    })
                elif platform.system() == "Windows":
                    import ctypes
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [
                            ("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                        ]
                    stat = MEMORYSTATUSEX()
                    stat.dwLength = ctypes.sizeof(stat)
                    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                    total = stat.ullTotalPhys
                    available = stat.ullAvailPhys
                    used = total - available
                    mem_info.update({
                        "total": total,
                        "available": available,
                        "used": used,
                        "percent": float(stat.dwMemoryLoad)
                    })
            except Exception as e:
                logger.error(f"Memory fallback failed: {e}")
                
        return mem_info

    def _detect_disk(self) -> dict:
        disk_info = {"total": 0, "free": 0, "used": 0, "percent": 0.0}
        path = '/' if platform.system() != 'Windows' else 'C:\\'
        
        if HAS_PSUTIL:
            try:
                usage = psutil.disk_usage(path)
                disk_info.update({
                    "total": usage.total,
                    "free": usage.free,
                    "used": usage.used,
                    "percent": usage.percent
                })
            except Exception as e:
                logger.error(f"psutil disk detection failed: {e}")
        else:
            try:
                if platform.system() == "Windows":
                    import ctypes
                    free_bytes = ctypes.c_ulonglong(0)
                    total_bytes = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(path), None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes)
                    )
                    total = total_bytes.value
                    free = free_bytes.value
                    used = total - free
                    disk_info.update({
                        "total": total,
                        "free": free,
                        "used": used,
                        "percent": round((used / total) * 100, 2) if total > 0 else 0.0
                    })
                else:
                    st = os.statvfs(path)
                    total = st.f_blocks * st.f_frsize
                    free = st.f_bavail * st.f_frsize
                    used = total - free
                    disk_info.update({
                        "total": total,
                        "free": free,
                        "used": used,
                        "percent": round((used / total) * 100, 2) if total > 0 else 0.0
                    })
            except Exception as e:
                logger.error(f"Disk fallback failed: {e}")
                
        return disk_info

    def _detect_os(self) -> dict:
        return {
            "operating_system": platform.system(),
            "version": platform.version(),
            "kernel": platform.release(),
            "hostname": socket.gethostname()
        }

    def _detect_python(self) -> dict:
        return {"python_version": sys.version}

    def _detect_gpu(self) -> list:
        gpus = []
        try:
            if platform.system() == "Windows":
                out = subprocess.check_output(['wmic', 'path', 'win32_VideoController', 'get', 'name'], text=True, timeout=5)
                for line in out.splitlines():
                    line = line.strip()
                    if line and line != 'Name':
                        gpus.append(line)
            elif platform.system() == "Darwin":
                out = subprocess.check_output(['system_profiler', 'SPDisplaysDataType', '-json'], text=True, timeout=5)
                data = json.loads(out)
                for item in data.get('SPDisplaysDataType', []):
                    if 'sppci_model' in item:
                        gpus.append(item['sppci_model'])
                    elif '_name' in item:
                        gpus.append(item['_name'])
            else:
                # Linux
                try:
                    out = subprocess.check_output(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], text=True, timeout=5)
                    for line in out.splitlines():
                        if line.strip():
                            gpus.append(line.strip())
                except Exception:
                    try:
                        out = subprocess.check_output(['lspci'], text=True, timeout=5)
                        for line in out.splitlines():
                            if re.search(r'vga|3d|display', line, re.IGNORECASE):
                                gpus.append(line.split(':', 1)[1].strip())
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"GPU detection failed: {e}")
            
        return gpus

    def _detect_network(self) -> dict:
        hostname = socket.gethostname()
        local_ip = "127.0.0.1"
        mac_address = "00:00:00:00:00:00"
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            except Exception:
                pass
            finally:
                s.close()
        except Exception as e:
            logger.error(f"Local IP detection failed: {e}")

        try:
            if platform.system() == "Linux":
                for iface in os.listdir('/sys/class/net'):
                    if iface == 'lo':
                        continue
                    try:
                        with open(f'/sys/class/net/{iface}/address', 'r') as f:
                            mac = f.read().strip()
                            if mac and mac != '00:00:00:00:00:00':
                                mac_address = mac
                                break
                    except Exception:
                        continue
            elif platform.system() == "Darwin":
                out = subprocess.check_output(['ifconfig', 'en0'], text=True, timeout=2)
                match = re.search(r'ether\s+([0-9a-f:]+)', out)
                if match:
                    mac_address = match.group(1)
            elif platform.system() == "Windows":
                out = subprocess.check_output(['getmac', '/fo', 'csv', '/nh'], text=True, timeout=2)
                for line in out.splitlines():
                    parts = line.split(',')
                    if len(parts) > 0:
                        mac = parts[0].strip().replace('-', ':')
                        if mac and mac != '00:00:00:00:00:00':
                            mac_address = mac
                            break
        except Exception as e:
            logger.error(f"MAC address detection failed: {e}")
            # Ultimate fallback
            mac_int = uuid.getnode()
            mac_hex = hex(mac_int)[2:].zfill(12)
            mac_address = ':'.join(mac_hex[i:i+2] for i in range(0, 12, 2))

        return {
            "hostname": hostname,
            "local_ip": local_ip,
            "mac_address": mac_address
        }

    def _detect_storage(self) -> dict:
        storage_type = "unknown"
        try:
            if platform.system() == "Linux":
                for block in os.listdir('/sys/block'):
                    if block.startswith(('sd', 'nvme', 'vd')):
                        try:
                            with open(f'/sys/block/{block}/queue/rotational', 'r') as f:
                                val = f.read().strip()
                                if val == '0':
                                    storage_type = "ssd"
                                elif val == '1':
                                    storage_type = "hdd"
                                break
                        except Exception:
                            continue
            elif platform.system() == "Darwin":
                out = subprocess.check_output(['system_profiler', 'SPStorageDataType'], text=True, timeout=5)
                if 'Solid State' in out or 'SSD' in out:
                    storage_type = "ssd"
                elif 'Rotational' in out or 'HDD' in out:
                    storage_type = "hdd"
            elif platform.system() == "Windows":
                out = subprocess.check_output(['wmic', 'diskdrive', 'get', 'mediatype'], text=True, timeout=5)
                if 'Fixed hard disk media' in out:
                    # WMI is often unreliable for SSD vs HDD, but we check for SSD keywords
                    if 'SSD' in out.upper():
                        storage_type = "ssd"
                    else:
                        storage_type = "hdd" # Default assumption if not explicitly SSD
                elif 'SSD' in out.upper():
                    storage_type = "ssd"
        except Exception as e:
            logger.error(f"Storage detection failed: {e}")
            
        return {"type": storage_type}
