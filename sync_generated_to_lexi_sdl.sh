#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest_dir="${script_dir}/../lexi-sdl/word_data"

python3 "${script_dir}/concat_language_txts.py"

mkdir -p "${dest_dir}"
cp "${script_dir}/ar.txt" "${dest_dir}/ar.txt"
cp "${script_dir}/en.txt" "${dest_dir}/en.txt"
cp "${script_dir}/ru.txt" "${dest_dir}/ru.txt"
cp "${script_dir}/tr.txt" "${dest_dir}/tr.txt"

printf 'Copied generated dictionaries to %s\n' "${dest_dir}"
