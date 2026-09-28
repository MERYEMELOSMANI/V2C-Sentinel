from pathlib import Path
import sys, os, json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'paper/working/packages'))
os.environ['MPLCONFIGDIR']=str(ROOT/'paper/working/mpl-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

OUT=ROOT/'paper/figures'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
 'font.size':8,'axes.labelsize':8,'axes.titlesize':9,'legend.fontsize':7,
 'xtick.labelsize':7,'ytick.labelsize':7,'axes.spines.top':False,
 'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
blue='#205D8F'; orange='#A94B13'; gray='#555555'
summary=pd.read_csv(ROOT/'results/final_two_level/summary.csv')
runs=pd.read_csv(ROOT/'results/final_two_level/all_runs.csv')
pred=pd.read_csv(ROOT/'results/tables/all_predictions.csv',usecols=['recording_id','timestamp','local_pred','cloud_pred','true_label'])
stats=pred.groupby('recording_id').agg(messages=('timestamp','size'),start=('timestamp','min'),end=('timestamp','max'))
stats['duration_s']=stats.end-stats.start
order=['1.0','5.0','10.0','50.0','unlimited']; labels=['1','5','10','50','Unrestricted']
def rows(split):
    z=summary[(summary.split==split)&(summary.deadline_s==.15)].copy()
    return z.set_index('budget').loc[order]
dev=rows('dev'); test=rows('test')
assert len(dev)==len(test)==5
for split,z in [('dev',dev),('test',test)]:
    assert (z.attack_episodes==1).all()
    rr=runs[(runs.split==split)&(runs.deadline_s==.15)].groupby('budget').total_requests.sum()
    assert (rr.loc[order].values==z.total_requests.values).all()
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=420,bbox_inches='tight',pad_inches=.04)
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight',pad_inches=.04)
    plt.close(fig)

# A purpose-built scientific architecture diagram; no decorative stock imagery.
fig,ax=plt.subplots(figsize=(3.35,3.25)); ax.set_xlim(0,10); ax.set_ylim(0,11); ax.axis('off')
def box(x,y,w,h,text,fill='white',edge=gray):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.07,rounding_size=0.08',facecolor=fill,edgecolor=edge,lw=.8))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=8)
def arrow(x1,y1,x2,y2): ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=9,lw=.8,color=gray))
box(2.1,9.5,5.8,.9,'ROAD CAN events\nChronological replay')
box(2.1,7.7,5.8,1.05,'Local logistic regression\nAssumed processing: 5 ms','#F0F5FA',blue)
arrow(5,9.5,5,8.75)
box(.15,5.55,4.25,1.05,'Level 1 warning\nLocal positive','#F0F5FA',blue)
box(5.5,5.55,4.3,1.05,'Token bucket\nBudgeted requests')
arrow(3.2,7.7,2.3,6.6); arrow(6.8,7.7,7.65,6.6)
ax.text(5,7.1,'Local positive',ha='center',fontsize=7)
box(5.5,3.5,4.3,1.05,'CICV5G delay replay\nUrban n78 trace')
arrow(7.65,5.55,7.65,4.55)
box(5.5,1.5,4.3,1.05,'Cloud random forest\n10 ms assumed','#FFF4EA',orange)
arrow(7.65,3.5,7.65,2.55)
box(.15,1.5,4.25,1.05,'Level 2 confirmation\nCloud positive','#FFF4EA',orange)
arrow(5.5,2.02,4.4,2.02)
ax.text(2.3,3.15,'Local warning remains\nregardless of confirmation',ha='center',va='center',fontsize=7)
ax.text(5,.45,'Both models run on the development computer.\nCommunication is replayed; no vehicle actuation.',ha='center',va='center',fontsize=7)
save(fig,'fig1_architecture')

