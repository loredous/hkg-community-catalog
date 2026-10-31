#!/usr/bin/env python3
"""Build and sign community/index.json from sources.json.

For each package in sources.json it finds the project's current download on GitHub, pinned
so the hash stays valid: the matching asset of the latest release (by its tag), or for a
project without releases, the committed file at the last commit that changed it. It
downloads the zip, checks that NEMESIS.data at the zip's root names the expected package id,
takes the version from it, and records the URL, size and SHA-256. Then it writes
community/index.json, community/key.pem and community/index.json.sig.

usage: python3 tools/build.py --key PATH [--skip-missing]
  --key PATH       the catalog's private signing key (PEM; never commit it)
  --skip-missing   leave out a package whose download can't be found, instead of failing
environment: GITHUB_TOKEN (optional) raises the GitHub API rate limit.
Needs openssl. Standard library only.
"""
import argparse
import datetime
import fnmatch
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "community")
API = "https://api.github.com"
META_LIMIT = 8192  # NEMESIS reads at most this much of NEMESIS.data


class Missing(Exception):
    pass


def get(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "hkg-community-catalog"})
    if accept:
        req.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(API):
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def api(path):
    return json.loads(get(API + path, "application/vnd.github+json"))


def release_asset(src):
    rel = api("/repos/%s/releases/latest" % src["repo"])
    hits = [a for a in rel["assets"]
            if fnmatch.fnmatchcase(a["name"], src["asset"])
            and not (src.get("not") and fnmatch.fnmatchcase(a["name"], src["not"]))]
    if len(hits) != 1:
        names = ", ".join(a["name"] for a in rel["assets"]) or "none"
        raise Missing("%s %s: %d assets match %r (assets: %s)"
                      % (src["repo"], rel["tag_name"], len(hits), src["asset"], names))
    return hits[0]["browser_download_url"], rel["tag_name"]


def committed_file(src):
    commits = api("/repos/%s/commits?path=%s&per_page=1" % (src["repo"], src["path"]))
    if not commits:
        raise Missing("%s: no commit has %s" % (src["repo"], src["path"]))
    sha = commits[0]["sha"]
    return "https://raw.githubusercontent.com/%s/%s/%s" % (src["repo"], sha, src["path"]), sha[:7]


def package_meta(data):
    """id, name and version from the zip's root NEMESIS.data [nemesis] section."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        try:
            text = z.read("NEMESIS.data")[:META_LIMIT].decode("utf-8", "replace")
        except KeyError:
            raise ValueError("no NEMESIS.data at the zip's root (a USB-stick zip, not a package zip?)")
    section, meta = "", {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "#;":
            continue
        if line.startswith("["):
            section = line[1:line.find("]")].strip() if "]" in line else section
        elif "=" in line and section == "nemesis":
            k, v = line.split("=", 1)
            meta.setdefault(k.strip(), v.strip())
    if meta.get("type") and not meta.get("id"):
        raise ValueError("NEMESIS.data is a USB-stick descriptor (type=%s), not a package" % meta["type"])
    return meta.get("id", ""), meta.get("name", ""), meta.get("version", "")


def entry(src):
    url, pin = release_asset(src) if "asset" in src else committed_file(src)
    data = get(url)
    pkg_id, name, version = package_meta(data)
    if pkg_id != src["id"]:
        raise ValueError("%s: zip says id %r, sources.json says %r" % (url, pkg_id, src["id"]))
    e = {
        "id": src["id"],
        "name": src.get("name") or name or src["id"],
        "version": version,
        "description": src["description"],
        "author": src["author"],
        "homepage": "https://github.com/" + src["repo"],
        "zip": url,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if src.get("compatibility"):
        e["compatibility"] = src["compatibility"]
    print("%-28s %-16s %-12s %8d  %s" % (src["id"], version, pin, len(data), url))
    return e


def openssl(*args):
    return subprocess.run(("openssl",) + args, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout


def write(path, data):
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def main(argv):
    ap = argparse.ArgumentParser(description="Build and sign the community catalog.")
    ap.add_argument("--key", required=True, help="private signing key (PEM)")
    ap.add_argument("--skip-missing", action="store_true",
                    help="leave out packages whose download can't be found")
    args = ap.parse_args(argv)

    with open(os.path.join(ROOT, "sources.json"), encoding="utf-8") as f:
        sources = json.load(f)

    entries = []
    for src in sources["packages"]:
        try:
            entries.append(entry(src))
        except Missing as e:
            if not args.skip_missing:
                print("error: %s" % e, file=sys.stderr)
                return 1
            print("skipped: %s" % e, file=sys.stderr)

    pub = openssl("pkey", "-in", args.key, "-pubout")
    der = openssl("pkey", "-in", args.key, "-pubout", "-outform", "DER")
    cat = sources["catalog"]
    index = {
        "format": 1,
        "id": cat["id"],
        "name": cat["name"],
        "publisher": cat["publisher"],
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "key": hashlib.sha256(der).hexdigest(),
        "packages": entries,
    }
    body = (json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    os.makedirs(OUT, exist_ok=True)
    write(os.path.join(OUT, "index.json"), body)
    write(os.path.join(OUT, "key.pem"), pub)
    sig = openssl("dgst", "-sha256", "-sign", args.key, os.path.join(OUT, "index.json"))
    write(os.path.join(OUT, "index.json.sig"), sig)
    print("wrote community/: %d packages, key %s" % (len(entries), index["key"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
