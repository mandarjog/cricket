from crick_util import mysql_execute, mysql_fetchall
import pylab as pyl
from collections import defaultdict
import matplotlib.colors
import numpy as np
_dismissal_map2 = { 'caught' :1.0, 
                    'bowled' :2.0,
                    'lbw': 3.0,
                    'run out': 4.0,
                    'stumped': 5.0,
                    'not out': 8.0
                }
_dismissal_map = { 'caught' : 'k',
                    'bowled' :'gold',
                    'lbw': 'c',
                    'run out': 'r',
                    'stumped': 'b',
                    'not out': 'chartreuse'
                }
dismissal_map = defaultdict(float)
for k in _dismissal_map:
    dismissal_map[k] = _dismissal_map[k]
colormap = [

        ]

success_rate_slabs = [0, 30, 50, 65, 75, 90, 100, 120 ]
# create a colormap matplotlib.colors.ListedColormap (colormap)
def player_teamtotal (player):
    """
    plot player score with signed innings against
    team score signed by win or loss
    """

    SQL = """select s.runs, m.inns, s.dismissal, m.score, m.result, s.team from
            scorecard s, matchresults m where s.odi=m.odi and s.team=m.team and
            s.player=%s"""
    #and YEAR(m.at)<2002"""

    res = mysql_fetchall(SQL, player)
    battingsuccess = defaultdict(lambda: np.asarray([[0,0,0],[0,0,0]]))

    player_total = []
    team_total = []
    dismissals = []
    dm_player = defaultdict(list)
    dm_team = defaultdict(list)

    for runs,inns,dismissal,score,result,team in res:
        if inns!=2:
            player_total.append(runs)
            dm_player[dismissal].append(runs)
        else:
            player_total.append(-1*runs)
            dm_player[dismissal].append(-1*runs)

        if result == 'won':
            team_total.append(score)
            dm_team[dismissal].append(score)
        else:
            team_total.append(-1*score)
            dm_team[dismissal].append(-1*score)

        for idx in range(len(success_rate_slabs)):
            if runs >= success_rate_slabs[idx]:
                battingsuccess[success_rate_slabs[idx]][inns-1][2] += 1
                if result == 'won':
                    battingsuccess[success_rate_slabs[idx]][inns-1][0] += 1
                else:
                    battingsuccess[success_rate_slabs[idx]][inns-1][1] += 1

        if dismissal in _dismissal_map:
            dismissals.append (_dismissal_map[dismissal])
        else:
            dismissals.append ( 'k')
        #dismissals.append (dismissal_map[dismissal])

    #print battingsuccess
    for slab in success_rate_slabs:
        print slab,":",int(100*float(battingsuccess[slab][0][0]+battingsuccess[slab][1][0])/float(battingsuccess[slab][0][2]+battingsuccess[slab][1][2])),
        print battingsuccess[slab][0][0]+battingsuccess[slab][1][0]
    #r1=pyl.scatter (team_total, player_total, c=dismissals, 
    #        marker='h', s=100, alpha=0.5)
    for dd in dm_team:
        if dd in _dismissal_map:
            color = _dismissal_map[dd]
            label = dd
        else:
            color = 'k'
            label = '_nolegend_'
        r1=pyl.scatter (dm_team[dd], dm_player[dd], c=color, 
            marker='h', s=100, alpha=0.5, label=label)

    #r1.axes .. can be used to set limits.
    #r1.axes.set_ylim (-5,220)
    team = team.capitalize()
    player = player.capitalize()
    r1.axes.set_ylim (-220,220)
    r1.axes.set_xlim (-510,510)
    r1.axes.set_xlabel(team+' Runs', fontsize=15)
    r1.axes.set_ylabel(player+' Runs')
    r1.axes.text(330,200, "Won Batting First", color='grey', fontsize=15)
    r1.axes.text(-480,200, "Lost Batting First", color='grey', fontsize=15)
    r1.axes.text(330,-200, "Won Chasing", color='grey', fontsize=15)
    r1.axes.text(-480,-200, "Lost Chasing", color='grey', fontsize=15)
    r1.axes.xaxis.grid()
    r1.axes.yaxis.grid()
    pyl.title ( team+" and "+player)
    leg=r1.axes.legend (loc='upper center')
    #import pdb;pdb.set_trace()
    pyl.show()

def main():
    #player_teamtotal ('matthew hayden')
    #player_teamtotal ('adam gilchrist')
    #player_teamtotal ('mohammad azharuddin')
    #player_teamtotal ('chris gayle')
    #player_teamtotal ('yuvraj singh')
    #player_teamtotal ('brian lara')
    #player_teamtotal ('sachin tendulkar')
    player_teamtotal ('viv richards')
    #player_teamtotal ('ricky ponting')
    #player_teamtotal ('saurav ganguly')
    #player_teamtotal ('virendra sehwag')
    #player_teamtotal ('mahendra dhoni')

if __name__ == "__main__":
    main()
