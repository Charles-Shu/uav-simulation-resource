"""Metre-scale city platform, open river basin and distant mountain ridges."""
import numpy as np
ROCK,GRASS,MUD,SAND,WATER,PAVING,ASPHALT=range(7)
NAMES=['rock','grass','mud','sand','riverbed','paving','asphalt']
ROAD_X=(-440.,-290.,-140.,10.)
ROAD_Y=(-440.,-400.,-240.,-80.,80.,240.)
BRIDGE_Y=(-240.,80.)
PARKS=((-215.,0.,49.,58.),(-65.,160.,49.,58.))
DRIVEWAY_Y=(-390.,-315.,-150.,-75.,0.,160.,225.)
CITY_LEVEL=8.
WATER_LEVEL=5.
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def noise(x,y):
 return .45*np.sin(x/67+1.2*np.sin(y/98))+.32*np.cos(y/45+x/123)+.18*np.sin(x/22+y/29)+.05*np.cos(x/8-y/11)
def river_center(y):return 160+25*np.sin(np.asarray(y)/160)+12*np.sin(np.asarray(y)/65)
def river_halfwidth(y):return 23+5*np.sin((np.asarray(y)+120)/110)
def river_r(x,y):return np.abs(np.asarray(x)-river_center(y))/river_halfwidth(y)
def terrain_height(x,y):
 x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float))
 north=smooth((y-(285+15*np.sin(x/100)))/200)*(130+35*np.sin(x/155+.6)+20*noise(x,y))
 # The river enters through a broad natural valley, not a narrow vertical cut.
 north*=smooth((np.abs(x-river_center(y))-75)/160)
 east=smooth((x-(350+15*np.sin(y/180)))/185)*(110+28*np.sin(y/133)+18*noise(x,y))
 h=8+np.maximum(north,east)+np.minimum(north,east)*.18
 # Banks and mineral river bed. Both connect continuously at the waterline.
 r=river_r(x,y)
 bank=5+(h-5)*smooth((r-1)/.85)
 bowl=5-6*np.maximum(0,1-r*r)**1.35
 h=np.where(r<1,bowl,np.where(r<1.85,bank,h))
 return h
def in_park(x,y):
 x,y=np.broadcast_arrays(x,y);out=np.zeros(x.shape,bool)
 for cx,cy,rx,ry in PARKS:out|=(np.abs(x-cx)<rx)&(np.abs(y-cy)<ry)
 return out
def road_mask(x,y,width_extra=0):
 x,y=np.broadcast_arrays(x,y);out=np.zeros(x.shape,bool)
 for cx in ROAD_X:out|=(np.abs(x-cx)<10+width_extra)&(y>-440)&(y<270)
 for cy in ROAD_Y:out|=(np.abs(y-cy)<10+width_extra)&(x>-480)&(x<55)
 # Two bridges connect the city to a park/residential road on the east bank.
 for cy in BRIDGE_Y:out|=(np.abs(y-cy)<10+width_extra)&(x>=55)&(x<325)
 out|=(np.abs(x-320)<7+width_extra)&(y>-440)&(y<260)
 for cy in DRIVEWAY_Y:out|=(np.abs(y-cy)<3+width_extra)&(x>258)&(x<320)
 return out
def height_and_zones(x,y):
 x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float));h=terrain_height(x,y)
 zone=np.full(h.shape,GRASS,np.uint8)
 city=(x>-480)&(x<55)&(y>-485)&(y<270)
 zone[city&~in_park(x,y)]=PAVING
 zone[(h>65+12*noise(x,y))]=ROCK
 r=river_r(x,y)
 zone[(r>1)&(r<1.28)]=SAND
 zone[(r>1.02)&(r<1.22)&(noise(x,y)<-.2)]=MUD
 zone[r<=1]=WATER
 # River and its bed stay intact below bridge decks.
 zone[road_mask(x,y)&(r>1.85)]=ASPHALT
 return h,zone
def slope_degrees(x,y):
 dx=(terrain_height(np.asarray(x)+1,y)-terrain_height(np.asarray(x)-1,y))/2
 dy=(terrain_height(x,np.asarray(y)+1)-terrain_height(x,np.asarray(y)-1))/2
 return np.degrees(np.arctan(np.hypot(dx,dy)))
def river_polygon(n=161):
 y=np.linspace(-500,500,n);c=river_center(y);r=river_halfwidth(y)
 return np.vstack([np.column_stack([c-r,y]),np.column_stack([c[::-1]+r[::-1],y[::-1]])])
