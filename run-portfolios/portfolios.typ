
= All
== Handmade
gecode,7
cp-sat,1

dexter,7
cp-sat,1

gurobi,7
cp-sat,1

gecode,1
chuffed,1


== k=1, 8 cores, 8 solvers
 1  oracle_score=3746.29  robustness=3746.29
    Portfolio 1 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(2c), org.picat-lang.picat(1c), yuck(1c)


== k=2, 8 cores, 8 solvers


 1  oracle_score=3848.05  robustness=3746.29
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(2c), org.picat-lang.picat(1c), yuck(1c)

 2  oracle_score=3847.31  robustness=3700.52
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(2c), org.minizinc.mip.coin-bc(1c), org.minizinc.mip.gurobi(1c), org.picat-lang.picat(1c), yuck(1c)

== k=2, 7 cores, 7 solvers

 1  oracle_score=3842.56  robustness=3737.46
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (7c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(1c), org.picat-lang.picat(1c), yuck(1c)

 2  oracle_score=3840.01  robustness=3737.19
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (7c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(1c), org.minizinc.mip.gurobi(2c), org.picat-lang.picat(1c), yuck(1c)

== k=2, 6 cores, 6 solvers
 1  oracle_score=3834.52  robustness=3728.37
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (6c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(1c), org.minizinc.mip.gurobi(1c), org.picat-lang.picat(1c), yuck(1c)

== k=2, 4 cores, 4 solvers
 1  oracle_score=3795.84  robustness=3667.48
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (4c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(1c), org.minizinc.mip.gurobi(1c)

== k=2, 2 cores, 2 solvers
 1  oracle_score=3712.60  robustness=3554.89
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (2c): cp-sat(1c), org.chuffed.chuffed(1c)

 2  oracle_score=3703.52  robustness=3471.69
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (2c): cp-sat(1c), org.gecode.gecode(1c)
    
== k=3, 8 cores, 8 solvers
 1  oracle_score=3885.27  robustness=3551.24
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), izplus(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(4c)
    Portfolio 3 (8c): cp-sat(1c), org.choco.choco(2c), org.chuffed.chuffed(1c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c), yuck(1c)

 2  oracle_score=3885.26  robustness=3540.46
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(1c), org.minizinc.mip.gurobi(4c), yuck(1c)
    Portfolio 3 (8c): cp-sat(1c), org.choco.choco(2c), org.gecode.gecode(2c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c)

 4  oracle_score=3885.24  robustness=3540.46
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.minizinc.mip.gurobi(4c), yuck(2c)
    Portfolio 3 (8c): cp-sat(1c), org.choco.choco(2c), org.gecode.gecode(2c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c)

 5  oracle_score=3885.24  robustness=3508.22
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(4c)
    Portfolio 3 (8c): cp-sat(1c), org.choco.choco(2c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c), yuck(2c)



== k=3, 7 cores, 7 solvers
 1  oracle_score=3880.86  robustness=3610.85
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (7c): cp-sat(1c), org.chuffed.chuffed(1c), org.minizinc.mip.gurobi(4c), yuck(1c)
    Portfolio 3 (7c): cp-sat(1c), org.choco.choco(1c), org.gecode.gecode(2c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c)


 4  oracle_score=3880.65  robustness=3595.93
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (7c): cp-sat(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(4c)
    Portfolio 3 (7c): cp-sat(1c), org.choco.choco(1c), org.chuffed.chuffed(1c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c), yuck(1c)


== k=3, 6 cores, 6 solvers
 1  oracle_score=3871.87  robustness=3581.18
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (6c): cp-sat(1c), org.chuffed.chuffed(1c), org.minizinc.mip.gurobi(4c)
    Portfolio 3 (6c): cp-sat(1c), org.gecode.gecode(2c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), yuck(1c)

== k=3, 4 cores, 4 solvers
 1  oracle_score=3843.47  robustness=3538.77
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (4c): cp-sat(1c), org.chuffed.chuffed(1c), org.minizinc.mip.gurobi(1c), yuck(1c)
    Portfolio 3 (4c): cp-sat(1c), org.gecode.gecode(1c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c)



== k=3, 2 cores, 2 solvers
 1  oracle_score=3766.16  robustness=2314.58
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (2c): cp-sat(1c), org.chuffed.chuffed(1c)
    Portfolio 3 (8c): org.minizinc.mip.gurobi(8c)




== k=3, 8 cores, 7 solvers
 1  oracle_score=3885.27  robustness=3551.24
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), izplus(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(4c)
    Portfolio 3 (8c): cp-sat(1c), org.choco.choco(2c), org.chuffed.chuffed(1c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c), yuck(1c)


== k=3, 8 cores, 6 solvers
 1  oracle_score=3885.26  robustness=3540.46
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(1c), org.minizinc.mip.gurobi(4c), yuck(1c)
    Portfolio 3 (8c): cp-sat(1c), org.choco.choco(2c), org.gecode.gecode(2c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c)

== k=3, 8 cores, 4 solvers

 1  oracle_score=3874.10  robustness=3540.71
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(4c), org.picat-lang.picat(1c)
    Portfolio 3 (8c): cp-sat(1c), org.choco.choco(2c), org.chuffed.chuffed(1c), yuck(4c)


== k=3, 8 cores, 2 solvers
 1  oracle_score=3697.90  robustness=1653.40
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): org.gecode.gecode(8c)
    Portfolio 3 (8c): org.minizinc.mip.gurobi(8c)



== k=3, 7 cores, 6 solvers
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (7c): cp-sat(1c), org.chuffed.chuffed(1c), org.minizinc.mip.gurobi(4c), yuck(1c)
    Portfolio 3 (7c): cp-sat(1c), org.choco.choco(1c), org.gecode.gecode(2c), org.minizinc.mip.coin-bc(1c), org.picat-lang.picat(1c), solutions.huub(1c)

== k=3, 7 cores, 4 solvers
 1  oracle_score=3871.86  robustness=3491.42
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (7c): cp-sat(1c), org.chuffed.chuffed(1c), org.minizinc.mip.gurobi(4c), org.picat-lang.picat(1c)
    Portfolio 3 (7c): cp-sat(1c), org.choco.choco(2c), org.gecode.gecode(2c), yuck(2c)


== k=2, 8 cores, 4 solvers
1  oracle_score=3829.58  robustness=3712.23
    Portfolio 1 (fixed): cp-sat(8c)
    Portfolio 2 (8c): cp-sat(1c), org.chuffed.chuffed(1c), org.gecode.gecode(2c), org.minizinc.mip.gurobi(4c)