fig,ax=plt.subplots(figsize=(3.35,2.65),layout='constrained')
x=np.arange(5)
ax.plot(x,dev.level2_cloud_delay*1000,'o-',color=blue,label='Development confirmation',lw=1.3,ms=4)
ax.plot(x,test.level2_cloud_delay*1000,'s--',color=orange,label='Test confirmation',lw=1.3,ms=4)
ax.axhline(5,color=gray,lw=1,ls=':',label='Local warning (both splits)')
ax.axhline(150,color='#222222',lw=.7,ls='--'); ax.text(4.12,150,'150',fontsize=6,va='center')
ax.axhline(300,color='#888888',lw=.7,ls='-.'); ax.text(4.12,300,'300',fontsize=6,va='center')
ax.set_yscale('log'); ax.set_ylim(3,13000); ax.set_xlim(-.18,4.5)
ax.set_yticks([5,30,150,300,1000,3000],['5','30','150','300','1000','3000'])
ax.set_xticks(x,labels); ax.set_xlabel('Request budget (requests/s)')
ax.set_ylabel('First detection delay (ms, log scale)')
ax.grid(axis='y',alpha=.18); ax.legend(loc='upper right',frameon=False)
save(fig,'fig2_latency')

fig,ax=plt.subplots(figsize=(3.35,2.3),layout='constrained')
xx=np.arange(2); vals=[dev.level1_local_false_per_hr.iloc[0],test.level1_local_false_per_hr.iloc[0]]
bars=ax.bar(xx-.18,vals,.34,color=blue,label='Level 1 local')
ax.bar(xx+.18,[0,0],.34,color=orange,label='Level 2 confirmed')
for rect,val in zip(bars,vals): ax.text(rect.get_x()+rect.get_width()/2,val+100,f'{val:.1f}',ha='center',fontsize=7)
for i in xx:
    ax.plot(i+.18,0,'s',color=orange,ms=5,clip_on=False)
    ax.text(i+.18,130,'0 observed',ha='center',fontsize=6.5)
ax.set_xticks(xx,['Development\n390.46 s normal traffic','Test\n47.73 s normal traffic'])
ax.set_ylim(0,4800); ax.set_ylabel('Grouped false alerts per hour')
ax.legend(frameon=False,loc='upper center',ncols=2)
ax.grid(axis='y',alpha=.18); ax.set_axisbelow(True)
save(fig,'fig3_false_alerts')

exposure={'dev':float(stats.loc[['normal_02','attack_02'],'duration_s'].sum()),
          'test':float(stats.loc[['normal_03','attack_03'],'duration_s'].sum())}
fig,ax=plt.subplots(figsize=(3.35,2.5),layout='constrained')
for offset,split,z,color,hatch in [(-.18,'dev',dev,blue,''),(.18,'test',test,orange,'//')]:
    rates=z.total_requests.values/exposure[split]
    bars=ax.bar(x+offset,rates,.34,color=color,hatch=hatch,label='Development' if split=='dev' else 'Test')
    for bar,val in zip(bars,rates): ax.text(bar.get_x()+bar.get_width()/2,val*1.12,f'{val:.1f}',ha='center',fontsize=6.5)
ax.set_yscale('log'); ax.set_ylim(.7,260); ax.set_ylabel('Actual requests/s (log scale)')
ax.set_yticks([1,5,10,50,100],['1','5','10','50','100']); ax.set_xticks(x,labels)
ax.set_xlabel('Request budget (requests/s)'); ax.legend(frameon=False,loc='upper left')
ax.grid(axis='y',alpha=.18); ax.set_axisbelow(True)
save(fig,'fig4_request_rates')

summary.to_csv(OUT/'source_summary.csv',index=False)
stats.to_csv(OUT/'recording_exposure.csv')
manifest={'exposure_seconds':exposure,'figures':['fig1_architecture','fig2_latency','fig3_false_alerts','fig4_request_rates'],
'source':'results/final_two_level/summary.csv, results/final_two_level/all_runs.csv, results/tables/all_predictions.csv',
'note':'No error bars: one observed attack episode per split, not independent repeated trials.'}
(OUT/'figure_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest))
