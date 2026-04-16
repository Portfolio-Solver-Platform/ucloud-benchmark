# Portfolio Inventory

All unique sub-portfolios extracted from `portfolios.typ`.

**Excluded:**
- Single-solver 8-core portfolios (already benchmarked): cp-sat(8), org.gecode.gecode(8), org.minizinc.mip.gurobi(8)
- "Portfolio 1 (fixed): cp-sat(8c)" entries from all k=2/k=3 sections

## Handmade

| # | Name | Solvers | Cores |
|---|------|---------|-------|
| 1 | handmade-gecode7-cpsat1 | org.gecode.gecode(7), cp-sat(1) | 8 |
| 2 | handmade-dexter7-cpsat1 | dexter(7), cp-sat(1) | 8 |
| 3 | handmade-gurobi7-cpsat1 | org.minizinc.mip.gurobi(7), cp-sat(1) | 8 |
| 4 | handmade-gecode1-chuffed1 | org.gecode.gecode(1), org.chuffed.chuffed(1) | 2 |

## k=1 and k=2

| # | Name | Solvers | Cores |
|---|------|---------|-------|
| 5 | k1-8c-8s-v1 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(2), org.minizinc.mip.gurobi(2), org.picat-lang.picat(1), yuck(1) | 8 |
| 6 | k2-8c-8s-v2-p2 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(2), org.minizinc.mip.coin-bc(1), org.minizinc.mip.gurobi(1), org.picat-lang.picat(1), yuck(1) | 8 |
| 7 | k2-7c-7s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(2), org.minizinc.mip.gurobi(1), org.picat-lang.picat(1), yuck(1) | 7 |
| 8 | k2-7c-7s-v2-p2 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(1), org.minizinc.mip.gurobi(2), org.picat-lang.picat(1), yuck(1) | 7 |
| 9 | k2-6c-6s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(1), org.minizinc.mip.gurobi(1), org.picat-lang.picat(1), yuck(1) | 6 |
| 10 | k2-4c-4s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(1), org.minizinc.mip.gurobi(1) | 4 |
| 11 | k2-2c-2s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1) | 2 |
| 12 | k2-2c-2s-v2-p2 | cp-sat(1), org.gecode.gecode(1) | 2 |

## k=3, 8 cores

| # | Name | Solvers | Cores |
|---|------|---------|-------|
| 13 | k3-8c-8s-v1-p2 | cp-sat(1), izplus(1), org.gecode.gecode(2), org.minizinc.mip.gurobi(4) | 8 |
| 14 | k3-8c-8s-v1-p3 | cp-sat(1), org.choco.choco(2), org.chuffed.chuffed(1), org.minizinc.mip.coin-bc(1), org.picat-lang.picat(1), solutions.huub(1), yuck(1) | 8 |
| 15 | k3-8c-8s-v2-p2 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(1), org.minizinc.mip.gurobi(4), yuck(1) | 8 |
| 16 | k3-8c-8s-v2-p3 | cp-sat(1), org.choco.choco(2), org.gecode.gecode(2), org.minizinc.mip.coin-bc(1), org.picat-lang.picat(1), solutions.huub(1) | 8 |
| 17 | k3-8c-8s-v4-p2 | cp-sat(1), org.chuffed.chuffed(1), org.minizinc.mip.gurobi(4), yuck(2) | 8 |
| 18 | k3-8c-8s-v5-p2 | cp-sat(1), org.chuffed.chuffed(1), org.gecode.gecode(2), org.minizinc.mip.gurobi(4) | 8 |
| 19 | k3-8c-8s-v5-p3 | cp-sat(1), org.choco.choco(2), org.minizinc.mip.coin-bc(1), org.picat-lang.picat(1), solutions.huub(1), yuck(2) | 8 |
| 20 | k3-8c-4s-v1-p2 | cp-sat(1), org.gecode.gecode(2), org.minizinc.mip.gurobi(4), org.picat-lang.picat(1) | 8 |
| 21 | k3-8c-4s-v1-p3 | cp-sat(1), org.choco.choco(2), org.chuffed.chuffed(1), yuck(4) | 8 |

## k=3, 7 cores

| # | Name | Solvers | Cores |
|---|------|---------|-------|
| 22 | k3-7c-7s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1), org.minizinc.mip.gurobi(4), yuck(1) | 7 |
| 23 | k3-7c-7s-v1-p3 | cp-sat(1), org.choco.choco(1), org.gecode.gecode(2), org.minizinc.mip.coin-bc(1), org.picat-lang.picat(1), solutions.huub(1) | 7 |
| 24 | k3-7c-7s-v4-p2 | cp-sat(1), org.gecode.gecode(2), org.minizinc.mip.gurobi(4) | 7 |
| 25 | k3-7c-7s-v4-p3 | cp-sat(1), org.choco.choco(1), org.chuffed.chuffed(1), org.minizinc.mip.coin-bc(1), org.picat-lang.picat(1), solutions.huub(1), yuck(1) | 7 |
| 26 | k3-7c-4s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1), org.minizinc.mip.gurobi(4), org.picat-lang.picat(1) | 7 |
| 27 | k3-7c-4s-v1-p3 | cp-sat(1), org.choco.choco(2), org.gecode.gecode(2), yuck(2) | 7 |

## k=3, 6 cores

| # | Name | Solvers | Cores |
|---|------|---------|-------|
| 28 | k3-6c-6s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1), org.minizinc.mip.gurobi(4) | 6 |
| 29 | k3-6c-6s-v1-p3 | cp-sat(1), org.gecode.gecode(2), org.minizinc.mip.coin-bc(1), org.picat-lang.picat(1), yuck(1) | 6 |

## k=3, 4 cores

| # | Name | Solvers | Cores |
|---|------|---------|-------|
| 30 | k3-4c-4s-v1-p2 | cp-sat(1), org.chuffed.chuffed(1), org.minizinc.mip.gurobi(1), yuck(1) | 4 |
| 31 | k3-4c-4s-v1-p3 | cp-sat(1), org.gecode.gecode(1), org.minizinc.mip.coin-bc(1), org.picat-lang.picat(1) | 4 |

## Duplicates (same solver allocation appears in multiple sections)

These are NOT separate portfolios — they are the same schedule appearing under a different k/c/s heading.

| Duplicate entry | Same as |
|----------------|---------|
| k2-8c-8s-v1-p2 | #5 k1-8c-8s-v1 |
| k3-2c-2s-v1-p2 | #11 k2-2c-2s-v1-p2 |
| k3-8c-7s-v1-p2 | #13 k3-8c-8s-v1-p2 |
| k3-8c-7s-v1-p3 | #14 k3-8c-8s-v1-p3 |
| k3-8c-6s-v1-p2 | #15 k3-8c-8s-v2-p2 |
| k3-8c-6s-v1-p3 | #16 k3-8c-8s-v2-p3 |
| k3-8c-8s-v4-p3 | #16 k3-8c-8s-v2-p3 |
| k2-8c-4s-v1-p2 | #18 k3-8c-8s-v5-p2 |
| k3-7c-6s-v1-p2 | #22 k3-7c-7s-v1-p2 |
| k3-7c-6s-v1-p3 | #23 k3-7c-7s-v1-p3 |
