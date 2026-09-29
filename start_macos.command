#!/usr/bin/env bash
cd -- "$(dirname -- "$0")"
bash start.sh
result=$?
if [ "$result" -ne 0 ]; then
  printf '\nНе вдалося запустити ReelSave. Перевір Python 3.11+ та інструкцію README.md.\n'
  read -r -p 'Натисни Enter, щоб закрити вікно…'
fi
exit "$result"
