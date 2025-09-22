# download_dump_script.py
import asyncio
import sys

CITIES = [
    ("San Francisco_CA", "dumps/San-Francisco_CA"),
    ("New Orleans_LA", "dumps/New-Orleans_LA"),
    ("Miami_FL", "dumps/Miami_FL"),
    ("Los Angeles_CA", "dumps/Los-Angeles_CA"),
]


async def run_one(city: str, outdir: str):
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "download_dump.py",
        city,
        outdir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "city": city,
        "outdir": outdir,
        "code": proc.returncode,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
    }


async def download_dump():
    results = await asyncio.gather(
        *(run_one(c, d) for c, d in CITIES), return_exceptions=True
    )
    for r in results:
        if isinstance(r, Exception):
            print(f"[ERROR] {r}")
            continue
        status = "OK" if r["code"] == 0 else f"FAIL ({r['code']})"
        print(f"\n=== {r['city']} -> {r['outdir']} : {status} ===")
        if r["stdout"]:
            print("stdout:\n", r["stdout"].rstrip())
        if r["stderr"]:
            print("stderr:\n", r["stderr"].rstrip())


if __name__ == "__main__":
    asyncio.run(download_dump())
