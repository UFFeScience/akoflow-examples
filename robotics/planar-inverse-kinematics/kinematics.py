"""Analytic planar inverse kinematics and continuity-aware branch selection."""

from math import atan2, cos, hypot, isfinite, pi, sin, sqrt, tau

LINKS = (1.0, 0.7)
FRAMES = 256
TOLERANCE = 1e-12


def forward(angles, lengths=LINKS):
    shoulder, elbow = angles
    first, second = lengths
    return (first*cos(shoulder) + second*cos(shoulder+elbow),
            first*sin(shoulder) + second*sin(shoulder+elbow))


def inverse(x, y, lengths=LINKS):
    first, second = lengths
    if not all(isfinite(value) for value in (x,y,first,second)) or min(lengths)<=0:
        raise ValueError("Expected finite coordinates and positive link lengths")
    radius = hypot(x,y)
    if radius < abs(first-second)-TOLERANCE or radius > first+second+TOLERANCE:
        return ()
    # At an origin with equal links, choose a representative shoulder angle.
    if radius <= TOLERANCE and abs(first-second) <= TOLERANCE:
        return ((0.0,pi),)
    if abs(radius-(first+second)) <= TOLERANCE:
        return ((atan2(y,x),0.0),)
    if abs(radius-abs(first-second)) <= TOLERANCE:
        return ((atan2(y,x)-(pi if second>first else 0.0),pi),)
    cosine = max(-1.0,min(1.0,(radius**2-first**2-second**2)/(2*first*second)))
    sine = sqrt(max(0.0,1-cosine**2))
    return tuple((atan2(y,x)-atan2(second*value,first+second*cosine),atan2(value,cosine))
                 for value in (sine,-sine))


def targets(trajectory=0):
    for index in range(FRAMES):
        phase = tau*index/FRAMES
        angle = phase + 0.18*sin(3*phase+trajectory/4)
        radius = {0:0.3,64:1.7,128:0.25,192:1.75}.get(index)
        if radius is None:
            radius = 1.0 + 0.6*sin(2*phase+trajectory/8)
        yield radius*cos(angle),radius*sin(angle)


def step_cost(previous, current):
    return sum(((b-a+pi)%tau-pi)**2 for a,b in zip(previous,current,strict=True))


def optimal_segment(segment):
    costs = [0.0]*len(segment[0])
    previous_rows = []
    for previous,current in zip(segment,segment[1:]):
        best=[min((cost+step_cost(old,now),index)
                  for index,(cost,old) in enumerate(zip(costs,previous,strict=True)))
              for now in current]
        costs=[cost for cost,_ in best]
        previous_rows.append([index for _,index in best])
    index=min(range(len(costs)),key=costs.__getitem__)
    selected=[index]
    for previous in reversed(previous_rows):
        index=previous[index]
        selected.append(index)
    return [choices[index] for choices,index in zip(segment,reversed(selected),strict=True)]


def select_path(frames):
    """Optimize each contiguous reachable segment; gaps have no pose."""
    selected=[]
    segment=[]
    for candidates in (*frames,()):
        if candidates:
            segment.append(candidates)
            continue
        if segment:
            selected.extend(optimal_segment(segment))
            segment=[]
        selected.append(None)
    return selected[:-1]
