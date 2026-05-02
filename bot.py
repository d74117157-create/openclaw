"""
BOT FACTORY — Digital Empire
==============================
Discord command → Groq generates bot → GitHub repo → Railway deploys → Status returned

Install: pip install discord.py requests groq
Run: python bot_factory.py

ENV VARS (already in Railway):
  DISCORD_TOKEN     = your discord bot token
  GITHUB_TOKEN      = ghp_... (repo scope)
  GITHUB_USERNAME   = your GitHub username
  GROQ_API_KEY      = already set ✅
  GROQ_MODEL        = already set ✅ (e.g. llama3-70b-8192)
"""

import os, re, json, time, base64, asyncio
import requests
import discord
from discord.ext import commands

# ─── CONFIG ────────────────────────────────────────────────────────────────────

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_TOKEN", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USERNAME   = os.environ.get("GITHUB_USERNAME", "")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL        = os.environ.get("GROQ_MODEL", "llama3-70b-8192")

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

GROQ_HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}

# ─── GROQ CLIENT ───────────────────────────────────────────────────────────────

def ask_groq(system: str, user: str, max_tokens: int = 2000) -> str:
    payload = {
        "model": GROQ_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=GROQ_HEADERS,
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# ─── GITHUB FUNCTIONS ──────────────────────────────────────────────────────────

def create_repo(repo_name: str, description: str = "") -> dict:
    payload = {
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": False,
    }
    r = requests.post("https://api.github.com/user/repos", headers=GITHUB_HEADERS, json=payload)
    return r.json()


def push_file(repo_name: str, file_path: str, content: str, commit_msg: str = "Initial commit") -> dict:
    encoded = base64.b64encode(content.encode()).decode()
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_path}"
    payload = {"message": commit_msg, "content": encoded}
    r = requests.put(url, headers=GITHUB_HEADERS, json=payload)
    return r.json()


def push_multiple_files(repo_name: str, files: dict, commit_msg: str = "Bot factory deploy") -> bool:
    ref_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/refs/heads/main"
    ref_r = requests.get(ref_url, headers=GITHUB_HEADERS)
    if ref_r.status_code != 200:
        ref_url = ref_url.replace("/main", "/master")
        ref_r = requests.get(ref_url, headers=GITHUB_HEADERS)
    if ref_r.status_code != 200:
        for path, content in files.items():
            push_file(repo_name, path, content, commit_msg)
        return True

    base_sha = ref_r.json()["object"]["sha"]
    blobs = []
    for file_path, content in files.items():
        blob_r = requests.post(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/blobs",
            headers=GITHUB_HEADERS,
            json={"content": content, "encoding": "utf-8"}
        )
        blobs.append({"path": file_path, "mode": "100644", "type": "blob", "sha": blob_r.json()["sha"]})

    tree_r = requests.post(
        f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/trees",
        headers=GITHUB_HEADERS,
        json={"base_tree": base_sha, "tree": blobs}
    )
    commit_r = requests.post(
        f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/commits",
        headers=GITHUB_HEADERS,
        json={"message": commit_msg, "tree": tree_r.json()["sha"], "parents": [base_sha]}
    )
    requests.patch(ref_url, headers=GITHUB_HEADERS, json={"sha": commit_r.json()["sha"]})
    return True


def init_repo_with_readme(repo_name: str):
    push_file(repo_name, "README.md", f"# {repo_name}\nDeployed via Digital Empire Bot Factory.")


def get_repo_url(repo_name: str) -> str:
    return f"https://github.com/{GITHUB_USERNAME}/{repo_name}"

# ─── CODE GENERATOR ────────────────────────────────────────────────────────────

BOT_SYSTEM_PROMPT = """You are a Python bot code generator for the Digital Empire swarm.
Generate complete, working Python bot code based on the user's description.
Output ONLY raw Python code — no markdown, no backticks, no explanation.
The code must:
- Use discord.py if it's a Discord bot
- Be self-contained in one file
- Read DISCORD_BOT_TOKEN from os.environ
- Include at the very end as a Python comment: # REQUIREMENTS: discord.py,requests
- Work in a Railway deployment
- Be production-ready and functional"""

def generate_bot_code(description: str) -> tuple:
    raw = ask_groq(BOT_SYSTEM_PROMPT, f"Build this bot: {description}")
    req_match = re.search(r"# REQUIREMENTS:\s*(.+)", raw)
    reqs = [r.strip() for r in req_match.group(1).split(",")] if req_match else ["discord.py", "requests"]
    requirements_txt = "\n".join(reqs)
    bot_code = re.sub(r"\n# REQUIREMENTS:.*", "", raw).strip()
    slug = re.sub(r"[^a-z0-9]", "-", description.lower())[:30].strip("-")
    repo_name = f"empire-{slug}-{int(time.time()) % 10000}"
    return bot_code, requirements_txt, repo_name


