#!/usr/bin/env bash
# Clone the third-party projects Zeitgauge learns from, pinned to the commits
# reviewed on 26 November 2026. They land in third_party/, which git ignores.
# See docs/third-party.md for each licence and how we use it.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p third_party
while read -r repo sha; do
  [ -z "$repo" ] && continue
  dest="third_party/${repo//\//_}"
  if [ ! -d "$dest/.git" ]; then
    git clone --quiet "https://github.com/$repo.git" "$dest"
  fi
  git -C "$dest" fetch --quiet origin "$sha" 2>/dev/null || true
  git -C "$dest" checkout --quiet "$sha"
  echo "ok  $repo @ ${sha:0:7}"
done <<'LIST'
flack0x/trendspyg 9f07b2573e7287df85df9202da206569024723e9
AndrewFSee/macro-regime-nowcaster 2e131938b2701d99c95b48ce58ef3e0b7031a018
alochemes/nowcast-quad 80ba137732e0280166b9fb8e3da33564bc9a36c9
amazon-science/nowcasting-recession-risk 9f9818e184da459c5aa32a57fa83b09fee055292
Seshat-Global-History-Databank/seshat_api d93034736f6a832b33a069f54d8e404773e1a11e
Seshat-Global-History-Databank/build_polaris_dataset 55ca5fbc2b563ddbbc1a3413071d4bd243d0a5fa
Joe-Wait/onspy 23e2b097b1bea1c98a4a89e2dacc4ae7d2d263c6
Asterbons/Cliodynamics 50cd4ff920eebcedd150eba0a55d02b929d5fad6
RichardScottOZ/Cliodynamics 39b325454fc34f4c86212a1107208f004d6f718a
LIST
