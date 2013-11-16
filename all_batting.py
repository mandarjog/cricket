#!/usr/bin/env python

"""
http://stats.espncricinfo.com/ci/engine/stats/index.html?class=2;orderby=start;orderbyad=reverse;page=1;result=1;result=2;result=3;result=5;template=results;type=batting;view=innings


Matches for a year
http://stats.espncricinfo.com/india/engine/records/team/match_results.html?class=2;id=2010;type=year

"""
import requests
import os
import crincinfo_import
from crick_util import mysql_execute, mysql_fetchall
from BeautifulSoup import BeautifulSoup
import difflib
import itertools


DIRNAME = os.path.dirname(os.path.abspath(__file__))


def import_year(year, force=False):
    """
    import a years worth of odi data
    into the database
    """

    # check if file is already downloaded

    datadir = DIRNAME + "/data"
    yearfile = "{}/matches.{}".format(datadir, year)
    yearurl = ("http://stats.espncricinfo.com/india/engine/records/"
               "team/match_results.html?class=2;id={};type=year".format(year))

    print yearurl

    if os.path.exists(yearfile):
        data = open(yearfile).read()
    else:
        data = requests.get(yearurl).text
        with open(yearfile, "wt") as fl:
            fl.write(data)

    print "Got {} bytes".format(len(data))
    # data is what we need
    crincinfo_import.import_matches(data)


def filt(trs):
    trsout = []
    for tr in trs:
        if tr.name == 'tr':
            try:
                if tr['class'] in ["inningsRow", "inningsComms"]:
                    trsout.append(tr)
            except KeyError:
                pass
    return trsout


class obj(object):
    def __repr__(self):
        return self.__dict__.__repr__()


def getint(val):
    try:
        return int(val)
    except ValueError:
        return 0
import re
RE_CB = re.compile("c\s+(.*)\s+b\s+(.*)$")
RE_STB = re.compile("st\s+(.*)\s+b\s+(.*)$")
RE_B = re.compile("b\s+(.*)$")
RE_RO = re.compile("run out \((\w+)(/s+)*\)")
RE_FOW = re.compile("(\d+)-(\d+)\*{0,1}\s*(.*?),\s*(\S+)")

# runout ==>  run out (Khan/Karthik)
# lbw b bhubhu


def resolve_name(pname, names):
    ns = difflib.get_close_matches(pname.strip(), names, n=1)

    if len(ns) > 0:
        return ns[0]
    else:
        return pname


def wicket(bat, wtype, bowl=None, assist=None):
    bat.out_type = wtype
    bat.out_by = bowl
    bat.out_assist = assist

    print wtype, "==>", bowl, assist


def resolve_match(bat1, bowl1, bat2, bowl2, summ1, summ2):
    player = {}

    for bn in itertools.chain(bat1, bat2, bowl1, bowl2):
        player[bn.player] = bn.playerid

    names = player.keys()
    print names

    for bat in itertools.chain(bat1, bat2):
        if bat.dismissal.startswith("run out"):
            dm = bat.dismissal[len("run out"):]
            wicket(bat, "runout", assist=resolve_name(dm.partition("/")[0], names))
            continue

        if "not out" in bat.dismissal:
            wicket(bat, "notout")
            continue

        if bat.dismissal.startswith("lbw"):
            bowler = bat.dismissal[5:]
            wicket(bat, "lbw", resolve_name(bowler, names))
            continue

        rm = RE_CB.match(bat.dismissal)
        if rm is not None:
            grp = rm.groups()
            # if caught and bowled grp[0] = "&"
            bowled = grp[1]
            caught = grp[0]
            if caught == "&":
                caught = bowled
            wicket(bat, "caught", resolve_name(bowled, names), resolve_name(caught, names))
            continue
        else:
            rm = RE_B.match(bat.dismissal)
            if rm is not None:
                grp = rm.groups()
                wicket(bat, "bowled", resolve_name(grp[0], names))
                continue
            else:
                rm = RE_STB.match(bat.dismissal)
                if rm is not None:
                    grp = rm.groups()
                    wicket(bat, "stumped", resolve_name(grp[1], names), resolve_name(grp[0], names))
                    continue

        # if none matched then just use it
        dm = bat.dismissal.split()[0]
        wicket(bat, dm)

    #import pdb; pdb.set_trace()
    print "ok"
    return names


def update_summary(odi, tbl, teamNo):
        trs = filt(tbl[0].findAll('tr'))
        summary = trs[-1]
        runs = summary.find('td', {'class': 'battingRuns'}).text
        wick = summary.find('td', {'class': 'battingDismissal'})
        spl = wick.text[1:-1].split()
        SQL = "update odi set team{}_runs=%s, team{}_wickets=%s, team{}_overs=%s where id=%s".format(teamNo,
                                     teamNo, teamNo)
        mysql_execute(SQL, runs, spl[0], spl[2], odi)

        # runs, wickets, overs
        return (runs, spl[0], spl[2])


