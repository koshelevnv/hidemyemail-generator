import asyncio
import os
import datetime
import re
from typing import Optional, List
from rich.console import Console
from rich.text import Text
from rich.prompt import IntPrompt
from rich.table import Table

from icloud import HideMyEmail


class RichHideMyEmail(HideMyEmail):
    _cookie_file = "cookie.txt"

    def __init__(self):
        super().__init__()
        self.console = Console()
        self.table = Table()
        if os.path.exists(self._cookie_file):
            with open(self._cookie_file, "r") as f:
                self.cookies = [line for line in f if not line.startswith("//")][0]
        else:
            self.console.log('[bold yellow][WARN][/] No "cookie.txt" file found!')

    async def _generate_one(self) -> Optional[str]:
        gen_res = await self.generate_email()
        if not gen_res or not gen_res.get("success"):
            reason = gen_res.get("reason") or gen_res.get("error", {}).get("errorMessage", "Unknown")
            self.console.log(f"[bold red][ERR][/] Failed to generate email: {reason}")
            return None

        email = gen_res["result"]["hme"]
        self.console.log(f'[50%] "{email}" - Generated')

        reserve_res = await self.reserve_email(email)
        if not reserve_res or not reserve_res.get("success"):
            reason = reserve_res.get("reason") or reserve_res.get("error", {}).get("errorMessage", "Unknown")

            # Check for Apple rate limit message
            if isinstance(reason, str) and "you have reached the limit" in reason.lower():
                self.console.log(
                    f'[bold yellow][!] Rate limit reached. Waiting 60 minutes...'
                )
                await asyncio.sleep(3600)
                return None

            self.console.log(f'[bold red][ERR][/] "{email}" - Failed to reserve: {reason}')
            return None

        self.console.log(f'[100%] "{email}" - Reserved')
        return email

    async def generate(self, total_count: int):
        self.console.rule()
        self.console.log(f"🔧 Starting generation of {total_count} email(s)...")
        self.console.rule()

        all_emails = set()
        generated = 0

        while generated < total_count:
            batch_count = 0

            while batch_count < 5 and generated < total_count:
                email = await self._generate_one()
                if not email:
                    continue
                if email in all_emails:
                    self.console.log(f"[yellow][!] Duplicate detected: {email}, skipping...")
                    continue

                all_emails.add(email)
                generated += 1
                batch_count += 1

                with open("emails.txt", "a+") as f:
                    f.write(email.strip() + "\n")

                self.console.log(f"[green]Saved {generated}/{total_count}")
                await asyncio.sleep(10)

            if generated < total_count:
                self.console.log(f"[cyan]⏸️  Batch complete. Waiting 1 hour before continuing...")
                await asyncio.sleep(3600)

        self.console.rule()
        self.console.log(f"[bold green]✅ Done! Generated {generated} unique email(s).")


async def main():
    console = Console()
    s = IntPrompt.ask(
        Text.assemble(("Сколько адресов iCloud нужно сгенерировать?")),
        console=console,
    )
    count = int(s)

    async with RichHideMyEmail() as hme:
        await hme.generate(count)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Остановка пользователем.")
