"""Render validated endpoint counts on shared axes and intensity scales."""

from collections import Counter
from math import log1p

import numpy as np
from PIL import Image, ImageDraw

from walks import BATCHES, SCENARIOS


def panel(histograms, extent, limit, batches, steps):
    width,height=338,216
    image=Image.new("RGB",(736,548),"#172131")
    draw=ImageDraw.Draw(image)
    draw.text((22,17),f"Endpoint dispersion · {steps} steps · {batches} batches per panel",
              fill="#f0f5fd")
    xmin,xmax,ymin,ymax=extent
    denominator=log1p(limit)
    for index,scenario in enumerate(SCENARIOS):
        counts=np.zeros((ymax-ymin+1,xmax-xmin+1))
        for (x,y),count in histograms[scenario].items():
            counts[ymax-y,x-xmin]=count
        scaled=np.log1p(counts)/denominator
        red=np.uint8(13+230*scaled)
        green=np.uint8(25+167*scaled)
        blue=np.uint8(46+51*scaled)
        tile=Image.fromarray(np.stack((red,green,blue),axis=-1))
        x,y=21+(index%2)*354,69+(index//2)*232
        image.paste(tile.resize((width,height-20),Image.Resampling.NEAREST),(x,y))
        draw.text((x,y-19),scenario.replace("-"," ").title(),fill="#f0f5fd")
        draw.text((x,y+height-18),f"x: {xmin} to {xmax}   y: {ymin} to {ymax}",fill="#b5c3d4")
    draw.text((21,528),f"Shared color scale: 0 to {limit} particles per grid cell (log scale)",
              fill="#b5c3d4")
    return image


def render(by_scenario, output, steps):
    totals={scenario:sum(histograms,Counter()) for scenario,histograms in by_scenario.items()}
    xs,ys=zip(*(point for histogram in totals.values() for point in histogram))
    extent=(min(xs),max(xs),min(ys),max(ys))
    limit=max(count for histogram in totals.values() for count in histogram.values())
    panel(totals,extent,limit,BATCHES,steps).save(output/"endpoint-dispersion.png")
    frames=[]
    for count in range(4,BATCHES+1,4):
        cumulative={scenario:sum(histograms[:count],Counter())
                    for scenario,histograms in by_scenario.items()}
        frames.append(panel(cumulative,extent,limit,count,steps))
    frames[0].save(output/"endpoint-accumulation.gif",save_all=True,append_images=frames[1:],
                   duration=180,loop=0,optimize=False)
