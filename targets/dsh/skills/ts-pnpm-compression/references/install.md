# Optional compression setup

Inspect the installed RTK version and help before configuring project filters. Merge only named sections from rtk-filters.toml and preserve existing user filters. No global
installation or shell hook modification is implied by using this skill.

Run RTK’s embedded filter verification and compare successful plus failing pnpm/Turbo output with raw logs. Compression must preserve warnings, errors, filenames, stacks and exit
codes. The filters deliberately avoid success short-circuits and tail truncation: an early success does not make a later failure disappear.

If the installed RTK cannot match these commands, use the real command and summarize saved output. Report optional compression as unavailable; never make it a dependency of
application verification or claim a shell rewrite occurred without observing it.