def generate_railway_config() -> str:
    return json.dumps({
        "$schema": "https://railway.app/railway.schema.json",
        "build": {"builder": "NIXPACKS"},
        "deploy": {
            "startCommand": "python bot.py",
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 3,
        },
    }, indent=2)

# ─── DISCORD BOT ───────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot Factory online as {bot.user}")
    print(f"   GitHub: {GITHUB_USERNAME}")
    print(f"   Model:  {GROQ_MODEL}")

@bot.command(name="make")
async def make_bot(ctx, *, description: str):
    """!make content bot for African history channel"""
    msg = await ctx.send(f"⚙️ **Generating:** `{description}`...")
    loop = asyncio.get_event_loop()
    try:
        await msg.edit(content="🧠 **[1/4]** Groq generating bot code...")
        bot_code, requirements, repo_name = await loop.run_in_executor(None, generate_bot_code, description)

        await msg.edit(content=f"📦 **[2/4]** Creating repo `{repo_name}`...")
        repo_data = await loop.run_in_executor(None, create_repo, repo_name, description)
        if "id" not in repo_data:
            await msg.edit(content=f"❌ GitHub error: `{repo_data.get('message', 'Unknown')}`")
            return

        await loop.run_in_executor(None, init_repo_with_readme, repo_name)
        await asyncio.sleep(1)

        await msg.edit(content="🚀 **[3/4]** Pushing to GitHub...")
        files = {
            "bot.py": bot_code,
            "requirements.txt": requirements,
            "railway.json": generate_railway_config(),
            "Procfile": "worker: python bot.py",
        }
        await loop.run_in_executor(None, push_multiple_files, repo_name, files, "🤖 Bot Factory deploy")

        await msg.edit(content=f"""✅ **Bot deployed!**

📁 **Repo:** {get_repo_url(repo_name)}
🚄 Connect `{repo_name}` in Railway → auto-deploys on every push

⚠️ **Railway → Variables → add:**
`DISCORD_BOT_TOKEN` = your bot token

🤖 **Type:** `{description[:60]}`""")

    except Exception as e:
        await msg.edit(content=f"❌ Factory error: `{str(e)}`")


@bot.command(name="update")
async def update_bot(ctx, repo_name: str, *, instruction: str):
    """!update empire-content-bot-1234 add a !stats command"""
    msg = await ctx.send(f"🔄 Updating `{repo_name}`...")
    loop = asyncio.get_event_loop()
    try:
        bot_code, requirements, _ = await loop.run_in_executor(None, generate_bot_code, instruction)
        files = {"bot.py": bot_code, "requirements.txt": requirements}
        await loop.run_in_executor(None, push_multiple_files, repo_name, files, f"🔄 {instruction[:50]}")
        await msg.edit(content=f"✅ `{repo_name}` updated — Railway redeploying.\n🔧 `{instruction}`")
    except Exception as e:
        await msg.edit(content=f"❌ Update error: `{str(e)}`")


@bot.command(name="status")
async def factory_status(ctx):
    r = requests.get(
        f"https://api.github.com/users/{GITHUB_USERNAME}/repos?sort=created&per_page=10",
        headers=GITHUB_HEADERS
    )
    repos = [repo for repo in r.json() if repo.get("name", "").startswith("empire-")]
    if not repos:
        await ctx.send("No empire bots yet. Use `!make <description>`")
        return
    lines = [f"🤖 **{r['name']}** — {r['description'] or 'no description'}" for r in repos]
    await ctx.send("**🏭 Bot Factory:**\n" + "\n".join(lines))


@bot.command(name="swarm")
async def deploy_swarm(ctx, count: int = 3, *, base_description: str = "African history content bot"):
    """!swarm 3 YouTube SEO optimizer bot"""
    if count > 5:
        await ctx.send("⚠️ Max 5 per swarm.")
        return
    await ctx.send(f"🐝 **Deploying swarm of {count}...**")
    specs = ["script writer", "SEO optimizer", "upload scheduler", "comment responder", "analytics tracker"]
    for i in range(count):
        await ctx.invoke(make_bot, description=f"{base_description} — {specs[i % len(specs)]}")
        await asyncio.sleep(3)


# ─── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🏭 DIGITAL EMPIRE BOT FACTORY")
    print(f"GitHub: {GITHUB_USERNAME or '⚠️ NOT SET'}")
    print(f"Model:  {GROQ_MODEL}")

    missing = []
    if not DISCORD_BOT_TOKEN: missing.append("DISCORD_TOKEN")
    if not GITHUB_TOKEN:      missing.append("GITHUB_TOKEN")
    if not GITHUB_USERNAME:   missing.append("GITHUB_USERNAME")
    if not GROQ_API_KEY:      missing.append("GROQ_API_KEY")

    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
    else:
        bot.run(DISCORD_BOT_TOKEN)
