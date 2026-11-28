"""Render both selection policies and the continuous joint trajectory."""

from math import cos, pi, sin

from PIL import Image, ImageDraw

from kinematics import LINKS, forward

COLORS = {"independent":"#a44d40", "continuous":"#1a8063"}


def joint_series(draw, poses, index, joint, box, color):
    left,top,right,bottom=box
    def point(frame,value):
        wrapped=(value+pi)%(2*pi)-pi
        return left+(right-left)*frame/(len(poses)-1), bottom-(wrapped+pi)*(bottom-top)/(2*pi)
    for frame in range(1,index+1):
        a,b=poses[frame-1],poses[frame]
        if a is None or b is None:
            continue
        p,q=point(frame-1,a[joint]),point(frame,b[joint])
        if abs(p[1]-q[1]) <= (bottom-top)/2:
            draw.line((p,q),fill=color,width=2)


def panel(targets, independent, continuous, index):
    image=Image.new("RGB",(900,530),"#f7fafc")
    draw=ImageDraw.Draw(image)
    draw.text((24,20),"Planar inverse kinematics · comparison of branch selection",fill="#182537")
    draw.text((24,45),f"Frame {index + 1} / {len(targets)}",fill="#35425a")
    center=(206,292)
    def map_point(x,y):
        return center[0]+x*98,center[1]-y*98
    radius=sum(LINKS)*98
    draw.ellipse((center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius),
                 outline="#bac6d6")
    draw.line([map_point(*point) for point in targets],fill="#9baabc",width=1)
    x,y=map_point(*targets[index])
    draw.ellipse((x-4,y-4,x+4,y+4),fill="#263149")
    if continuous[index] is None:
        draw.text((24,501),"Target outside reachable workspace",fill="#a44d40")
    for label,poses in (("independent",independent),("continuous",continuous)):
        color=COLORS[label]
        pose=poses[index]
        if pose is not None:
            elbow=(LINKS[0]*cos(pose[0]),LINKS[0]*sin(pose[0]))
            draw.line((center,map_point(*elbow),map_point(*forward(pose))),fill=color,width=4)
        for joint,box in enumerate(((445,116,865,254),(445,324,865,462))):
            joint_series(draw,poses,index,joint,box,color)
    for box,label in (((445,116,865,254),"Shoulder angle"),((445,324,865,462),"Elbow angle")):
        draw.rectangle(box,outline="#8492a6")
        draw.text((box[0],box[1]-22),label+" · −π to π",fill="#182537")
        draw.text((box[0],box[3]+8),"Frame 1",fill="#35425a")
        draw.text((box[2]-62,box[3]+8),f"Frame {len(targets)}",fill="#35425a")
    draw.text((446,501),"Independent",fill=COLORS["independent"])
    draw.text((568,501),"Continuous",fill=COLORS["continuous"])
    return image


def render(targets, independent, continuous, output):
    frame_count=len(targets)
    stops=set(range(0,frame_count,12)) | {frame_count-1,64,128,192}
    images=[panel(targets,independent,continuous,index) for index in sorted(stops)]
    images[-1].save(output/"trajectory-angles.png")
    images[0].save(output/"arm-poses.gif",save_all=True,append_images=images[1:],
                   duration=140,loop=0,optimize=False)
