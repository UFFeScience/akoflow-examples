# Planar inverse kinematics and branch continuity

This geometric experiment is inspired by the [ERI-GO study by Zacca and colleagues at PUC Goiás and UFG](https://sol.sbc.org.br/index.php/erigo/article/download/13859/13706/).
It uses synthetic targets and a two-link planar arm. The shoulder angle
is measured counterclockwise from the x-axis, and the elbow angle is
relative to the first link. Angles are radians and links are 1.0 and 0.7
simulation units.

The 256-frame reference includes two reach-boundary controls with one
pose and two unreachable controls. Dynamic programming minimizes the
sum of squared circular changes across contiguous reachable frames.
