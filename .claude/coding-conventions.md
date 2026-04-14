# Coding Conventions

## Python (Backend)

- **Formatter:** black (line-length 100)
- **Linter:** ruff (pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade)
- **Type hints** on every function signature
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Async:** all database operations use `async/await`
- **Error handling:** custom exception classes → global handlers → consistent JSON responses

## TypeScript (Frontend)

- **Strict mode** enabled in tsconfig.json
- **Formatter:** Prettier (semi, double quotes, trailing commas)
- **Linter:** ESLint (react, react-hooks, typescript rules)
- **Components:** server components by default; add `'use client'` only when needed
- **Naming:** camelCase for functions/variables, PascalCase for components/types

## Git

- **Commits:** conventional commits format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- **Pre-commit hooks:** ruff + black (Python), ESLint + Prettier (TS), detect-private-key
- **Branch naming:** `feature/`, `fix/`, `refactor/` prefixes
- **Author:** Commit as **Armando Gonzalez** (armandogon94@gmail.com)
- **Do NOT add** "Co-Authored-By: Claude" or any AI co-author credits
- Keep commits atomic (one logical change per commit)
- Use the 7 specialist roles from AGENTS.md when applicable — include role context in detailed commit descriptions or `.claude/memory.md`