def fetch_odi(year, odis=None):
    sql = "select id, odi_url from odi where match_date>='{}-01-01' and match_date <= '{}-12-31'".format(year, year)
    if odis is not None:
        sql += " and id in ({})".format(str(odis)[1:-1])
    odis = mysql_fetchall(sql)
    datadir = DIRNAME + "/data"

    for idx, odi in enumerate(odis):
        matchfile = "{}/matche.{}".format(datadir, odi.id)
        match_url = "http://www.espncricinfo.com{}".format(odi.odi_url)
        if os.path.exists(matchfile):
            data = open(matchfile).read()
        else:
            print match_url
            data = requests.get(match_url).text
            with open(matchfile, "wt") as fl:
                fl.write(data)

        soup = BeautifulSoup(data)
        tbl = soup.findAll('table', {'id': 'inningsBat1'})
        th = tbl[0].find('tr', {'class': 'inningsHead'})
        summ1 = update_summary(odi.id, tbl, 1)
        tdd = th.findAll('td')[1]
        team1 = tdd.text.partition('innings')[0].strip()
        bat1 = get_innings(tbl)
        tbl = soup.findAll('table', {'id': 'inningsBowl1'})
        bowl1 = get_innings(tbl)
        tbl = soup.findAll('table', {'id': 'inningsBat2'})
        summ2 = update_summary(odi.id, tbl, 2)
        th = tbl[0].find('tr', {'class': 'inningsHead'})
        tdd = th.findAll('td')[1]
        team2 = tdd.text.partition('innings')[0].strip()
        bat2 = get_innings(tbl)
        tbl = soup.findAll('table', {'id': 'inningsBowl2'})
        bowl2 = get_innings(tbl)
        names = resolve_match(bat1, bowl1, bat2, bowl2, summ1, summ2)
        # write results to database
        print bat1, bat2

        tbls = soup.findAll('table', {'class': 'inningsTable'})
        fow = {}
        for _tbl in tbls:
            _trs = _tbl.findAll('tr')
            if len(_trs) > 1:
                continue
            if _trs[0].text.lower().startswith("fall of wickets"):
                for ll in _trs[0].text[len("Fall of wickets"):].split('),'):
                    if "not out" in ll:
                        continue
                    mm = RE_FOW.match(ll)
                    if mm:
                        grp = mm.groups()
                        fow[resolve_name(grp[2], names)] = (int(grp[0]), int(grp[1]), int(float(grp[3])))

        # set fow on bat1 and bat2
        for bt in itertools.chain(bat1, bat2):
            if bt.out_type == "notout":
                continue
            if not hasattr(bt, 'out_over'):
                fw = fow[bt.player]
                bt.out_wicket_no = fw[0]
                bt.out_score = fw[1]
                bt.out_over = fw[2]

        write_vals(bat1, 1, team1, odi.id, summ1)

        write_vals(bat2, 2, team2, odi.id, summ2)

        #if idx == 3:
        #    break

import _mysql


def write_vals(bt, inns, team, odi, summ):
    """

    """
    print team, inns, bt

    SQL = ("INSERT INTO `score`(odi, team, player, inns, runs, balls, mins, fours, sixes, pos,"
           "`out`, out_over, out_score, out_wicket_no, out_by, out_assist) VALUES ")
    vals = []
    for bb in bt:
        row = "("
        row += '{},"{}","{}",{},{},{},'.format(odi, team, _mysql.escape_string(bb.player), inns, bb.runs, bb.balls)
        row += '{},{},{},{},'.format(bb.mins, bb.fours, bb.sixes, bb.pos)
        if bb.out_type == 'notout':
            row += '"notout",NULL,NULL,NULL,'
            row += 'NULL,NULL'
        else:
            if hasattr(bb, "out_over"):
                row += '"{}",{},{},{},'.format(bb.out_type, bb.out_over, bb.out_score, bb.out_wicket_no)
            else:
                row += '"{}",{},{},{},'.format(bb.out_type, summ[2], summ[0], summ[1])

            if hasattr(bb, 'out_by'):
                row += '"{}",'.format(bb.out_by)
            else:
                row += 'NULL,'
            if hasattr(bb, 'out_assist'):
                row += '"{}"'.format(bb.out_assist)
            else:
                row += 'NULL'
        row += ')'

        print row
        vals.append(row)

    mysql_execute(SQL + ",".join(vals))


def cleanup_name(diss):
    diss = diss.replace("*", "")
    diss = diss.replace("&dagger;", "")
    return diss


def get_innings(tbl):
        trs = filt(tbl[0].findAll('tr'))
        obs = []
        for tr in trs:
            td = tr.findAll('td')
            if tr['class'] == "inningsRow":
                print td[4]['class']
                if "battingDetails" == td[4]['class']:
                    if "battingDismissal" != td[2]['class']:
                        continue
                    if td[1].a is None:
                        continue
                    ob = obj()
                    obs.append(ob)
                    ob.pos = len(obs)
                    ob.player = cleanup_name(td[1].text)
                    ob.playerid = os.path.basename(td[1].a['href'].partition(".")[0])
                    ob.dismissal = cleanup_name(td[2].text)
                    ob.runs = getint(td[3].text)
                    ob.mins = getint(td[4].text)
                    ob.balls = getint(td[5].text)
                    ob.fours = getint(td[6].text)
                    ob.sixes = getint(td[7].text)
                elif "bowlingDetails" == td[4]['class']:
                    ob = obj()
                    obs.append(ob)
                    ob.player = cleanup_name(td[1].text)
                    ob.playerid = os.path.basename(td[1].a['href'].partition(".")[0])
            elif tr['class'] == "inningsComms":
                td = tr.find('td', {'class': 'battingComms'})
                if td is not None:
                    vals = td.findAll('b')
                    if len(vals) < 2:
                        continue
                    ob.out_over = int(float(vals[0].text))
                    score, _, wicket_no = vals[-1].text.partition('/')
                    ob.out_score = int(score)
                    ob.out_wicket_no = int(wicket_no)
        return obs
