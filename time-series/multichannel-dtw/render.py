"""Draw paired DTW paths over channel-specific cost matrices."""

import numpy as np
from PIL import Image, ImageDraw

from alignment import SHIFTS, channel_losses, signals, solve


def example(length, shift):
    a, b, anchors, shifted=signals(0,shift,length)
    matrices=channel_losses(a,b)
    image=Image.new("RGB",(756,742),"#172031")
    draw=ImageDraw.Draw(image)
    common_cost,common,_=solve(a,b,"common")
    independent_cost,independent,_=solve(a,b,"independent")
    titles=("Common alignment","Independent alignment")
    draw.text((24,16),f"Opposite event shifts: ±{shift} samples",fill="white")
    for column,(title,paths,cost) in enumerate(zip(titles,(common,independent),(common_cost,independent_cost),strict=True)):
        x=28+column*368
        draw.text((x,42),f"{title} · total cost {cost:.3g}",fill="#e0eafa")
        for channel,(matrix,path) in enumerate(zip(matrices,paths,strict=True)):
            y=83+channel*328
            scale=308/length
            scaled=np.uint8(np.clip(matrix,0,1)*255)
            heatmap=np.stack((scaled,scaled//2,np.uint8(40)+scaled//4),axis=-1)
            image.paste(Image.fromarray(heatmap).resize((308,308),Image.Resampling.NEAREST),(x,y))
            point=lambda i,j:(x+(j+.5)*scale,y+(i+.5)*scale)
            draw.line([point(i,j) for i,j in path],fill="#49f5cd",width=2)
            px,py=point(anchors[channel],shifted[channel])
            draw.ellipse((px-4,py-4,px+4,py+4),outline="#ffe9a1",width=2)
            draw.text((x,y-16),f"Channel {channel+1}: source row, target column",fill="#d9e2f4")
    return image


def render(length, output):
    images=[example(length,shift) for shift in SHIFTS]
    images[SHIFTS.index(12)].save(output/"alignment-paths.png")
    images[0].save(output/"lag-sweep.gif",save_all=True,append_images=images[1:],
                   duration=350,loop=0,optimize=False)
