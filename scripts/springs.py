"""
springs.py
the spring curves in css/site.css (--spring-bouncy, --spring-quick, --spring-view), as css linear()
easing. each is an apple-style spring given a duration and a bounce: stiffness (2 pi / duration)^2,
damping ratio 1 - bounce, mass 1, from 0 to 1 at rest. the animate skill keeps bounce at 0.1 to 0.3.

run: python scripts/springs.py   (prints the custom properties to paste into site.css)
"""
import math

SPRINGS = {
    "bouncy": (0.5, 0.3),   # playful, rare moments: the map's first load, markers, dots, labels
    "quick": (0.35, 0.3),   # controls: a press releasing, the toggle's thumb, a stop's hover lift
    "view": (0.45, 0.2),    # whole screens arriving, calmer because they're big
    # past the skill's 0.3 on purpose: the title screen david gave as a reference pops its letters and
    # icons with about 12% overshoot. used only on the map's first load, which plays once
    "pop": (0.5, 0.45),
}


def position(t, duration, bounce):
    w = 2 * math.pi / duration
    z = 1 - bounce
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))


for name, (duration, bounce) in SPRINGS.items():
    step = 0.0005
    t, last_out = 0.0, 0.0
    while t < 5:
        if abs(position(t, duration, bounce) - 1) > 0.001:
            last_out = t
        t += step
    settle = math.ceil(last_out * 100) / 100  # within 0.1% of the end from here on, rounded up to 10ms
    points = [round(position(settle * i / 40, duration, bounce), 4) for i in range(41)]
    points[-1] = 1
    peak = max(position(i * step, duration, bounce) for i in range(int(settle / step)))
    print(f"    --spring-{name}: linear({', '.join(('1' if p == 1 else f'{p:g}') for p in points)});")
    print(f"    --spring-{name}-time: {round(settle * 1000)}ms; /* duration {duration}, bounce {bounce}, overshoot {100 * (peak - 1):.1f}% */")
