from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Dict, List, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment
from .config import TRACKING

@dataclass
class Track:
    track_id: int
    label: str
    confidence: float
    box: Tuple[float, float, float, float]
    last_time: float
    missed: int = 0
    age: int = 1
    hits: int = 1
    history: List[dict] = field(default_factory=list)

    @property
    def center(self):
        x1, y1, x2, y2 = self.box
        return ((x1+x2)/2.0, (y1+y2)/2.0)
    @property
    def width(self): return max(1.0, self.box[2]-self.box[0])
    @property
    def height(self): return max(1.0, self.box[3]-self.box[1])
    @property
    def area(self): return self.width*self.height
    @property
    def bottom(self): return self.box[3]

class GreedyTracker:
    """Class-aware constant-velocity tracker with global assignment.

    Detection frames are associated globally; non-detection frames are predicted so
    temporal reasoning keeps receiving current positions instead of stale boxes.
    """
    def __init__(self, max_distance=180.0, max_missed=None):
        self.max_distance = float(max_distance)
        self.max_missed = max_missed if max_missed is not None else TRACKING["max_missed_frames"]
        self.min_iou = TRACKING["min_iou"]
        self.distance_gate_ratio = TRACKING["distance_gate_ratio"]
        self.next_id = 1
        self.tracks: Dict[int, Track] = {}
        self.total_matches = 0
        self.total_track_creations = 0
        self.total_misses = 0

    @staticmethod
    def _iou(a, b):
        x1=max(a[0],b[0]); y1=max(a[1],b[1]); x2=min(a[2],b[2]); y2=min(a[3],b[3])
        inter=max(0,x2-x1)*max(0,y2-y1)
        aa=max(1,(a[2]-a[0])*(a[3]-a[1])); bb=max(1,(b[2]-b[0])*(b[3]-b[1]))
        return inter/(aa+bb-inter)

    @staticmethod
    def _center(box):
        return ((box[0]+box[2])/2.0, (box[1]+box[3])/2.0)

    @staticmethod
    def _dist(a,b):
        ax,ay=GreedyTracker._center(a); bx,by=GreedyTracker._center(b)
        return math.hypot(ax-bx, ay-by)

    def _predicted_box(self, t: Track, timestamp: float):
        if not t.history: return t.box
        last=t.history[-1]; dt=max(0.0,timestamp-t.last_time)
        vx,vy=last.get('vx',0.0),last.get('vy',0.0)
        dx,dy=vx*dt,vy*dt
        return (t.box[0]+dx,t.box[1]+dy,t.box[2]+dx,t.box[3]+dy)

    def update(self, detections: List[dict], timestamp: float):
        if not self.tracks:
            for d in detections: self._create(d,timestamp)
            return list(self.tracks.values())

        tids=list(self.tracks)
        preds={tid:self._predicted_box(self.tracks[tid],timestamp) for tid in tids}
        if detections:
            cost=np.full((len(tids),len(detections)),1e6,dtype=float)
            for i,tid in enumerate(tids):
                tr=self.tracks[tid]; pred=preds[tid]
                for j,d in enumerate(detections):
                    if tr.label != d['label'] and not self._compatible(tr.label,d['label']):
                        continue
                    dist=self._dist(pred,d['box'])
                    iou=self._iou(pred,d['box'])
                    gate=max(self.max_distance,self.distance_gate_ratio*max(tr.width,tr.height))
                    if dist <= gate or iou >= self.min_iou:
                        # Lower is better. IoU dominates when boxes overlap; distance breaks ties.
                        cost[i,j]=(1.0-iou)*100.0 + min(dist,gate)/max(1.0,gate)*25.0
            rows,cols=linear_sum_assignment(cost)
            matched_tids=set(); matched_dets=set()
            for r,c in zip(rows,cols):
                if cost[r,c] >= 1e6: continue
                tid=tids[r]; d=detections[c]; t=self.tracks[tid]
                self._update_track(t,d,timestamp); matched_tids.add(tid); matched_dets.add(c); self.total_matches+=1
        else:
            matched_tids=set(); matched_dets=set()

        for tid in tids:
            if tid in matched_tids: continue
            t=self.tracks.get(tid)
            if t is None: continue
            predicted=preds[tid]
            t.box=tuple(predicted); t.last_time=timestamp; t.missed+=1; t.age+=1; self.total_misses+=1
            self._append(t,timestamp,predicted=True)
            if t.missed>self.max_missed: del self.tracks[tid]

        for j,d in enumerate(detections):
            if j not in matched_dets: self._create(d,timestamp)
        return list(self.tracks.values())

    @staticmethod
    def _compatible(a,b):
        # Preserve semantic class but tolerate closely related generic labels.
        return (a in {'person','worker','operator','employee','human'} and b in {'person','worker','operator','employee','human'})

    def _create(self,d,timestamp):
        t=Track(self.next_id,d['label'],float(d['confidence']),tuple(d['box']),timestamp)
        self.next_id+=1; self.total_track_creations+=1; self._append(t,timestamp); self.tracks[t.track_id]=t

    def _update_track(self,t,d,timestamp):
        t.box=tuple(d['box']); t.label=d['label']; t.confidence=float(d['confidence']); t.missed=0; t.last_time=timestamp; t.age+=1; t.hits+=1
        self._append(t,timestamp)

    def _append(self,t,timestamp,predicted=False):
        cx,cy=t.center
        rec={'t':timestamp,'cx':cx,'cy':cy,'w':t.width,'h':t.height,'area':t.area,'bottom':t.bottom,'conf':t.confidence,'predicted':predicted}
        if t.history:
            p=t.history[-1]; dt=max(1e-3,timestamp-p['t']); rec['vx']=(cx-p['cx'])/dt; rec['vy']=(cy-p['cy'])/dt; rec['speed']=math.hypot(rec['vx'],rec['vy'])
            rec['acceleration']=(rec['speed']-p.get('speed',0.0))/dt
        else: rec['vx']=rec['vy']=rec['speed']=rec['acceleration']=0.0
        t.history.append(rec)
        if len(t.history)>60: del t.history[:-60]

    def stats(self):
        return {'active_tracks':len(self.tracks),'matches':self.total_matches,'track_creations':self.total_track_creations,'predicted_misses':self.total_misses}
